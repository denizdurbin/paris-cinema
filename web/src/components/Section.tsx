import type { ReactNode } from "react";

export function Section({ title, count, children }: {
  title: string; count?: number; children: ReactNode;
}) {
  return (
    <section className="section">
      <h2 className="section-title">
        {title}
        {count !== undefined && <span className="section-count faint">{count}</span>}
      </h2>
      {children}
    </section>
  );
}
