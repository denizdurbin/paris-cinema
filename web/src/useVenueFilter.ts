import { useCallback, useEffect, useMemo, useState } from "react";
import type { Venue } from "./types";

export const STORAGE_KEY = "paris-cinema:hidden-venues";

/** Reads the persisted hidden set, tolerating absent or corrupt storage. */
function readHidden(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === "string"));
  } catch {
    return new Set();
  }
}

export function useVenueFilter(allVenues: Venue[]) {
  const [hidden, setHidden] = useState<Set<string>>(readHidden);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...hidden]));
    } catch {
      // Private browsing or a full quota. Filtering still works for this
      // session; only persistence is lost, which is not worth crashing over.
    }
  }, [hidden]);

  const independents = useMemo(
    () => allVenues.filter((v) => v.kind === "independent"),
    [allVenues]
  );

  const isVisible = useCallback((id: string) => !hidden.has(id), [hidden]);

  const toggle = useCallback((id: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const showAll = useCallback(() => setHidden(new Set()), []);

  const hideAll = useCallback((ids: string[]) => setHidden(new Set(ids)), []);

  /** Sets visibility for a set of ids at once (used by arrondissement group toggles). */
  const setVisible = useCallback((ids: string[], visible: boolean) => {
    setHidden((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (visible) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }, []);

  const visibleCount = independents.filter((v) => !hidden.has(v.id)).length;

  return {
    hidden,
    isVisible,
    toggle,
    showAll,
    hideAll,
    setVisible,
    visibleCount,
    totalCount: independents.length,
    isFiltered: visibleCount < independents.length,
  };
}
