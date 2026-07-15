import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Settings,
  Info,
  ShieldCheck,
} from 'lucide-react';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-brand">
        <ShieldCheck className="brand-icon" />
        <span className="brand-text">Deploy<span>Guard</span></span>
      </div>

      <nav className="sidebar-nav">
        {/* Primary Navigation */}
        <div className="nav-section-label">Navigation</div>

        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <LayoutDashboard className="nav-icon" />
          <span>Dashboard</span>
        </NavLink>

        {/* Utility Section */}
        <div className="nav-section-label" style={{ marginTop: '16px' }}>Configuration</div>

        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Settings className="nav-icon" />
          <span>Settings</span>
        </NavLink>

        <NavLink
          to="/about"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Info className="nav-icon" />
          <span>About</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="platform-tag">v1.0.0-Beta</div>
      </div>
    </aside>
  );
};
