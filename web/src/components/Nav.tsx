import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/", label: "Now", end: true },
  { to: "/week", label: "Week", end: false },
  { to: "/cinemas", label: "Cinemas", end: false },
  { to: "/chains", label: "UGC & MK2", end: false },
];

export function Nav() {
  return (
    <nav className="nav">
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          end={t.end}
          className={({ isActive }) => (isActive ? "nav-item nav-item-on" : "nav-item")}
        >
          {t.label}
        </NavLink>
      ))}
    </nav>
  );
}
