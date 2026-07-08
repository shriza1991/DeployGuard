import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Rocket, BarChart3, History, ShieldCheck } from 'lucide-react';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-brand">
        <ShieldCheck className="brand-icon" />
        <span className="brand-text">Deploy<span>Guard</span></span>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink 
          to="/" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <LayoutDashboard className="nav-icon" />
          <span>Dashboard</span>
        </NavLink>
        
        <NavLink 
          to="/deployments" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Rocket className="nav-icon" />
          <span>Deployments</span>
        </NavLink>
        
        <NavLink 
          to="/analytics" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <BarChart3 className="nav-icon" />
          <span>Analytics</span>
        </NavLink>
        
        <NavLink 
          to="/incident-history" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <History className="nav-icon" />
          <span>Incident History</span>
        </NavLink>
      </nav>
      
      <div className="sidebar-footer">
        <div className="platform-tag">v1.0.0-Beta</div>
      </div>
    </aside>
  );
};
