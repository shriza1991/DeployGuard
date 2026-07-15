import React, { useState, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  getAggregatorHealth,
  getAgentStatus,
  getDeploymentMetrics,
  listDeployments,
  type DeploymentSummary,
} from '../api/dashboard';
import {
  Shield,
  Activity,
  Database,
  Network,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Terminal,
  FileText,
  BarChart3,
  Rocket,
  History,
  Bot,
  Cpu,
  CheckCircle2,
  XCircle,
  Zap,
  RefreshCw,
} from 'lucide-react';
import './Dashboard.css';

// --- Toast Notification Component ---
interface Toast {
  id: string;
  message: string;
  type: 'success' | 'block' | 'review' | 'info';
}

const PIPELINE_SERVICES = [
  { key: 'kafka', label: 'Kafka', icon: Network },
  { key: 'redis', label: 'Redis', icon: Database },
  { key: 'qdrant', label: 'Qdrant', icon: Cpu },
  { key: 'gateway', label: 'Gateway', icon: Activity },
  { key: 'agents', label: 'Agents', icon: Bot },
  { key: 'aggregator', label: 'Aggregator', icon: Shield },
];

const QUICK_ACTIONS = [
  { label: 'Run Simulation', icon: Terminal, path: '/simulator', primary: true },
  { label: 'View Deployments', icon: Rocket, path: '/deployments', primary: false },
  { label: 'Analytics', icon: BarChart3, path: '/analytics', primary: false },
  { label: 'Generate Report', icon: FileText, path: '/reports', primary: false },
  { label: 'Incident History', icon: History, path: '/incidents', primary: false },
  { label: 'Agent Status', icon: Bot, path: '/agents', primary: false },
  { label: 'System Health', icon: Activity, path: '/system-health', primary: false },
];

function decisionTypeToToastType(decision: string): Toast['type'] {
  if (decision === 'BLOCK') return 'block';
  if (decision === 'REVIEW') return 'review';
  if (decision === 'SAFE') return 'success';
  return 'info';
}

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

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [timePeriod, setTimePeriod] = useState<'24h' | '7d' | '30d'>('7d');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const prevDecisions = useRef<Record<string, string>>({});
  const lastRefresh = useRef<Date>(new Date());

  const showToast = useCallback((message: string, type: Toast['type']) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  // --- Queries ---
  const healthQuery = useQuery({
    queryKey: ['aggregatorHealth'],
    queryFn: getAggregatorHealth,
    refetchInterval: 15_000,
  });
  const backendOnline = healthQuery.data?.status === 'healthy';

  const metricsQuery = useQuery({
    queryKey: ['deploymentMetrics', timePeriod],
    queryFn: () => getDeploymentMetrics({ period: timePeriod }),
    refetchInterval: 15_000,
  });

  const deploymentsQuery = useQuery({
    queryKey: ['dashboardDeployments'],
    queryFn: () => listDeployments({ page: 1, page_size: 8 }),
    refetchInterval: 10_000,
  });

  // React Query v5 alignment: Handle side effects via useEffect instead of onSuccess
  React.useEffect(() => {
    if (deploymentsQuery.data) {
      lastRefresh.current = new Date();
      
      const items = (deploymentsQuery.data?.items ?? []) as DeploymentSummary[];
      const isFirstLoad = Object.keys(prevDecisions.current).length === 0;

      items.forEach(dep => {
        if (!dep.decision) return;
        const prev = prevDecisions.current[dep.correlation_id];
        if (!isFirstLoad && prev !== dep.decision) {
          const repoShort = dep.repository.split('/').pop() ?? dep.repository;
          showToast(
            dep.decision === 'BLOCK'
              ? `🚨 Deployment BLOCKED — ${repoShort}: Risk too high`
              : `Deployment ${dep.decision} — ${repoShort}`,
            decisionTypeToToastType(dep.decision)
          );
        }
        prevDecisions.current[dep.correlation_id] = dep.decision;
      });
    }
  }, [deploymentsQuery.data, showToast]);

  const agentStatusQuery = useQuery({
    queryKey: ['agentStatus'],
    queryFn: getAgentStatus,
    refetchInterval: 15_000,
  });

  const deploymentsList = (deploymentsQuery.data?.items ?? []) as DeploymentSummary[];

  // --- Calculations ---
  const total = metricsQuery.data?.total ?? 0;
  const safe = metricsQuery.data?.safe ?? 0;
  const review = metricsQuery.data?.review ?? 0;
  const blocked = metricsQuery.data?.blocked ?? 0;
  const avgRisk = metricsQuery.data?.avgRisk ?? 0;
  const avgConfidence = metricsQuery.data?.avgConfidence ?? 0;


  // Pipeline health derivation
  const agentsOnline = agentStatusQuery.data?.agents?.every(a => a.status === 'online') ?? false;
  const agentsDegraded = agentStatusQuery.data?.agents?.some(a => a.status === 'degraded') ?? false;

  function getPipelineStatus(key: string): 'online' | 'degraded' | 'offline' | 'unknown' {
    if (!backendOnline) {
      if (key === 'aggregator') return 'offline';
    }
    if (key === 'agents') {
      if (!agentStatusQuery.data) return 'unknown';
      if (agentsOnline) return 'online';
      if (agentsDegraded) return 'degraded';
      return 'offline';
    }
    if (key === 'aggregator') return backendOnline ? 'online' : 'offline';
    if (key === 'kafka' || key === 'redis' || key === 'qdrant' || key === 'gateway') {
      // These are always assumed online if aggregator is online
      return backendOnline ? 'online' : 'offline';
    }
    return 'unknown';
  }

  return (
    <div className="dashboard-container fade-in">

      {/* --- Toast Stack --- */}
      <div className="toast-stack">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast-item toast-${toast.type}`}>
            {toast.type === 'success' && <CheckCircle2 size={14} />}
            {toast.type === 'block' && <XCircle size={14} />}
            {toast.type === 'review' && <AlertTriangle size={14} />}
            {toast.type === 'info' && <Zap size={14} />}
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      {/* ====== SECTION 1: HEADER ====== */}
      <div className="dashboard-header-container">
        <div className="dashboard-header-left">
          <div className="title-area">
            <div className="title-icon-wrapper">
              <Shield className="title-icon" />
            </div>
            <h1>Operations Center</h1>
          </div>
          <p className="description">
            Real-time security auditing and risk gating for your deployment pipeline.
          </p>
        </div>

        <div className="dashboard-header-right">
          {/* System status */}
          <div className={`system-status-chip ${backendOnline ? 'online' : 'offline'}`}>
            <span className={`status-dot ${backendOnline ? 'pulse' : ''}`} />
            <span>{backendOnline ? 'All Systems Online' : 'Backend Unreachable'}</span>
          </div>

          {/* Last sync */}
          <div className="last-sync-chip">
            <RefreshCw size={11} />
            <span>Synced {formatRelativeTime(lastRefresh.current.toISOString())}</span>
          </div>

          {/* Time range selector */}
          <div className="timeframe-selector">
            {(['24h', '7d', '30d'] as const).map(p => (
              <button
                key={p}
                onClick={() => setTimePeriod(p)}
                className={`time-btn ${timePeriod === p ? 'active' : ''}`}
              >
                {p === '24h' ? '24 Hours' : p === '7d' ? '7 Days' : '30 Days'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ====== SECTION 2: LIVE SECURITY SUMMARY (KPI GRID) ====== */}
      <div className="section-block">
        <div className="section-header">
          <span className="section-label">Live Security Summary</span>
          <span className="section-period">{timePeriod}</span>
        </div>
        <div className="kpi-grid-6">
          {/* Total */}
          <div className="kpi-card glass-panel kpi-card--neutral">
            <span className="kpi-title">TOTAL DEPLOYMENTS</span>
            <div className="kpi-value font-mono">{total}</div>
            <p className="kpi-sub">Evaluated in window</p>
          </div>

          {/* Blocked */}
          <div className={`kpi-card glass-panel kpi-card--${blocked > 0 ? 'danger' : 'neutral'}`}>
            <span className="kpi-title">BLOCKED</span>
            <div className="kpi-value font-mono" style={{ color: blocked > 0 ? 'var(--color-block)' : undefined }}>{blocked}</div>
            <p className="kpi-sub">{blocked > 0 ? 'Require immediate action' : 'No blocks in period'}</p>
          </div>

          {/* Under Review */}
          <div className={`kpi-card glass-panel kpi-card--${review > 0 ? 'warn' : 'neutral'}`}>
            <span className="kpi-title">UNDER REVIEW</span>
            <div className="kpi-value font-mono" style={{ color: review > 0 ? 'var(--color-review)' : undefined }}>{review}</div>
            <p className="kpi-sub">Awaiting human review</p>
          </div>

          {/* Safe */}
          <div className="kpi-card glass-panel kpi-card--safe">
            <span className="kpi-title">SAFE</span>
            <div className="kpi-value font-mono" style={{ color: 'var(--color-safe)' }}>{safe}</div>
            <p className="kpi-sub">Clean promotions</p>
          </div>

          {/* Avg Risk */}
          <div className="kpi-card glass-panel kpi-card--neutral">
            <span className="kpi-title">AVG RISK SCORE</span>
            <div className="kpi-value font-mono">
              {avgRisk}
              <span style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 400 }}>/100</span>
            </div>
            <div className="kpi-progress-bar">
              <div className="kpi-progress-fill" style={{
                width: `${avgRisk}%`,
                background: avgRisk >= 60 ? 'var(--color-block)' : avgRisk >= 30 ? 'var(--color-review)' : 'var(--color-safe)'
              }} />
            </div>
          </div>

          {/* Avg Confidence */}
          <div className="kpi-card glass-panel kpi-card--safe">
            <span className="kpi-title">AVG CONFIDENCE</span>
            <div className="kpi-value font-mono" style={{ color: 'var(--color-safe)' }}>
              {Math.round(avgConfidence * 100)}%
            </div>
            <div className="kpi-progress-bar">
              <div className="kpi-progress-fill" style={{ width: `${avgConfidence * 100}%`, background: 'var(--color-safe)' }} />
            </div>
          </div>
        </div>
      </div>

      {/* ====== MAIN CONTENT GRID (Deployments + Pipeline + Actions) ====== */}
      <div className="dashboard-main-grid">

        {/* LEFT COLUMN: Recent Deployments */}
        <div className="dash-col-left">
          <div className="section-block" style={{ height: '100%' }}>
            <div className="section-header">
              <span className="section-label">Recent Deployment Activity</span>
              <button
                onClick={() => navigate('/deployments')}
                className="section-action-btn"
              >
                View All <ChevronRight size={12} />
              </button>
            </div>

            <div className="glass-panel" style={{ overflow: 'hidden' }}>
              {deploymentsQuery.isLoading ? (
                <div className="dash-empty-state">
                  <RefreshCw size={20} className="spinning" />
                  <span>Loading deployment activity...</span>
                </div>
              ) : deploymentsList.length === 0 ? (
                <div className="dash-empty-state dash-empty-state--cta">
                  <Rocket size={28} className="empty-icon" />
                  <h3 className="empty-headline">No deployment analyses yet</h3>
                  <p className="empty-desc">
                    Connect a GitHub repository or run a simulated scan to begin seeing results here.
                  </p>
                  <div className="empty-cta-row">
                    <button onClick={() => navigate('/simulator')} className="btn-primary-stitch font-mono">
                      <Terminal size={13} /> Run Simulation
                    </button>
                    <button onClick={() => navigate('/settings')} className="btn-secondary-stitch font-mono">
                      <Activity size={13} /> Configure
                    </button>
                  </div>
                </div>
              ) : (
                <table className="deploy-table font-mono">
                  <thead>
                    <tr>
                      <th>Repository</th>
                      <th>Decision</th>
                      <th>Risk</th>
                      <th>Branch</th>
                      <th>Time</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {deploymentsList.map(dep => (
                      <tr
                        key={dep.correlation_id}
                        onClick={() => navigate(`/deployments/${dep.correlation_id}`)}
                        className="deploy-row"
                      >
                        <td className="repo-cell">
                          <span className="repo-name">{dep.repository}</span>
                          <span className="repo-id">{dep.correlation_id.substring(0, 8)}…</span>
                        </td>
                        <td>
                          <span className={`verdict-tag-small ${dep.decision?.toLowerCase() || 'pending'}`}>
                            {dep.decision || 'PENDING'}
                          </span>
                        </td>
                        <td>
                          <span className={`score-badge ${(dep.overall_score ?? 0) >= 60 ? 'high' : (dep.overall_score ?? 0) >= 30 ? 'medium' : 'low'}`}>
                            {dep.overall_score ?? '—'}
                          </span>
                        </td>
                        <td className="branch-cell">{dep.branch || '—'}</td>
                        <td className="time-cell">{formatRelativeTime(dep.generated_at)}</td>
                        <td>
                          <ExternalLink size={12} className="row-link-icon" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Pipeline Health + Quick Actions */}
        <div className="dash-col-right">

          {/* SECTION 4: Pipeline Health */}
          <div className="section-block">
            <div className="section-header">
              <span className="section-label">Pipeline Health</span>
            </div>
            <div className="glass-panel" style={{ padding: '16px' }}>
              <div className="pipeline-health-grid">
                {PIPELINE_SERVICES.map(svc => {
                  const status = getPipelineStatus(svc.key);
                  const Icon = svc.icon;
                  return (
                    <div key={svc.key} className="pipeline-service-item">
                      <div className="pipeline-service-left">
                        <Icon size={13} className="pipeline-icon" />
                        <span className="pipeline-label">{svc.label}</span>
                      </div>
                      <div className={`pipeline-status-badge status-${status}`}>
                        <span className={`status-pip ${status !== 'unknown' ? status : 'offline'}`} />
                        <span>{status === 'unknown' ? 'CHECKING' : status.toUpperCase()}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Active agents chips */}
              {agentStatusQuery.data?.agents && agentStatusQuery.data.agents.length > 0 && (
                <div className="agents-row">
                  {agentStatusQuery.data.agents.map(a => (
                    <span key={a.name} className="agent-chip font-mono">
                      <span className={`agent-dot ${a.status}`} />
                      {a.name.replace(' Agent', '')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* SECTION 5: Quick Actions */}
          <div className="section-block">
            <div className="section-header">
              <span className="section-label">Quick Actions</span>
            </div>
            <div className="quick-actions-grid">
              {QUICK_ACTIONS.map(action => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.path}
                    onClick={() => navigate(action.path)}
                    className={`quick-action-btn ${action.primary ? 'quick-action-btn--primary' : 'quick-action-btn--secondary'}`}
                  >
                    <Icon size={14} />
                    <span>{action.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

        </div>
      </div>

    </div>
  );
};
export default Dashboard;
