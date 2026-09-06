import { NavLink, useNavigate } from "react-router-dom";

import { clearToken } from "../services/auth";
import "./Sidebar.css";

export function Sidebar() {
  const navigate = useNavigate();

  function logout() {
    clearToken();
    navigate("/login");
  }

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__brand-drop">DROP</span>
        <span aria-hidden="true" className="sidebar__brand-pin">
          📍
        </span>
        <span className="sidebar__brand-by">BY</span>
      </div>
      <span className="sidebar__brand-subtitle">Partner</span>
      <nav className="sidebar__nav">
        <NavLink to="/" end>
          Overview
        </NavLink>
        <NavLink to="/drops" end>
          Manage Drops
        </NavLink>
        <NavLink to="/drops/new">Create Drop</NavLink>
        <NavLink to="/scan">Scan to confirm</NavLink>
        <NavLink to="/queue">Redemption Log</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
      <button type="button" className="sidebar__logout" onClick={logout}>
        Log out
      </button>
    </aside>
  );
}
