import { ReactNode } from "react";

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Card({ title, children, className = "" }: CardProps) {
  return (
    <section
      className={`rounded-2xl border border-white/10 bg-slate-900/60 p-4 shadow-sm backdrop-blur ${className}`}
    >
      {title ? (
        <header className="mb-3 text-base font-semibold tracking-tight text-slate-100">
          {title}
        </header>
      ) : null}
      <div className="text-base text-slate-200">{children}</div>
    </section>
  );
}




