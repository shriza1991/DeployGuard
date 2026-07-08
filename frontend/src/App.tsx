import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Deployments } from './pages/Deployments';
import { Analytics } from './pages/Analytics';
import { IncidentHistory } from './pages/IncidentHistory';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="deployments" element={<Deployments />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="incident-history" element={<IncidentHistory />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
