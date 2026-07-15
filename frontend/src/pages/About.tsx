import React from 'react';
import { Info, Cpu, Database, Network } from 'lucide-react';
import './Dashboard.css';

export const About: React.FC = () => {
  return (
    <div className="dashboard-container fade-in" style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '48px' }}>
      
      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '24px' }}>
        <div className="dashboard-header-left">
          <div className="title-area" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Info size={24} className="text-indigo" />
            <h1>Architecture Documentation</h1>
          </div>
          <p className="description">
            Technical specification of the DeployGuard risk gating pipeline, AI agents, and platform stack.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* Core Overview */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', color: '#fff', fontWeight: 600, marginBottom: '12px' }}>Platform Concept</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            DeployGuard is an agentic, pre-deployment risk gating system designed to intercept GitHub push events and perform deep, multi-dimensional security audits before a build is promoted to production. By combining static code scans, infrastructure configuration checks, and semantic matching against historical incidents, DeployGuard provides high-fidelity, explainable risk assessments within seconds.
          </p>
        </div>

        {/* Pipeline Architecture Diagram (Visual) */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', color: '#fff', fontWeight: 600, marginBottom: '16px' }}>Distributed Pipeline Workflow</h3>
          
          {/* Simple premium ASCII/Box flow design */}
          <div className="font-mono" style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '6px', border: '1px solid var(--panel-border)', overflowX: 'auto', fontSize: '11px', lineHeight: 1.5, color: 'var(--accent-cyan)' }}>
            {`  [ GitHub Push Webhook ]
             ↓
     [ API Gateway Ingress (port 8000) ]
             ↓
     [ Kafka Message Bus (deployment-events queue) ]
             ↓
    ┌─────────────────────────┼─────────────────────────┐
    ↓                         ↓                         ↓
[ Code Risk Agent ]     [ Infra Risk Agent ]     [ Incident History Agent ]
(Vulnerabilities check)  (Kubernetes/IaC drift)    (Outages vector lookup)
    │                         │                         │
    └─────────────────────────┼─────────────────────────┘
                              ↓
                  [ Redis cache channels ]
                              ↓
             [ Decision Aggregator (port 8002) ]
                              ↓
              [ Decision Verdict: SAFE / BLOCK ]`}
          </div>
        </div>

        {/* Agent Profiles */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', color: '#fff', fontWeight: 600, marginBottom: '16px' }}>AI Security Agent Profiles</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <div style={{ background: 'rgba(78, 222, 163, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(78, 222, 163, 0.2)' }}>
                <Cpu size={16} className="text-green" />
              </div>
              <div>
                <h4 style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>Static Analysis Agent (Code Risk)</h4>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
                  Scans modified file diffs for hardcoded secrets, api keys, disabled oauth configurations, vulnerable dependencies, and general programming security defects.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', borderTop: '1px solid var(--panel-border)', paddingTop: '16px' }}>
              <div style={{ background: 'rgba(255, 185, 95, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(255, 185, 95, 0.2)' }}>
                <Network size={16} className="text-yellow" />
              </div>
              <div>
                <h4 style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>Infrastructure Configuration Agent (Infra Risk)</h4>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
                  Audits Helm charts, Terraform templates, Dockerfiles, and Kubernetes manifests for security context vulnerabilities (e.g., privileged containers, hostNamespace bindings).
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', borderTop: '1px solid var(--panel-border)', paddingTop: '16px' }}>
              <div style={{ background: 'rgba(192, 193, 255, 0.05)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(192, 193, 255, 0.2)' }}>
                <Database size={16} className="text-indigo" />
              </div>
              <div>
                <h4 style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>Regression Similarity Agent (Incident History)</h4>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
                  Translates pull request content into dense vector embeddings and queries a Qdrant database to calculate similarity scores against historical outage databases.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Tech Stack Details */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', color: '#fff', fontWeight: 600, marginBottom: '16px' }}>Core Technologies Stack</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }} className="font-mono text-center">
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--panel-border)', borderRadius: '6px' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>SERVICES</span>
              <p style={{ fontSize: '12px', color: '#fff', marginTop: '4px', fontWeight: 'bold' }}>FastAPI / Python</p>
            </div>
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--panel-border)', borderRadius: '6px' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>STREAMING</span>
              <p style={{ fontSize: '12px', color: '#fff', marginTop: '4px', fontWeight: 'bold' }}>Apache Kafka</p>
            </div>
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--panel-border)', borderRadius: '6px' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>CACHE &amp; STATE</span>
              <p style={{ fontSize: '12px', color: '#fff', marginTop: '4px', fontWeight: 'bold' }}>Redis In-Memory</p>
            </div>
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--panel-border)', borderRadius: '6px' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>VECTOR INDEX</span>
              <p style={{ fontSize: '12px', color: '#fff', marginTop: '4px', fontWeight: 'bold' }}>Qdrant DB</p>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
};
export default About;
