import { useMemo, useState } from "react";
import type { Venue } from "../types";

interface Props {
  venues: Venue[];
  isVisible: (id: string) => boolean;
  toggle: (id: string) => void;
  showAll: () => void;
  hideAll: (ids: string[]) => void;
  visibleCount: number;
  totalCount: number;
  isFiltered: boolean;
}

export function VenueFilter({
  venues, isVisible, toggle, showAll, hideAll, visibleCount, totalCount, isFiltered,
}: Props) {
  const [open, setOpen] = useState(false);

  const independents = useMemo(
    () =>
      venues
        .filter((v) => v.kind === "independent")
        .sort((a, b) => a.arrondissement - b.arrondissement || a.name.localeCompare(b.name)),
    [venues]
  );

  return (
    <div className="filter">
      <button
        className="filter-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className={isFiltered ? "filter-summary-on" : "filter-summary"}>
          {isFiltered ? `${visibleCount} of ${totalCount} cinemas` : "All cinemas"}
        </span>
        <span className="filter-chevron faint">{open ? "Hide" : "Filter"}</span>
      </button>

      {open && (
        <div className="filter-panel">
          <div className="filter-actions">
            <button className="filter-action" onClick={showAll}>
              Select all
            </button>
            <button
              className="filter-action"
              onClick={() => hideAll(independents.map((v) => v.id))}
            >
              Clear all
            </button>
          </div>

          <div className="filter-chips">
            {independents.map((v) => (
              <button
                key={v.id}
                onClick={() => toggle(v.id)}
                aria-pressed={isVisible(v.id)}
                className={isVisible(v.id) ? "chip chip-on" : "chip"}
              >
                {v.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
