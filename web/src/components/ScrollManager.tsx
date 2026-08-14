import { useLayoutEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

/**
 * BrowserRouter does no scroll management: without this, following a link
 * keeps the previous page's scroll offset and the back button lands at the
 * top instead of where the user was. We record the scroll position of every
 * history entry (keyed by location.key) as the user scrolls, restore it on
 * POP (back/forward) and scroll to top on PUSH/REPLACE.
 *
 * Everything runs in layout effects: the scroll is applied synchronously
 * before paint (no flash at the wrong offset), and the previous entry's
 * scroll listener is detached at commit time — before the browser can fire
 * a clamping scroll event for a shorter new page, which would otherwise
 * overwrite the old entry's true position.
 */
const positions = new Map<string, number>();

if ("scrollRestoration" in window.history) {
  window.history.scrollRestoration = "manual";
}

export function ScrollManager() {
  const { key } = useLocation();
  const navType = useNavigationType();

  useLayoutEffect(() => {
    const save = () => positions.set(key, window.scrollY);
    window.addEventListener("scroll", save, { passive: true });
    return () => window.removeEventListener("scroll", save);
  }, [key]);

  useLayoutEffect(() => {
    window.scrollTo(0, navType === "POP" ? (positions.get(key) ?? 0) : 0);
  }, [key, navType]);

  return null;
}
