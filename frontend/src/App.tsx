import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Deployments } from './pages/Deployments';
import { DeploymentDetails } from './pages/DeploymentDetails';
import { Analytics } from './pages/Analytics';
import { Agents } from './pages/Agents';
import { Incidents } from './pages/Incidents';
import { SystemHealth } from './pages/SystemHealth';
import { WebhookSimulator } from './pages/WebhookSimulator';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { About } from './pages/About';
import { SearchRepository } from './pages/SearchRepository';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="deployments" element={<Deployments />} />
          <Route path="deployments/:id" element={<DeploymentDetails />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="agents" element={<Agents />} />
          <Route path="incidents" element={<Incidents />} />
          <Route path="system-health" element={<SystemHealth />} />
          <Route path="simulator" element={<WebhookSimulator />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="about" element={<About />} />
          <Route path="search" element={<SearchRepository />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
