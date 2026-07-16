import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAgentStatus, listDeployments } from '../api/dashboard';
import { Bot, Terminal, Cpu } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { AgentStat } from '../components/AgentStat';
import './Dashboard.css';

const MOCK_AGENT_LOGS: Record<string, string[]> = {
  "Code Risk Agent": [
    "[INFO] Ingress pull request webhook payload parsed successfully.",
    "[INFO] Deterministic scan complete: 0 modified files found.",
    "[INFO] Running Gemini model model-2.5-flash risk assessment...",
    "[INFO] Decision compiled. Risk score: 10, Confidence: 0.65."
  ],
  "Infra Risk Agent": [
    "[INFO] Ingress k8s / TF files parsing complete.",
    "[INFO] Heuristics checks complete: no root / privileged context drifts.",
    "[INFO] Running Gemini infrastructure assessment scan...",
    "[INFO] Decision compiled. Risk score: 0, Confidence: 0.65."
  ],
  "Incident History Agent": [
    "[INFO] Connecting to Qdrant vector space instance collection 'incident_history'...",
    "[INFO] Fetching document embeddings using sentence-transformer model...",
    "[INFO] Vector matches lookup complete. Hits: 0.",
    "[INFO] Decision compiled. Risk score: 10, Confidence: 0.35."
  ]
};

function formatRelativeTime(isoStr?: string): string {
  if (!isoStr) return '';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(isoStr).toLocaleDateString();
}

export const Agents: React.FC = () => {
  // Poll agent status every 5 seconds
  const agentQuery = useQuery({
    queryKey: ['agentStatusList'],
    queryFn: getAgentStatus,
    refetchInterval: 5000,
  });

  // Query deployments to compute live stats
  const deploymentsQuery = useQuery({
    queryKey: ['deploymentsForAgentStats'],
    queryFn: () => listDeployments({ page: 1, page_size: 100 }),
    refetchInterval: 10_000,
  });

  const agents = agentQuery.data?.agents ?? [];
  const deployments = deploymentsQuery.data?.items ?? [];
  const totalScans = deploymentsQuery.data?.total ?? 0;

  // Compute live confidence mean
  const confidences = deployments
    .map(d => d.overall_confidence)
    .filter(c => c !== undefined && c !== null) as number[];
  const liveAvgConfidence = confidences.length > 0
    ? `${Math.round((confidences.reduce((sum, val) => sum + val, 0) / confidences.length) * 100)}%`
    : '--';

  // Compute relative time of last analysis run
  const liveLastRun = deployments.length > 0 && deployments[0].generated_at
    ? formatRelativeTime(deployments[0].generated_at)
    : '--';

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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
            {agents.map((agent) => {
              const logs = MOCK_AGENT_LOGS[agent.name] || [];

              return (
                <div 
                  key={agent.name} 
                  className="glass-panel" 
                  style={{ 
                    padding: '24px', 
                    display: 'flex', 
                    flexDirection: 'column', 
                    justifyContent: 'space-between',
                    minHeight: '480px',
                    boxSizing: 'border-box'
                  }}
                >
                  
                  {/* Card top info */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <div style={{ 
                          background: 'rgba(192, 193, 255, 0.05)', 
                          border: '1px solid rgba(192, 193, 255, 0.1)', 
                          padding: '8px', 
                          borderRadius: '6px',
                          color: 'var(--accent-cyan)'
                        }}>
                          <Cpu size={20} />
                        </div>
                        <div>
                          <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600, margin: 0 }}>{agent.name}</h3>
                          <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                            Region: {agent.region || 'local'}
                          </span>
                        </div>
                      </div>
                      <StatusBadge status={agent.status} />
                    </div>

                    {/* Stats Grid */}
                    <div style={{ 
                      display: 'grid', 
                      gridTemplateColumns: '1fr 1fr', 
                      gap: '16px 12px', 
                      marginBottom: '20px', 
                      borderTop: '1px solid var(--panel-border)', 
                      paddingTop: '16px' 
                    }}>
                      <AgentStat label="Last Run" value={liveLastRun} />
                      <AgentStat label="Average Latency" value={`${agent.latency_ms} ms`} />
                      <AgentStat label="Analysis Count" value={totalScans > 0 ? totalScans.toLocaleString() : '--'} />
                      <AgentStat label="Average Confidence" value={liveAvgConfidence} />
                      
                      {/* Hardware / Environment (unexposed in API - gracefully show '--') */}
                      <AgentStat label="Version" value="--" />
                      <AgentStat label="Uptime" value="--" />
                      <AgentStat label="CPU Usage" value="--" />
                      <AgentStat label="Memory Usage" value="--" />
                    </div>
                  </div>

                  {/* Terminal Stds / Logs block */}
                  <div style={{ marginTop: 'auto' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                      <Terminal size={12} style={{ color: 'var(--accent-cyan)' }} />
                      <span style={{ fontSize: '11px', fontWeight: 600 }} className="font-mono">CONSOLE LOGS:</span>
                    </div>
                    <div style={{ 
                      background: 'var(--bg-secondary)', 
                      border: '1px solid var(--panel-border)', 
                      padding: '12px', 
                      borderRadius: '4px', 
                      height: '130px', 
                      overflowY: 'auto',
                      boxSizing: 'border-box'
                    }} className="font-mono">
                      {logs.map((log, idx) => (
                        <p key={idx} style={{ fontSize: '10px', color: 'rgba(192, 193, 255, 0.7)', margin: '4px 0', lineHeight: 1.4 }}>
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
