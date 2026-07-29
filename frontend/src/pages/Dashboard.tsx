import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  getAggregatorHealth,
  getAgentStatus,
  getDeploymentMetrics,
  listDeployments,
  type DeploymentSummary,
  type AgentStatusItem,
} from '../api/dashboard';
import { getRepositoryStatus, getRepositoryManifest, getRepositoryStats } from '../api/repository';
import { normalizeConfidence, getConfidenceColor } from '../utils/confidence';
import {
  Shield,
  Activity,
  Database,
  Network,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Terminal,
  Rocket,
  Bot,
  Cpu,
  CheckCircle2,
  XCircle,
  Zap,
  RefreshCw,
  GitBranch,
  Search,
  TrendingUp,
  Clock,
  Play,
  RotateCcw,
  FileText,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import { HealthIndicator } from '../components/HealthIndicator';
import './Dashboard.css';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'block' | 'review' | 'info';
}

interface ActivityEvent {
  id: string;
  icon: React.ReactNode;
  label: string;
  timestamp: string;
  type: 'safe' | 'block' | 'review' | 'info';
}

// ─── Constants ───────────────────────────────────────────────────────────────

const PIPELINE_SERVICES = [
  { key: 'kafka',       label: 'Kafka',       icon: Network   },
  { key: 'redis',       label: 'Redis',       icon: Database  },
  { key: 'qdrant',      label: 'Qdrant',      icon: Cpu       },
  { key: 'gateway',     label: 'Gateway',     icon: Activity  },
  { key: 'aggregator',  label: 'Aggregator',  icon: Shield    },
  { key: 'agents',      label: 'Agents',      icon: Bot       },
];

const AGENT_DISPLAY: Record<string, { label: string; short: string }> = {
  'Code Risk Agent':        { label: 'Code Risk',     short: 'code-risk'     },
  'Infra Risk Agent':       { label: 'Infra Risk',    short: 'infra-risk'    },
  'Incident History Agent': { label: 'Incident Risk', short: 'incident-risk' },
};

// ─── Utilities ───────────────────────────────────────────────────────────────

function decisionToToastType(d: string): Toast['type'] {
  if (d === 'BLOCK')  return 'block';
  if (d === 'REVIEW') return 'review';
  if (d === 'SAFE')   return 'success';
  return 'info';
}

function decisionToActivityType(d: string): ActivityEvent['type'] {
  if (d === 'BLOCK')  return 'block';
  if (d === 'REVIEW') return 'review';
  return 'safe';
}

function formatRelativeTime(isoStr?: string): string {
  if (!isoStr) return '—';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return new Date(isoStr).toLocaleDateString();
}

function isWithin60Min(isoStr?: string): boolean {
  if (!isoStr) return false;
  try {
    const dt = new Date(isoStr).getTime();
    if (isNaN(dt)) return false;
    return (Date.now() - dt) <= 60 * 60 * 1000 && dt <= Date.now() + 60_000;
  } catch { return false; }
}

// ─── Component ───────────────────────────────────────────────────────────────

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [timePeriod, setTimePeriod] = useState<'60m' | '24h' | '7d' | '30d'>('60m');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const prevDecisions = useRef<Record<string, string>>({});
  const lastRefresh = useRef<Date>(new Date());
  const [activityFeed, setActivityFeed] = useState<ActivityEvent[]>([]);

  const repoName   = 'shriza1991/DeployGuard';
  const branchName = 'main';

  // ── Toast helper ─────────────────────────────────────────────────────────
  const showToast = useCallback((message: string, type: Toast['type']) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  }, []);

  // ── Queries ──────────────────────────────────────────────────────────────
  const healthQuery = useQuery({
    queryKey: ['aggregatorHealth'],
    queryFn: getAggregatorHealth,
    refetchInterval: 5_000,
  });
  const backendOnline = healthQuery.data?.status === 'healthy';

  const metricsQuery = useQuery({
    queryKey: ['deploymentMetrics', timePeriod],
    queryFn: () => getDeploymentMetrics({ period: timePeriod }),
    refetchInterval: 15_000,
  });

  const deploymentsQuery = useQuery({
    queryKey: ['dashboardDeployments'],
    queryFn: () => listDeployments({ page: 1, page_size: 20 }),
    refetchInterval: 5_000,
  });

  const agentStatusQuery = useQuery({
    queryKey: ['agentStatus'],
    queryFn: getAgentStatus,
    refetchInterval: 5_000,
  });

  const repoStatusQuery = useQuery({
    queryKey: ['repoStatus', repoName, branchName],
    queryFn: () => getRepositoryStatus(repoName, branchName),
    refetchInterval: 5_000,
  });

  const repoManifestQuery = useQuery({
    queryKey: ['repoManifest', repoName, branchName],
    queryFn: () => getRepositoryManifest(repoName, branchName),
    refetchInterval: 10_000,
  });

  const repoStatsQuery = useQuery({
    queryKey: ['repoStats', repoName, branchName],
    queryFn: () => getRepositoryStats(repoName, branchName),
    refetchInterval: 10_000,
  });

  // ── Derived data ─────────────────────────────────────────────────────────
  const rawList = (deploymentsQuery.data?.items ?? []) as DeploymentSummary[];
  const recentList = rawList.filter(d => isWithin60Min(d.generated_at)).slice(0, 6);

  const total       = metricsQuery.data?.total        ?? 0;
  const safe        = metricsQuery.data?.safe         ?? 0;
  const blocked     = metricsQuery.data?.blocked      ?? 0;
  const review      = metricsQuery.data?.review       ?? 0;
  const avgRisk     = metricsQuery.data?.avgRisk      ?? 0;
  const avgConf     = metricsQuery.data?.avgConfidence ?? 0;
  const safePct     = total > 0 ? Math.round((safe / total) * 100) : 0;
  const confPct     = normalizeConfidence(avgConf) ?? 0;
  const confColor   = getConfidenceColor(confPct);

  const agentsOnline  = agentStatusQuery.data?.agents?.every(a => a.status === 'online') ?? false;
  const agentsDegraded = agentStatusQuery.data?.agents?.some(a => a.status === 'degraded') ?? false;

  function getPipelineStatus(key: string): 'online' | 'degraded' | 'offline' | 'unknown' {
    if (key === 'agents') {
      if (!agentStatusQuery.data) return 'unknown';
      if (agentsOnline) return 'online';
      if (agentsDegraded) return 'degraded';
      return 'offline';
    }
    if (!backendOnline) return key === 'aggregator' ? 'offline' : 'unknown';
    return backendOnline ? 'online' : 'offline';
  }

  // ── Toast & activity feed on new deployments ──────────────────────────────
  useEffect(() => {
    if (!deploymentsQuery.data) return;
    lastRefresh.current = new Date();
    const items = deploymentsQuery.data.items as DeploymentSummary[];
    const isFirstLoad = Object.keys(prevDecisions.current).length === 0;
    const newEvents: ActivityEvent[] = [];

    items.forEach(dep => {
      if (!dep.decision) return;
      const prev = prevDecisions.current[dep.correlation_id];
      if (!isFirstLoad && prev !== dep.decision) {
        const repoShort = dep.repository.split('/').pop() ?? dep.repository;
        const type = decisionToToastType(dep.decision);
        showToast(
          dep.decision === 'BLOCK'
            ? `🚨 Deployment BLOCKED — ${repoShort}: Risk too high`
            : `Deployment ${dep.decision} — ${repoShort}`,
          type
        );
        newEvents.push({
          id: dep.correlation_id + '-' + dep.decision,
          icon: dep.decision === 'BLOCK'
            ? <XCircle size={13} />
            : dep.decision === 'SAFE'
              ? <CheckCircle2 size={13} />
              : <AlertTriangle size={13} />,
          label: `Deployment ${dep.decision.toLowerCase()} — ${repoShort}`,
          timestamp: dep.generated_at ?? new Date().toISOString(),
          type: decisionToActivityType(dep.decision),
        });
      }
      prevDecisions.current[dep.correlation_id] = dep.decision;
    });

    if (newEvents.length > 0) {
      setActivityFeed(prev => [...newEvents, ...prev].slice(0, 10));
    }
  }, [deploymentsQuery.data, showToast]);

  // Seed initial activity feed from first load
  useEffect(() => {
    if (!deploymentsQuery.data || activityFeed.length > 0) return;
    const items = (deploymentsQuery.data.items as DeploymentSummary[])
      .filter(d => d.decision)
      .slice(0, 8)
      .map(dep => {
        const repoShort = dep.repository.split('/').pop() ?? dep.repository;
        const actType = decisionToActivityType(dep.decision!);
        return {
          id: dep.correlation_id,
          icon: dep.decision === 'BLOCK'
            ? <XCircle size={13} />
            : dep.decision === 'SAFE'
              ? <CheckCircle2 size={13} />
              : <AlertTriangle size={13} />,
          label: `Deployment ${dep.decision!.toLowerCase()} — ${repoShort}`,
          timestamp: dep.generated_at ?? new Date().toISOString(),
          type: actType,
        } as ActivityEvent;
      });
    setActivityFeed(items);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deploymentsQuery.data]);

  const repoIndexed = repoStatusQuery.data?.status === 'indexed';

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="dashboard-container fade-in">

      {/* ── Toast Stack ── */}
      <div className="toast-stack">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast-item toast-${toast.type}`}>
            {toast.type === 'success' && <CheckCircle2 size={14} />}
            {toast.type === 'block'   && <XCircle size={14} />}
            {toast.type === 'review'  && <AlertTriangle size={14} />}
            {toast.type === 'info'    && <Zap size={14} />}
            <span>{toast.message}</span>
          </div>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════
          SECTION 1 — EXECUTIVE HEADER
      ══════════════════════════════════════════════════════════ */}
      <div className="dashboard-header-container">
        <div className="dashboard-header-left">
          <div className="title-area">
            <div className="title-icon-wrapper">
              <Shield className="title-icon" />
            </div>
            <h1>Operations Center</h1>
          </div>
          <p className="description">
            Real-time security auditing and deployment intelligence.
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
            {(['60m', '24h', '7d', '30d'] as const).map(p => (
              <button
                key={p}
                onClick={() => setTimePeriod(p)}
                className={`time-btn ${timePeriod === p ? 'active' : ''}`}
              >
                {p === '60m' ? '60 Mins' : p === '24h' ? '24 Hours' : p === '7d' ? '7 Days' : '30 Days'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          SECTION 2 — EXECUTIVE SUMMARY CARDS
      ══════════════════════════════════════════════════════════ */}
      <div className="section-block">
        <div className="section-header">
          <span className="section-label">Executive Summary</span>
          <span className="section-period">{timePeriod}</span>
        </div>
        <div className="exec-summary-grid">
          <MetricCard
            title="DEPLOYMENTS"
            value={total}
            subtitle="Total in window"
            type="neutral"
          />
          <MetricCard
            title="SUCCESS RATE"
            value={`${safePct}%`}
            subtitle="Approved promotions"
            type={safePct >= 70 ? 'safe' : safePct >= 40 ? 'warn' : 'danger'}
            progress={safePct}
            progressColor={safePct >= 70 ? 'var(--ds-secondary)' : safePct >= 40 ? 'var(--ds-tertiary)' : 'var(--ds-error)'}
            valueStyle={{ color: safePct >= 70 ? 'var(--ds-secondary)' : safePct >= 40 ? 'var(--ds-tertiary)' : 'var(--ds-error)' }}
          />
          <MetricCard
            title="AVG RISK SCORE"
            value={<>{avgRisk}<span style={{ fontSize: '12px', color: 'var(--ds-outline)', fontWeight: 400 }}>/100</span></>}
            subtitle="Pipeline risk mean"
            type={avgRisk >= 60 ? 'danger' : avgRisk >= 30 ? 'warn' : 'safe'}
            progress={avgRisk}
            progressColor={avgRisk >= 60 ? 'var(--ds-error)' : avgRisk >= 30 ? 'var(--ds-tertiary)' : 'var(--ds-secondary)'}
          />
          <MetricCard
            title="BLOCKED"
            value={blocked}
            subtitle="High-risk deployments stopped"
            type={blocked > 0 ? 'danger' : 'neutral'}
            valueStyle={blocked > 0 ? { color: 'var(--ds-error)' } : undefined}
          />
          <MetricCard
            title="UNDER REVIEW"
            value={review}
            subtitle="Manual review required"
            type={review > 0 ? 'warn' : 'neutral'}
            valueStyle={review > 0 ? { color: 'var(--ds-tertiary)' } : undefined}
          />
          <MetricCard
            title="AVG CONFIDENCE"
            value={`${confPct}%`}
            subtitle="Model validation average"
            type="safe"
            progress={confPct}
            progressColor={confColor}
            valueStyle={{ color: confColor }}
          />
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          SECTION 3 — LATEST DEPLOYMENT DECISIONS
      ══════════════════════════════════════════════════════════ */}
      <div className="section-block">
        <div className="section-header">
          <span className="section-label">Latest Deployment Decisions</span>
          <button onClick={() => navigate('/deployments')} className="section-action-btn">
            View All <ChevronRight size={12} />
          </button>
        </div>

        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          {deploymentsQuery.isLoading ? (
            <div className="dash-empty-state">
              <RefreshCw size={20} className="spinning" />
              <span>Loading deployment decisions...</span>
            </div>
          ) : recentList.length === 0 ? (
            <div className="dash-empty-state dash-empty-state--cta">
              <Rocket size={28} className="empty-icon" />
              <h3 className="empty-headline">No recent deployments in the last 60 minutes</h3>
              <p className="empty-desc">
                Trigger a scan from the webhook simulator to evaluate security outcomes.
              </p>
              <div className="empty-cta-row">
                <button onClick={() => navigate('/simulator')} className="btn-primary-stitch font-mono">
                  <Terminal size={13} /> Run Simulation
                </button>
                <button onClick={() => navigate('/deployments')} className="btn-secondary-stitch font-mono">
                  View History <ChevronRight size={12} />
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
                  <th>Confidence</th>
                  <th>Branch</th>
                  <th>Time</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentList.map(dep => {
                  const conf = normalizeConfidence(dep.overall_confidence);
                  return (
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
                      <td>
                        {conf !== null ? (
                          <span className="font-mono" style={{ fontSize: '11px', color: getConfidenceColor(conf) }}>
                            {conf}%
                          </span>
                        ) : (
                          <span style={{ color: 'var(--ds-outline)', fontSize: '11px' }}>—</span>
                        )}
                      </td>
                      <td className="branch-cell">{dep.branch || '—'}</td>
                      <td className="time-cell">{formatRelativeTime(dep.generated_at)}</td>
                      <td><ExternalLink size={12} className="row-link-icon" /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════
          SECTION 4 — REPOSITORY CONTEXT | PIPELINE HEALTH
      ══════════════════════════════════════════════════════════ */}
      <div className="dash-two-col">

        {/* Repository Context */}
        <div className="section-block">
          <div className="section-header">
            <span className="section-label">Repository Context</span>
            {repoIndexed && (
              <span style={{ fontSize: '10px', color: 'var(--ds-secondary)', fontFamily: 'JetBrains Mono, monospace' }}>
                ● Indexed
              </span>
            )}
          </div>
          <div className="glass-panel repo-context-panel">
            {(repoStatusQuery.isLoading || repoManifestQuery.isLoading || repoStatsQuery.isLoading) ? (
              <div className="dash-empty-state" style={{ padding: '28px' }}>
                <RefreshCw size={16} className="spinning" />
                <span style={{ fontSize: '12px' }}>Loading repository...</span>
              </div>
            ) : (repoStatusQuery.isError || repoStatsQuery.isError) ? (
              <div className="dash-empty-state" style={{ padding: '24px', color: 'var(--ds-outline)', gap: '6px' }}>
                <GitBranch size={20} style={{ opacity: 0.35 }} />
                <span style={{ fontSize: '12px' }}>Repository not indexed</span>
                <span style={{ fontSize: '11px', color: 'var(--ds-outline)', opacity: 0.7 }}>
                  Trigger indexing to populate context
                </span>
              </div>
            ) : (
              <div className="repo-context-rows">
                {[
                  { label: 'Repository',   value: <span className="font-mono" style={{ fontSize: '12px', color: 'var(--ds-primary)', fontWeight: 600 }}>{repoName}</span> },
                  { label: 'Status',       value: <StatusBadge status={repoStatusQuery.data?.status === 'indexed' ? 'ONLINE' : repoStatusQuery.data?.status === 'indexing' ? 'INDEXING' : repoStatusQuery.data?.status === 'failed' ? 'FAILED' : 'NOT_INDEXED'} /> },
                  { label: 'Files',        value: repoStatsQuery.data?.number_of_files?.toLocaleString() ?? '—' },
                  { label: 'Lines of Code', value: repoStatsQuery.data?.lines_of_code?.toLocaleString() ?? '—' },
                  { label: 'Last Indexed', value: repoManifestQuery.data?.last_indexed_at ? formatRelativeTime(repoManifestQuery.data.last_indexed_at) : '—' },
                ].map(({ label, value }) => (
                  <div key={label} className="repo-context-row">
                    <span className="repo-ctx-label">{label}</span>
                    <span className="repo-ctx-value font-mono">{value}</span>
                  </div>
                ))}
                {repoManifestQuery.data?.frameworks && repoManifestQuery.data.frameworks.length > 0 && (
                  <div className="repo-context-row" style={{ alignItems: 'flex-start' }}>
                    <span className="repo-ctx-label">Frameworks</span>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      {repoManifestQuery.data.frameworks.map(fw => (
                        <span key={fw} className="agent-chip font-mono" style={{ margin: 0, padding: '1px 6px', fontSize: '9px' }}>{fw}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Pipeline Health */}
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
                    <HealthIndicator status={status} />
                  </div>
                );
              })}
            </div>
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

      {/* ══════════════════════════════════════════════════════════
          SECTION 5 — RECENT ACTIVITY | AI AGENT OVERVIEW
      ══════════════════════════════════════════════════════════ */}
      <div className="dash-two-col">

        {/* Recent Activity Feed */}
        <div className="section-block">
          <div className="section-header">
            <span className="section-label">Recent Activity</span>
            <span style={{ fontSize: '10px', color: 'var(--ds-outline)', fontFamily: 'JetBrains Mono, monospace' }}>Live</span>
          </div>
          <div className="glass-panel activity-feed">
            {activityFeed.length === 0 ? (
              <div className="dash-empty-state" style={{ padding: '32px' }}>
                <Zap size={22} className="empty-icon" />
                <span style={{ fontSize: '12px' }}>No events yet — pipeline is idle</span>
              </div>
            ) : (
              <div className="activity-list">
                {activityFeed.map(evt => (
                  <div key={evt.id} className={`activity-row activity-row--${evt.type}`}>
                    <span className={`activity-icon activity-icon--${evt.type}`}>{evt.icon}</span>
                    <div className="activity-body">
                      <span className="activity-label">{evt.label}</span>
                      <span className="activity-time">{formatRelativeTime(evt.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* AI Agent Overview */}
        <div className="section-block">
          <div className="section-header">
            <span className="section-label">AI Agent Overview</span>
            <button onClick={() => navigate('/agents')} className="section-action-btn">
              View Details <ChevronRight size={12} />
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {agentStatusQuery.isLoading ? (
              <div className="dash-empty-state glass-panel" style={{ padding: '28px' }}>
                <RefreshCw size={16} className="spinning" />
                <span style={{ fontSize: '12px' }}>Loading agents...</span>
              </div>
            ) : agentStatusQuery.isError || !agentStatusQuery.data?.agents?.length ? (
              <div className="dash-empty-state glass-panel" style={{ padding: '28px' }}>
                <Bot size={22} className="empty-icon" />
                <span style={{ fontSize: '12px' }}>No agent data available</span>
              </div>
            ) : (
              agentStatusQuery.data.agents.map((agent: AgentStatusItem) => {
                const display = AGENT_DISPLAY[agent.name] ?? { label: agent.name.replace(' Agent', ''), short: agent.name };
                const conf = normalizeConfidence(agent.average_confidence);
                const confColor = getConfidenceColor(conf);
                return (
                  <div key={agent.name} className="agent-overview-card glass-panel">
                    <div className="agent-overview-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={`agent-dot ${agent.status}`} style={{ width: '7px', height: '7px' }} />
                        <span className="agent-overview-name">{display.label}</span>
                      </div>
                      <HealthIndicator status={agent.status} />
                    </div>
                    <div className="agent-overview-stats">
                      <div className="agent-stat-item">
                        <span className="agent-stat-label">Analyses</span>
                        <span className="agent-stat-value font-mono">{agent.analysis_count ?? '—'}</span>
                      </div>
                      <div className="agent-stat-item">
                        <span className="agent-stat-label">Latency</span>
                        <span className="agent-stat-value font-mono">
                          {agent.latency_ms > 0 ? `${agent.latency_ms}ms` : '—'}
                        </span>
                      </div>
                      <div className="agent-stat-item">
                        <span className="agent-stat-label">Confidence</span>
                        <span className="agent-stat-value font-mono" style={{ color: conf !== null ? confColor : undefined }}>
                          {conf !== null ? `${conf}%` : '—'}
                        </span>
                      </div>
                      <div className="agent-stat-item">
                        <span className="agent-stat-label">Last Run</span>
                        <span className="agent-stat-value font-mono">
                          {agent.last_run_timestamp ? formatRelativeTime(agent.last_run_timestamp) : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

      {/* ══════════════════════════════════════════════════════════
          SECTION 6 — QUICK ACTIONS (actions, not navigation)
      ══════════════════════════════════════════════════════════ */}
      <div className="section-block">
        <div className="section-header">
          <span className="section-label">Quick Actions</span>
        </div>
        <div className="quick-ops-grid">
          <button
            className="quick-op-btn quick-op-btn--primary"
            onClick={() => navigate('/simulator')}
          >
            <Play size={14} />
            <div>
              <span className="quick-op-title">Run Simulation</span>
              <span className="quick-op-desc">Trigger a deployment scan via webhook</span>
            </div>
          </button>
          <button
            className="quick-op-btn"
            onClick={() => navigate('/search')}
          >
            <Search size={14} />
            <div>
              <span className="quick-op-title">Query Repository</span>
              <span className="quick-op-desc">Vector search over indexed code</span>
            </div>
          </button>
          <button
            className="quick-op-btn"
            onClick={() => {
              deploymentsQuery.refetch();
              metricsQuery.refetch();
              agentStatusQuery.refetch();
              showToast('Dashboard refreshed', 'info');
            }}
          >
            <RotateCcw size={14} />
            <div>
              <span className="quick-op-title">Refresh Dashboard</span>
              <span className="quick-op-desc">Re-poll all live data sources</span>
            </div>
          </button>
          <button
            className="quick-op-btn"
            onClick={() => navigate('/deployments')}
          >
            <FileText size={14} />
            <div>
              <span className="quick-op-title">View All Deployments</span>
              <span className="quick-op-desc">Full deployment history & filters</span>
            </div>
          </button>
          <button
            className="quick-op-btn"
            onClick={() => navigate('/analytics')}
          >
            <TrendingUp size={14} />
            <div>
              <span className="quick-op-title">Open Analytics</span>
              <span className="quick-op-desc">Historical trends and risk charts</span>
            </div>
          </button>
          <button
            className="quick-op-btn"
            onClick={() => {
              const ts = new Date().toISOString().replace('T', ' ').slice(0, 16);
              const blob = new Blob(
                [`DeployGuard Snapshot — ${ts}\n\nTotal: ${total} | Safe: ${safe} | Review: ${review} | Blocked: ${blocked}\nAvg Risk: ${avgRisk}/100 | Avg Confidence: ${confPct}%`],
                { type: 'text/plain' }
              );
              const a = document.createElement('a');
              a.href = URL.createObjectURL(blob);
              a.download = `deployguard-snapshot-${Date.now()}.txt`;
              a.click();
              showToast('Snapshot exported', 'success');
            }}
          >
            <Clock size={14} />
            <div>
              <span className="quick-op-title">Export Snapshot</span>
              <span className="quick-op-desc">Download current metrics summary</span>
            </div>
          </button>
        </div>
      </div>

    </div>
  );
};

export default Dashboard;
