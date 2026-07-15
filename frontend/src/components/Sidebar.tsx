import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Rocket,
  BarChart3,
  Bot,
  History,
  Activity,
  Terminal,
  ClipboardList,
  Settings,
  Info,
  ShieldCheck
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
          to="/agents" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Bot className="nav-icon" />
          <span>Agents</span>
        </NavLink>
        
        <NavLink 
          to="/incidents" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <History className="nav-icon" />
          <span>Incidents</span>
        </NavLink>
        
        <NavLink 
          to="/system-health" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Activity className="nav-icon" />
          <span>System Health</span>
        </NavLink>
        
        <NavLink 
          to="/simulator" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Terminal className="nav-icon" />
          <span>Webhook Simulator</span>
        </NavLink>
        
        <NavLink 
          to="/reports" 
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <ClipboardList className="nav-icon" />
          <span>Reports</span>
        </NavLink>
        
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
