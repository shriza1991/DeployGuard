import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAgentStatus } from '../api/dashboard';
import { Bot, Terminal, Cpu } from 'lucide-react';
import './Dashboard.css'; // Unify styles

const MOCK_AGENT_EXTRA: Record<string, {
  lastRun: string;
  totalAnalyses: number;
  avgConfidence: string;
  uptime: string;
  specs: string;
  logs: string[];
}> = {
  "Code Risk Agent": {
    lastRun: "2 mins ago",
    totalAnalyses: 1245,
    avgConfidence: "94.2%",
    uptime: "99.98%",
    specs: "v1.2.0 • 0.2 CPU • 182 MB",
    logs: [
      "[INFO] 14:54:26.110 - Ingress pull request webhook payload parsed successfully.",
      "[INFO] 14:54:26.150 - Deterministic scan complete: 0 modified files found.",
      "[INFO] 14:54:26.210 - Running Gemini model model-2.5-flash risk assessment...",
      "[INFO] 14:54:26.230 - Decision compiled. Risk score: 10, Confidence: 0.65."
    ]
  },
  "Infra Risk Agent": {
    lastRun: "2 mins ago",
    totalAnalyses: 1245,
    avgConfidence: "89.5%",
    uptime: "99.99%",
    specs: "v1.2.0 • 0.1 CPU • 165 MB",
    logs: [
      "[INFO] 14:54:24.780 - Ingress k8s / TF files parsing complete.",
      "[INFO] 14:54:24.810 - Heuristics checks complete: no root / privileged context drifts.",
      "[INFO] 14:54:24.902 - Running Gemini infrastructure assessment scan...",
      "[INFO] 14:54:24.910 - Decision compiled. Risk score: 0, Confidence: 0.65."
    ]
  },
  "Incident History Agent": {
    lastRun: "2 mins ago",
    totalAnalyses: 1245,
    avgConfidence: "92.4%",
    uptime: "99.95%",
    specs: "v1.1.4 • 0.4 CPU • 342 MB",
    logs: [
      "[INFO] 14:54:21.210 - Connecting to Qdrant vector space instance collection 'incident_history'...",
      "[INFO] 14:54:21.503 - Fetching document embeddings using sentence-transformer model...",
      "[INFO] 14:54:21.782 - Vector matches lookup complete. Hits: 0.",
      "[INFO] 14:54:21.846 - Decision compiled. Risk score: 10, Confidence: 0.35."
    ]
  }
};

export const Agents: React.FC = () => {
  const agentQuery = useQuery({
    queryKey: ['agentStatusList'],
    queryFn: getAgentStatus,
    refetchInterval: 15_000,
  });

  const agents = agentQuery.data?.agents ?? [];

  return (
    <div className="dashboard-container fade-in">
      
      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '24px' }}>
        <div className="dashboard-header-left">
          <div className="title-area" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Bot size={24} className="text-indigo" />
            <h1>Distributed AI Agents</h1>
          </div>
          <p className="description">
            Monitor, inspect, and trace execution logs for risk gate evaluation workers.
          </p>
        </div>
      </div>

      {agentQuery.isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', gap: '16px', color: 'var(--text-muted)' }}>
          <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
          <span>Connecting to agent fleet...</span>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          
          {/* Agent Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
            {agents.map((agent) => {
              const extra = MOCK_AGENT_EXTRA[agent.name] || {
                lastRun: 'unknown',
                totalAnalyses: 0,
                avgConfidence: '0.0%',
                uptime: '100%',
                specs: 'N/A',
                logs: []
              };

              return (
                <div key={agent.name} className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  
                  {/* Card top info */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <Cpu className="text-indigo" size={20} />
                        <div>
                          <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600 }}>{agent.name}</h3>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{extra.specs}</span>
                        </div>
                      </div>
                      <span className="confidence-badge font-mono" style={{ background: agent.status === 'online' ? 'var(--color-safe-bg)' : 'var(--color-review-bg)', color: agent.status === 'online' ? 'var(--color-safe)' : 'var(--color-review)', fontSize: '10px' }}>
                        {agent.status.toUpperCase()}
                      </span>
                    </div>

                    {/* Stats table */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px', borderTop: '1px solid var(--panel-border)', paddingTop: '16px' }}>
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>LAST RUN</span>
                        <p className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold', marginTop: '2px' }}>{extra.lastRun}</p>
                      </div>
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>LATENCY</span>
                        <p className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold', marginTop: '2px' }}>{agent.latency_ms} ms</p>
                      </div>
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>TOTAL ANALYSES</span>
                        <p className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold', marginTop: '2px' }}>{extra.totalAnalyses}</p>
                      </div>
                      <div>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>AVG CONFIDENCE</span>
                        <p className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold', marginTop: '2px' }}>{extra.avgConfidence}</p>
                      </div>
                    </div>
                  </div>

                  {/* Terminal Stds / Logs block */}
                  <div style={{ marginTop: 'auto' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                      <Terminal size={12} />
                      <span style={{ fontSize: '11px', fontWeight: 600 }} className="font-mono">STDERR/STDOUT OUTPUT:</span>
                    </div>
                    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', padding: '10px', borderRadius: '4px', height: '120px', overflowY: 'auto' }} className="font-mono">
                      {extra.logs.map((log, idx) => (
                        <p key={idx} style={{ fontSize: '10px', color: '#88f', margin: '2px 0', lineHeight: 1.4 }}>
                          {log}
                        </p>
                      ))}
                    </div>
                  </div>

                </div>
              );
            })}
          </div>

        </div>
      )}

    </div>
  );
};
export default Agents;
