import React from 'react';
import { Cpu, Database, Network } from 'lucide-react';
import './TopNavbar.css';

export const TopNavbar: React.FC = () => {
  return (
    <header className="top-navbar glass-panel">
      <div className="navbar-left">
        <div className="workspace-selector">
          <span className="workspace-label">Repository:</span>
          <span className="workspace-value">shriza1991/DeployGuard</span>
        </div>
      </div>
      
      <div className="navbar-right">
        <div className="platform-health">
          <div className="health-indicator pulse"></div>
          <span className="health-label">System Healthy</span>
        </div>
        
        <div className="services-grid">
          <div className="service-badge active" title="Kafka Message Broker Connected">
            <Network className="badge-icon" />
            <span>KAFKA</span>
          </div>
          <div className="service-badge active" title="Redis Cache Store Connected">
            <Database className="badge-icon" />
            <span>REDIS</span>
          </div>
          <div className="service-badge active" title="Qdrant Vector DB Connected">
            <Cpu className="badge-icon" />
            <span>QDRANT</span>
          </div>
        </div>
      </div>
    </header>
  );
};
