"use client";

import { useEffect, useRef } from "react";
import type { TrajectoryData } from "../lib/api";

interface Props {
  trajectory: TrajectoryData;
}

export function TrajectoryMap({ trajectory }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;
    
    // Guard: don't render if camera data is missing
    if (!trajectory?.camera_a?.lat || !trajectory?.camera_b?.lat) return;
    
    import("leaflet").then((L) => {
      // Fix default marker icons
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
      });

      const { camera_a, camera_b, vehicle_paths } = trajectory;

      // Center map between the two cameras
      const centerLat = (camera_a.lat + camera_b.lat) / 2;
      const centerLng = (camera_a.lng + camera_b.lng) / 2;

      const map = L.map(mapRef.current!).setView([centerLat, centerLng], 14);
      mapInstanceRef.current = map;

      // Dark tile layer
      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        {
          attribution: "©OpenStreetMap ©CartoDB",
          maxZoom: 19,
        }
      ).addTo(map);

      // Camera A marker (blue)
      const camAIcon = L.divIcon({
        html: `<div style="background:#6366f1;border:2px solid #fff;border-radius:50%;width:16px;height:16px;box-shadow:0 0 8px #6366f1aa"></div>`,
        className: "",
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });

      // Camera B marker (emerald)
      const camBIcon = L.divIcon({
        html: `<div style="background:#10b981;border:2px solid #fff;border-radius:50%;width:16px;height:16px;box-shadow:0 0 8px #10b981aa"></div>`,
        className: "",
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });

      L.marker([camera_a.lat, camera_a.lng], { icon: camAIcon })
        .addTo(map)
        .bindPopup(
          `<div style="color:#1e293b;font-weight:600">${camera_a.name}</div><div style="font-size:11px">Camera A</div>`
        );

      L.marker([camera_b.lat, camera_b.lng], { icon: camBIcon })
        .addTo(map)
        .bindPopup(
          `<div style="color:#1e293b;font-weight:600">${camera_b.name}</div><div style="font-size:11px">Camera B</div>`
        );

      // Draw trajectory lines for re-identified vehicles
      const reidentified = vehicle_paths.filter((v) => v.reidentified);
      const notReidentified = vehicle_paths.filter((v) => !v.reidentified);

      // Re-identified vehicles: bright animated line
      if (reidentified.length > 0) {
        L.polyline(
          [[camera_a.lat, camera_a.lng], [camera_b.lat, camera_b.lng]],
          {
            color: "#6366f1",
            weight: 3,
            opacity: 0.9,
            dashArray: "8 4",
          }
        )
          .addTo(map)
          .bindPopup(
            `<div style="color:#1e293b;font-weight:600">${reidentified.length} vehicle(s) re-identified</div><div style="font-size:11px">Tracked across both cameras</div>`
          );
      }

      // Camera labels
      L.tooltip({
        permanent: true,
        direction: "top",
        className: "cam-label",
        offset: [0, -12],
      })
        .setContent(`<span style="font-size:11px;font-weight:600;color:#a5b4fc">CAM-A</span>`)
        .setLatLng([camera_a.lat, camera_a.lng])
        .addTo(map);

      L.tooltip({
        permanent: true,
        direction: "top",
        className: "cam-label",
        offset: [0, -12],
      })
        .setContent(`<span style="font-size:11px;font-weight:600;color:#6ee7b7">CAM-B</span>`)
        .setLatLng([camera_b.lat, camera_b.lng])
        .addTo(map);

      // Stats box on map
      const legend = L.control({ position: "bottomright" });
      legend.onAdd = () => {
        const div = L.DomUtil.create("div");
        div.innerHTML = `
          <div style="background:rgba(15,23,42,0.9);border:1px solid #334155;border-radius:8px;padding:10px 14px;min-width:160px">
            <div style="font-size:11px;font-weight:600;color:#94a3b8;margin-bottom:6px">TRAJECTORY SUMMARY</div>
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
              <div style="width:10px;height:10px;border-radius:50%;background:#6366f1"></div>
              <span style="font-size:11px;color:#e2e8f0">Camera A: ${camera_a.name.split("–")[1]?.trim() ?? "View 1"}</span>
            </div>
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
              <div style="width:10px;height:10px;border-radius:50%;background:#10b981"></div>
              <span style="font-size:11px;color:#e2e8f0">Camera B: ${camera_b.name.split("–")[1]?.trim() ?? "View 2"}</span>
            </div>
            <div style="border-top:1px solid #334155;padding-top:6px">
              <div style="font-size:12px;color:#6ee7b7;font-weight:600">${reidentified.length} re-identified</div>
              <div style="font-size:11px;color:#94a3b8">${notReidentified.length} single-camera</div>
            </div>
          </div>
        `;
        return div;
      };
      legend.addTo(map);
    });

    return () => {
      if (mapInstanceRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (mapInstanceRef.current as any).remove();
        mapInstanceRef.current = null;
      }
    };
  }, [trajectory]);

  return (
    <>
      <style>{`
        .cam-label { background: transparent !important; border: none !important; box-shadow: none !important; }
        .leaflet-tooltip.cam-label::before { display: none; }
      `}</style>
      <div
        ref={mapRef}
        className="h-72 w-full rounded-xl border border-slate-700 overflow-hidden"
      />
      <div className="mt-2 flex items-center gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-indigo-400" /> Camera A
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /> Camera B
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-5 border-t-2 border-dashed border-indigo-400" />
          Vehicle trajectory
        </span>
      </div>
    </>
  );
}