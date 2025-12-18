"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/#upload", label: "Upload" },
  { href: "/#about", label: "About" },
  { href: "/videos", label: "History" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="flex items-center justify-between rounded-2xl border border-white/10 bg-slate-900/60 px-4 py-3 backdrop-blur">
      <div className="text-base font-semibold tracking-tight text-slate-50">
        VehiclereID
      </div>
      <nav className="flex gap-1 text-sm sm:text-base">
        {links.map((link) => {
          const active =
            link.href === "/"
              ? pathname === "/"
              : pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={[
                "rounded-full px-3 py-1.5 transition",
                active
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-200 hover:bg-slate-800",
              ].join(" ")}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}




