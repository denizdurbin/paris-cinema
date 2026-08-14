import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

/**
 * BrowserRouter does no scroll management: without this, following a link
 * keeps the previous page's scroll offset and the back button lands at the
 * top instead of where the user was. We keep one saved position per history
 * entry (location.key), restore it on POP (back/forward) and scroll to top
 * on PUSH/REPLACE.
 */
const positions = new Map<string, number>();

if ("scrollRestoration" in window.history) {
  window.history.scrollRestoration = "manual";
}

export function ScrollManager() {
  const { key } = useLocation();
  const navType = useNavigationType();

  // The cleanup runs with the *previous* key just before the new effects,
  // while the window is still scrolled where the user left the old page.
  useEffect(() => {
    return () => {
      positions.set(key, window.scrollY);
    };
  }, [key]);

  useEffect(() => {
    window.scrollTo(0, navType === "POP" ? (positions.get(key) ?? 0) : 0);
  }, [key, navType]);

  return null;
}
