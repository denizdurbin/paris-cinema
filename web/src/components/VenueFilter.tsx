import { useMemo, useState } from "react";
import type { Venue } from "../types";
import { ParisMap } from "./ParisMap";

interface Props {
  venues: Venue[];
  isVisible: (id: string) => boolean;
  toggle: (id: string) => void;
  showAll: () => void;
  hideAll: (ids: string[]) => void;
  setVisible: (ids: string[], visible: boolean) => void;
  visibleCount: number;
  totalCount: number;
  isFiltered: boolean;
}

export function VenueFilter({
  venues, isVisible, toggle, showAll, hideAll, setVisible, visibleCount, totalCount, isFiltered,
}: Props) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<"map" | "list">("map");

  const independents = useMemo(
    () =>
      venues
        .filter((v) => v.kind === "independent")
        .sort((a, b) => a.arrondissement - b.arrondissement || a.name.localeCompare(b.name)),
    [venues]
  );

  const groups = useMemo(() => {
    const m = new Map<number, Venue[]>();
    for (const v of independents) {
      const list = m.get(v.arrondissement);
      if (list) list.push(v);
      else m.set(v.arrondissement, [v]);
    }
    return [...m.entries()].sort(([a], [b]) => a - b);
  }, [independents]);

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
            <span className="filter-view-toggle">
              <button
                className={view === "map" ? "filter-view filter-view-on" : "filter-view"}
                onClick={() => setView("map")}
              >
                Map
              </button>
              <button
                className={view === "list" ? "filter-view filter-view-on" : "filter-view"}
                onClick={() => setView("list")}
              >
                List
              </button>
            </span>
          </div>

          {view === "map" ? (
            <ParisMap venues={venues} isVisible={isVisible} toggle={toggle} />
          ) : (
            <div className="filter-groups">
              {groups.map(([arr, arrVenues]) => {
                const ids = arrVenues.map((v) => v.id);
                const allVisible = ids.every((id) => isVisible(id));
                const someVisible = ids.some((id) => isVisible(id));
                return (
                  <div key={arr} className="filter-group">
                    <label className="filter-group-head">
                      <input
                        type="checkbox"
                        checked={allVisible}
                        ref={(el) => { if (el) el.indeterminate = !allVisible && someVisible; }}
                        onChange={() => setVisible(ids, !allVisible)}
                      />
                      <span className="filter-group-label">
                        {arr}<sup>e</sup>
                        <span className="faint">
                          {" "}· {ids.filter((id) => isVisible(id)).length}/{ids.length}
                        </span>
                      </span>
                    </label>
                    <div className="filter-chips">
                      {arrVenues.map((v) => (
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
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
