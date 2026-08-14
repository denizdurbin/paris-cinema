import type { ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

/**
 * A back link that behaves like the browser back button: a real POP, so the
 * ScrollManager can restore the previous page's scroll position. A plain
 * `<Link to="..">` would PUSH a fresh entry and land at the top instead.
 * On a direct visit (no in-app history) it falls back to the parent page.
 */
export function BackLink({ to, className, children }: {
  to: string;
  className?: string;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Link
      to={to}
      className={className}
      onClick={(e) => {
        // The initial history entry has the key "default"; anything else
        // means the user arrived from inside the app and can go back.
        if (location.key === "default") return;
        e.preventDefault();
        navigate(-1);
      }}
    >
      {children}
    </Link>
  );
}
