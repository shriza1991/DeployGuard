import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import './Layout.css';

export const Layout: React.FC = () => {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="layout-content">
        <TopNavbar />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
