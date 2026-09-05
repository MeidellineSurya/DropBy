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
        <span className="sidebar__brand-mark">D</span>
        <div>
          <span className="sidebar__brand-eyebrow">DROPBY</span>
          <span className="sidebar__brand-name">Partner</span>
        </div>
      </div>
      <nav className="sidebar__nav">
        <NavLink to="/" end>
          Overview
        </NavLink>
        <NavLink to="/drops" end>
          Drops
        </NavLink>
        <NavLink to="/drops/new">Create Drop</NavLink>
        <NavLink to="/queue">Live Queue</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
      </nav>
      <button type="button" className="sidebar__logout" onClick={logout}>
        Log out
      </button>
    </aside>
  );
}
