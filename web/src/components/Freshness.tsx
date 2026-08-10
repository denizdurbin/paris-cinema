export function Freshness({ generatedAt, now }: { generatedAt: string; now: Date }) {
  const hours = Math.floor((now.getTime() - new Date(generatedAt).getTime()) / 3_600_000);
  const stale = hours >= 12;
  const label =
    hours < 1 ? "updated just now" : `updated ${hours}h ago`;
  return (
    <span className={stale ? "freshness freshness-stale" : "freshness"}>
      {stale ? `${label} — data may be out of date` : label}
    </span>
  );
}
