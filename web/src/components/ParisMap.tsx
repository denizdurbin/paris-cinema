import type { Venue } from "../types";
import { venuePosition, SEINE_PATH, MAP_WIDTH, MAP_HEIGHT, ARRONDISSEMENT_LABELS } from "../venueCoords";

export function ParisMap({ venues, isVisible, toggle }: {
  venues: Venue[];
  isVisible: (id: string) => boolean;
  toggle: (id: string) => void;
}) {
  const independents = venues.filter((v) => v.kind === "independent");

  return (
    <svg
      className="paris-map"
      viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
      role="img"
      aria-label="Map of Paris cinemas"
    >
      <path className="map-seine" d={SEINE_PATH} />

      {ARRONDISSEMENT_LABELS.map(({ num, x, y }) => (
        <text key={num} className="map-arr" x={x} y={y}>{num}</text>
      ))}

      {independents.map((v, i) => {
        const { x, y } = venuePosition(v);
        return (
          <circle
            key={v.id}
            className={isVisible(v.id) ? "map-dot map-dot-on" : "map-dot map-dot-off"}
            cx={x}
            cy={y}
            r={4}
            style={{ animationDelay: `${i * 20}ms` }}
            onClick={() => toggle(v.id)}
          >
            <title>{v.name}</title>
          </circle>
        );
      })}
    </svg>
  );
}
