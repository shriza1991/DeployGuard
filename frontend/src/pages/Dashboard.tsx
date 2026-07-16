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
import { getRepositoryStatus, getRepositoryManifest, getRepositoryStats } from '../api/repository';
import {
  Shield,
  Activity,
  Database,
  Network,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Terminal,
  BarChart3,
  Rocket,
  History,
  Bot,
  Cpu,
  CheckCircle2,
  XCircle,
  Zap,
  RefreshCw,
  Search,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import { QuickActionCard } from '../components/QuickActionCard';
import { HealthIndicator } from '../components/HealthIndicator';
import './Dashboard.css';

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

  const repoName = 'shriza1991/DeployGuard';
  const branchName = 'main';

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
    refetchInterval: 5000, // Faster polling (5 seconds)
  });
  const backendOnline = healthQuery.data?.status === 'healthy';

  const metricsQuery = useQuery({
    queryKey: ['deploymentMetrics', timePeriod],
    queryFn: () => getDeploymentMetrics({ period: timePeriod }),
    refetchInterval: 15_000,
  });

  const deploymentsQuery = useQuery({
    queryKey: ['dashboardDeployments'],
    queryFn: () => listDeployments({ page: 1, page_size: 6 }),
    refetchInterval: 5000, // Poll recent deployments every 5s
  });

  const repoStatusQuery = useQuery({
    queryKey: ['repoStatus', repoName, branchName],
    queryFn: () => getRepositoryStatus(repoName, branchName),
    refetchInterval: 5000,
  });

  const repoManifestQuery = useQuery({
    queryKey: ['repoManifest', repoName, branchName],
    queryFn: () => getRepositoryManifest(repoName, branchName),
    refetchInterval: 10000,
  });

  const repoStatsQuery = useQuery({
    queryKey: ['repoStats', repoName, branchName],
    queryFn: () => getRepositoryStats(repoName, branchName),
    refetchInterval: 10000,
  });

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
    refetchInterval: 5000, // Poll agents status every 5 seconds
  });

  const deploymentsList = (deploymentsQuery.data?.items ?? []) as DeploymentSummary[];

  // --- Calculations ---
  const total = metricsQuery.data?.total ?? 0;
  const safe = metricsQuery.data?.safe ?? 0;
  const review = metricsQuery.data?.review ?? 0;
  const blocked = metricsQuery.data?.blocked ?? 0;
  const avgRisk = metricsQuery.data?.avgRisk ?? 0;
  const avgConfidence = metricsQuery.data?.avgConfidence ?? 0;

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
      return backendOnline ? 'online' : 'offline';
    }
    return 'unknown';
  }

  const quickActionsList = [
    { label: 'Run Simulation', description: 'Simulate deployment webhook scans', icon: Terminal, path: '/simulator', primary: true },
    { label: 'Repo Search', description: 'Query repo vectors for logic patterns', icon: Search, path: '/search', primary: false },
    { label: 'View Analytics', description: 'Review security statistics & risk metrics', icon: BarChart3, path: '/analytics', primary: false },
    { label: 'Incident History', description: 'Inspect past production outage rollbacks', icon: History, path: '/incidents', primary: false },
    { label: 'Agent Status', description: 'Monitor worker logs & health endpoints', icon: Bot, path: '/agents', primary: false },
    { label: 'System Health', description: 'Track status of Redis, Qdrant, and Kafka', icon: Activity, path: '/system-health', primary: false },
  ];

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

      {/* ====== SECTION 1: HEADER & SYSTEM HEALTH ====== */}
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
          <HealthIndicator
            status={backendOnline ? 'online' : 'offline'}
            label={backendOnline ? 'All Systems Online' : 'Backend Unreachable'}
            type="chip"
          />

          <div className="last-sync-chip">
            <RefreshCw size={11} />
            <span>Synced {formatRelativeTime(lastRefresh.current.toISOString())}</span>
          </div>

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

      {/* ====== SECTION 2: REPOSITORY CONTEXT & QUICK ACTIONS ====== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        
        {/* Repository Context Card */}
        <div className="section-block">
          <div className="section-header">
            <span className="section-label">Repository Context</span>
          </div>
          <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', minHeight: '180px', justifyContent: 'center' }}>
            { (repoStatusQuery.isLoading || repoManifestQuery.isLoading || repoStatsQuery.isLoading) ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
                <span style={{ animation: 'spin 1s linear infinite', fontSize: '16px' }}>⏳</span>
                <span style={{ fontSize: '11px' }}>Loading repository context...</span>
              </div>
            ) : (repoStatusQuery.isError || repoManifestQuery.isError || repoStatsQuery.isError) ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--accent-red)' }}>
                <span style={{ fontSize: '16px' }}>⚠️</span>
                <span style={{ fontSize: '11px', textAlign: 'center' }}>Failed to load repository context</span>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Repository</span>
                  <span className="font-mono" style={{ fontSize: '13px', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                    {repoName}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Status</span>
                  <StatusBadge status={repoStatusQuery.data?.status === 'completed' ? 'ONLINE' : (repoStatusQuery.data?.status === 'indexing' ? 'INDEXING' : (repoStatusQuery.data?.status === 'failed' ? 'FAILED' : 'NOT_INDEXED'))} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Files Indexed</span>
                  <span className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 600 }}>
                    {repoStatsQuery.data?.number_of_files !== undefined ? repoStatsQuery.data.number_of_files : '--'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Lines of Code</span>
                  <span className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 600 }}>
                    {repoStatsQuery.data?.lines_of_code !== undefined ? repoStatsQuery.data.lines_of_code.toLocaleString() : '--'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Frameworks</span>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {repoManifestQuery.data?.frameworks && repoManifestQuery.data.frameworks.length > 0 ? (
                      repoManifestQuery.data.frameworks.map(fw => (
                        <span key={fw} className="agent-chip font-mono" style={{ margin: 0, padding: '1px 6px', fontSize: '9px' }}>
                          {fw}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>--</span>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Last Indexed</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {repoManifestQuery.data?.last_indexed ? formatRelativeTime(repoManifestQuery.data.last_indexed) : '--'}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Quick Actions Grid */}
        <div className="section-block">
          <div className="section-header">
            <span className="section-label">Quick Actions</span>
          </div>
          <div className="quick-actions-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
            {quickActionsList.map(action => (
              <QuickActionCard
                key={action.path}
                label={action.label}
                description={action.description}
                icon={action.icon}
                onClick={() => navigate(action.path)}
                primary={action.primary}
              />
            ))}
          </div>
        </div>

      </div>

      {/* ====== SECTION 3: RECENT DEPLOYMENTS (LATEST DECISIONS) ====== */}
      <div className="section-block">
        <div className="section-header">
          <span className="section-label">Latest Deployment Decisions</span>
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
              <span>Loading deployment decisions...</span>
            </div>
          ) : deploymentsList.length === 0 ? (
            <div className="dash-empty-state dash-empty-state--cta">
              <Rocket size={28} className="empty-icon" />
              <h3 className="empty-headline">No deployment decisions logged</h3>
              <p className="empty-desc">
                Trigger a scan from the webhook simulator to evaluate security outcomes.
              </p>
              <div className="empty-cta-row">
                <button onClick={() => navigate('/simulator')} className="btn-primary-stitch font-mono">
                  <Terminal size={13} /> Run Simulation
                </button>
              </div>
            </div>
          ) : (
            <table className="deploy-table font-mono">
              <thead>
                <tr>
                  <th>Repository</th>
                  <th>Decision</th>
                  <th>Risk Score</th>
                  <th>Branch</th>
                  <th>Time Evaluated</th>
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
                      <StatusBadge status={dep.decision || 'PENDING'} />
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

      {/* ====== SECTION 4: SYSTEM HEALTH & AGENT STATUS ====== */}
      <div className="dashboard-main-grid">
        
        {/* Left Column: Pipeline Health */}
        <div className="dash-col-left">
          <div className="section-block">
            <div className="section-header">
              <span className="section-label">Pipeline System Health</span>
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
                      <HealthIndicator status={status} />
                    </div>
                  );
                })}
              </div>

              {/* Active Agent Chips */}
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
        </div>

        {/* Right Column: Deployment Statistics / Analytics */}
        <div className="dash-col-right">
          <div className="section-block">
            <div className="section-header">
              <span className="section-label">Deployment Statistics</span>
              <span className="section-period">{timePeriod}</span>
            </div>
            <div className="kpi-grid-6" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
              
              <MetricCard
                title="TOTAL SCAN VOLUME"
                value={total}
                subtitle="Scans evaluated"
              />

              <MetricCard
                title="BLOCKED OUTCOMES"
                value={blocked}
                subtitle="High-risk scans rejected"
                type={blocked > 0 ? 'danger' : 'neutral'}
                valueStyle={blocked > 0 ? { color: 'var(--color-block)' } : undefined}
              />

              <MetricCard
                title="UNDER REVIEW"
                value={review}
                subtitle="Manual verification cases"
                type={review > 0 ? 'warn' : 'neutral'}
                valueStyle={review > 0 ? { color: 'var(--color-review)' } : undefined}
              />

              <MetricCard
                title="CLEAN PROMOTIONS"
                value={safe}
                subtitle="Scans promoted safe"
                type="safe"
                valueStyle={{ color: 'var(--color-safe)' }}
              />

              <MetricCard
                title="AVG PIPELINE RISK"
                value={
                  <>
                    {avgRisk}
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 400 }}>/100</span>
                  </>
                }
                subtitle="Overall pipeline score mean"
                progress={avgRisk}
                progressColor={avgRisk >= 60 ? 'var(--color-block)' : avgRisk >= 30 ? 'var(--color-review)' : 'var(--color-safe)'}
              />

              <MetricCard
                title="AVG CONFIDENCE INDEX"
                value={`${Math.round(avgConfidence * 100)}%`}
                subtitle="Model validation average"
                type="safe"
                progress={avgConfidence * 100}
                progressColor="var(--color-safe)"
                valueStyle={{ color: 'var(--color-safe)' }}
              />

            </div>
          </div>
        </div>

      </div>

    </div>
  );
};

export default Dashboard;
