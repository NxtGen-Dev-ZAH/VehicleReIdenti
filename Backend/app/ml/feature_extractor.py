from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    import cv2
except Exception as exc:
    raise RuntimeError("OpenCV (cv2) is required.") from exc

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

from app.ml.config import ModelConfig

logger = logging.getLogger("app.ml.feature_extractor")


# ──────────────────────────────────────────────
# Inline TransReID model definition
# (copied from your training server so Backend
#  has no dependency on the training project)
# ──────────────────────────────────────────────

class SELayer(nn.Module):
    def __init__(self, channel, reduction=16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channel, channel // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channel // reduction, channel, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        return x * y.expand_as(x)


class ResNet50IBN(nn.Module):
    """ResNet-50 with Instance-Batch Normalization backbone (simplified inline)."""
    def __init__(self):
        super().__init__()
        from torchvision.models import resnet50, ResNet50_Weights
        base = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        # Remove avgpool and fc — we want the feature map
        self.layer0 = nn.Sequential(base.conv1, base.bn1, base.relu, base.maxpool)
        self.layer1 = base.layer1
        self.layer2 = base.layer2
        self.layer3 = base.layer3
        self.layer4 = base.layer4

    def forward(self, x):
        x = self.layer0(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        return x  # (B, 2048, H, W)


class TransReIDBlock(nn.Module):
    """Single transformer encoder block."""
    def __init__(self, dim, num_heads, mlp_ratio=4.0, dropout=0.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = nn.MultiheadAttention(dim, num_heads, dropout=dropout, batch_first=True)
        self.norm2 = nn.LayerNorm(dim)
        mlp_dim = int(dim * mlp_ratio)
        self.mlp = nn.Sequential(
            nn.Linear(dim, mlp_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(mlp_dim, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        x2 = self.norm1(x)
        attn_out, _ = self.attn(x2, x2, x2)
        x = x + attn_out
        x = x + self.mlp(self.norm2(x))
        return x


class TransReID(nn.Module):
    def __init__(self, in_chans=2048, embed_dim=512, depth=6,
                 num_heads=8, camera_num=20):
        super().__init__()
        self.patch_embed = nn.Conv2d(in_chans, embed_dim, kernel_size=1)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.cam_embed = nn.Embedding(camera_num + 1, embed_dim)
        self.blocks = nn.ModuleList([
            TransReIDBlock(embed_dim, num_heads) for _ in range(depth)
        ])
        self.norm = nn.LayerNorm(embed_dim)
        nn.init.trunc_normal_(self.cls_token, std=0.02)

    def forward(self, x, cam_label=None):
        B = x.size(0)
        x = self.patch_embed(x)                          # (B, embed_dim, H, W)
        x = x.flatten(2).transpose(1, 2)                 # (B, N, embed_dim)
        cls = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls, x], dim=1)                   # (B, N+1, embed_dim)
        if cam_label is not None:
            cam_label = cam_label.clamp(0, self.cam_embed.num_embeddings - 1)
            cam_emb = self.cam_embed(cam_label).unsqueeze(1)
            x[:, 0:1] = x[:, 0:1] + cam_emb
        for blk in self.blocks:
            x = blk(x)
        x = self.norm(x)
        return x[:, 0], x[:, 1:]   # global_feat, patch_tokens


class AttributeNet_TransReID(nn.Module):
    """Matches your training architecture exactly."""
    def __init__(self, num_classes, num_attributes=2, attr_classes=None,
                 feature_dim=512, attr_feat_dim=128,
                 transformer_depth=6, transformer_heads=8, camera_num=20):
        super().__init__()
        if attr_classes is None:
            attr_classes = [11, 10]

        self.num_attributes = num_attributes
        self.attr_classes = attr_classes
        self.backbone = ResNet50IBN()
        self.in_planes = 2048

        self.transreid = TransReID(
            in_chans=2048, embed_dim=512,
            depth=transformer_depth, num_heads=transformer_heads,
            camera_num=camera_num,
        )

        self.bottleneck_trans = nn.BatchNorm1d(512)
        self.bottleneck_trans.bias.requires_grad_(False)
        self.fc_trans = nn.Linear(512, feature_dim, bias=False)
        self.bn_trans = nn.BatchNorm1d(feature_dim)
        self.bn_trans.bias.requires_grad_(False)
        nn.init.normal_(self.fc_trans.weight, std=0.001)
        self.classifier_trans = nn.Linear(feature_dim, num_classes, bias=False)
        nn.init.normal_(self.classifier_trans.weight, std=0.001)

        self.gap = nn.AdaptiveAvgPool2d(1)
        self.attr_attns = nn.ModuleList([SELayer(self.in_planes, 16) for _ in range(num_attributes)])
        self.attr_fcs = nn.ModuleList([nn.Linear(self.in_planes, attr_feat_dim, bias=False) for _ in range(num_attributes)])
        self.attr_classifiers = nn.ModuleList([nn.Linear(attr_feat_dim, attr_classes[i], bias=False) for i in range(num_attributes)])

        self.attr_combine_conv = nn.Sequential(
            nn.Conv2d(self.in_planes, self.in_planes, 1),
            nn.BatchNorm2d(self.in_planes), nn.ReLU(inplace=True),
        )
        self.attr_distill = nn.Sequential(
            nn.Conv2d(self.in_planes, self.in_planes, 3, padding=1),
            nn.BatchNorm2d(self.in_planes), nn.ReLU(inplace=True),
            nn.Conv2d(self.in_planes, 512, 3, padding=1),
            nn.BatchNorm2d(512), nn.ReLU(inplace=True),
        )
        self.fc_joint = nn.Linear(512, feature_dim, bias=False)
        self.bn_joint = nn.BatchNorm1d(feature_dim)
        self.bn_joint.bias.requires_grad_(False)
        nn.init.normal_(self.fc_joint.weight, std=0.001)
        self.classifier_joint = nn.Linear(feature_dim, num_classes, bias=False)
        nn.init.normal_(self.classifier_joint.weight, std=0.001)

    def forward(self, x, cam_label=None):
        B = x.size(0)
        F_map = self.backbone(x)
        trans_global_feat, _ = self.transreid(F_map, cam_label)
        trans_bn = self.bottleneck_trans(trans_global_feat)
        trans_feat = self.fc_trans(trans_bn)
        trans_feat_bn = self.bn_trans(trans_feat)

        A_maps = []
        for i in range(self.num_attributes):
            A_i = self.attr_attns[i](F_map)
            A_maps.append(A_i)

        G_map = sum(A_maps)
        G_map = G_map + self.attr_combine_conv(G_map)
        G_reid = self.attr_distill(G_map)
        G_reid_pooled = self.gap(G_reid).view(B, -1)

        joint_feat = trans_global_feat + G_reid_pooled
        joint_feat_proj = self.fc_joint(joint_feat)
        joint_feat_bn = self.bn_joint(joint_feat_proj)

        # Always return normalized embedding (inference mode)
        return F.normalize(joint_feat_bn, p=2, dim=1)


# ──────────────────────────────────────────────
# Feature extractor wrapper
# ──────────────────────────────────────────────

class TransReIDFeatureExtractor:
    """Loads your trained TransReID model and extracts 512-dim embeddings."""

    def __init__(self, config: ModelConfig):
        self.device = torch.device(config.device)
        self.batch_size = max(1, config.batch_size)

        self.model = AttributeNet_TransReID(
            num_classes=config.transreid_num_classes,
            num_attributes=config.transreid_num_attributes,
            attr_classes=config.transreid_attr_classes,
            feature_dim=config.transreid_feature_dim,
            camera_num=config.transreid_camera_num,
        )

        weights_path = config.model_weights_path
        if weights_path and Path(weights_path).exists():
            self._load_weights(weights_path)
        else:
            logger.warning(
                "TransReID weights not found — using random weights! "
                "Set MODEL_WEIGHTS_PATH in .env",
                extra={"path": str(weights_path)},
            )

        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((256, 128)),   # standard Re-ID input size
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])
        logger.info("TransReIDFeatureExtractor ready", extra={"device": str(self.device)})

    def _load_weights(self, weights_path: Path) -> None:
        try:
            checkpoint = torch.load(str(weights_path), map_location="cpu")
            state_dict = checkpoint.get("model_state_dict", checkpoint)
            missing, unexpected = self.model.load_state_dict(state_dict, strict=False)
            logger.info(
                "Loaded TransReID weights",
                extra={
                    "weights": str(weights_path),
                    "missing": len(missing),
                    "unexpected": len(unexpected),
                },
            )
        except Exception as exc:
            logger.error("Failed to load TransReID weights", extra={"error": str(exc)})

    def _preprocess(self, frame: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        return self.transform(image)

    @torch.inference_mode()
    def extract(self, crops: Iterable[np.ndarray]) -> np.ndarray:
        crops_list = list(crops)
        if not crops_list:
            return np.zeros((0, 512), dtype=np.float32)

        tensors = [self._preprocess(c) for c in crops_list]
        feats: list[np.ndarray] = []

        for idx in range(0, len(tensors), self.batch_size):
            batch = torch.stack(tensors[idx: idx + self.batch_size]).to(self.device)
            embeddings = self.model(batch).detach().cpu().numpy()
            feats.append(embeddings)

        stacked = np.vstack(feats)
        # Already L2-normalized by model, but normalize again for safety
        norms = np.linalg.norm(stacked, axis=1, keepdims=True) + 1e-12
        return stacked / norms