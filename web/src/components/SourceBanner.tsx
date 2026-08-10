import type { SourceStatus } from "../types";

export function SourceBanner({ sources }: { sources: SourceStatus[] }) {
  const broken = sources.filter((s) => !s.ok);
  const partial = sources.filter(
    (s) => s.ok && Object.keys(s.failed_venues).length > 0
  );
  if (broken.length === 0 && partial.length === 0) return null;

  return (
    <div className="banner">
      {broken.length > 0 && (
        <span>{broken.map((s) => s.slug).join(", ")} unavailable — showing older data. </span>
      )}
      {partial.length > 0 && (
        <span>
          {partial.reduce((n, s) => n + Object.keys(s.failed_venues).length, 0)} cinemas
          could not be refreshed.
        </span>
      )}
    </div>
  );
}
