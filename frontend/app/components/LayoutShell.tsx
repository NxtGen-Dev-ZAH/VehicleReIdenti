"use client";

import { ReactNode } from "react";
import { NavBar } from "./NavBar";

interface LayoutShellProps {
  children: ReactNode;
}

export function LayoutShell({ children }: LayoutShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <NavBar />
        <main className="mt-6 flex-1">{children}</main>
        <footer className="mt-10 border-t border-white/10 pt-4 text-xs text-slate-500">
          VehiclereID • Minimal analysis dashboard
        </footer>
      </div>
    </div>
  );
}




