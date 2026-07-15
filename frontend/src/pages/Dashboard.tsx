import React, { useState } from 'react';
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
  Sliders,
} from 'lucide-react';

import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [timePeriod, setTimePeriod] = useState<'24h' | '7d' | '30d'>('7d');

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
    queryFn: () => listDeployments({ page: 1, page_size: 10 }),
    refetchInterval: 15_000,
  });

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

  // Deployment Health Score (e.g., % of Safe deployments out of total evaluated)
  const healthScore = total > 0 ? Math.round((safe / total) * 100) : 100;

  // Filter top/worst risks (Score >= 50 or BLOCKED)
  const topRisks = deploymentsList.filter(
    d => d.decision === 'BLOCK' || (d.overall_score ?? 0) >= 50
  );

  return (
    <div className="dashboard-container fade-in">
      {/* --- Header Section --- */}
      <div className="dashboard-header-container">
        <div className="dashboard-header-left">
          <div className="title-area">
            <div className="title-icon-wrapper">
              <Shield className="title-icon text-indigo" />
            </div>
            <h1>Executive Overview</h1>
          </div>
          <p className="description">
            Real-time security auditing and risk gating pipeline metrics.
          </p>
        </div>

        <div className="dashboard-header-right">
          {/* Time range selector */}
          <div className="timeframe-selector">
            <button
              onClick={() => setTimePeriod('24h')}
              className={`time-btn ${timePeriod === '24h' ? 'active' : ''}`}
            >
              24 Hours
            </button>
            <button
              onClick={() => setTimePeriod('7d')}
              className={`time-btn ${timePeriod === '7d' ? 'active' : ''}`}
            >
              7 Days
            </button>
            <button
              onClick={() => setTimePeriod('30d')}
              className={`time-btn ${timePeriod === '30d' ? 'active' : ''}`}
            >
              30 Days
            </button>
          </div>
        </div>
      </div>

      {/* --- Main Dashboard Grid --- */}
      <div className="dashboard-content-layout" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
        
        {/* --- Top Metrics Panel (Flex/Grid of Health Score and KPIs) --- */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px' }}>
          
          {/* Health Score Card */}
          <div className="kpi-card glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', borderLeft: '4px solid var(--color-safe)' }}>
            <div>
              <span className="kpi-title" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>DEPLOYMENT HEALTH SCORE</span>
              <div style={{ display: 'flex', alignItems: 'baseline', marginTop: '8px' }}>
                <span className="kpi-card-value font-mono" style={{ fontSize: '36px', color: '#fff', fontWeight: 800 }}>{healthScore}%</span>
              </div>
            </div>
            <div style={{ marginTop: '12px' }}>
              <div className="kpi-progress-bar" style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${healthScore}%`, height: '100%', background: 'var(--color-safe)', borderRadius: '3px' }} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>Percentage of clean and safe promotions.</p>
            </div>
          </div>

          {/* Total Audited */}
          <div className="kpi-card glass-panel" style={{ borderLeft: '4px solid var(--accent-blue)' }}>
            <span className="kpi-title">TOTAL EVALUATED</span>
            <div className="kpi-card-value font-mono">{total}</div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>Total git webhook pushes verified.</p>
          </div>

          {/* Verdicts breakdown */}
          <div className="kpi-card glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span className="kpi-title">VERDICT DISTRIBUTION</span>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Safe:</span>
              <span className="font-mono" style={{ color: 'var(--color-safe)', fontWeight: 'bold' }}>{safe}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Review Required:</span>
              <span className="font-mono" style={{ color: 'var(--color-review)', fontWeight: 'bold' }}>{review}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Blocked:</span>
              <span className="font-mono" style={{ color: 'var(--color-block)', fontWeight: 'bold' }}>{blocked}</span>
            </div>
          </div>

          {/* Risk & Confidence */}
          <div className="kpi-card glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <span className="kpi-title">AVG RISK & CONFIDENCE</span>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
                <div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Risk Score</span>
                  <p className="font-mono" style={{ fontSize: '20px', color: '#fff', fontWeight: 'bold' }}>{avgRisk}</p>
                </div>
                <div style={{ borderLeft: '1px solid var(--panel-border)', paddingLeft: '16px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Confidence</span>
                  <p className="font-mono" style={{ fontSize: '20px', color: '#fff', fontWeight: 'bold' }}>{Math.round(avgConfidence * 100)}%</p>
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* --- Middle Section: Grid (Recent Deployments vs Statuses & Feeds) --- */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
          
          {/* Left Block: Recent Deployments */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>Recent Deployments</h2>
              <button 
                onClick={() => navigate('/deployments')} 
                style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', fontSize: '12px' }}
              >
                View All <ChevronRight size={14} />
              </button>
            </div>

            {deploymentsList.length === 0 ? (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No deployments audited in this window.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {deploymentsList.slice(0, 5).map(dep => (
                  <div 
                    key={dep.correlation_id}
                    onClick={() => navigate(`/deployments/${dep.correlation_id}`)}
                    style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '6px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', transition: 'border-color 0.2s' }}
                    className="deployment-item-hover"
                  >
                    <div>
                      <h4 className="font-mono" style={{ fontSize: '13px', color: '#fff' }}>{dep.repository}</h4>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>ID: {dep.correlation_id.substring(0, 8)}...</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className={`verdict-tag-small ${dep.decision?.toLowerCase() || 'pending'}`}>
                        {dep.decision || 'PENDING'}
                      </span>
                      <ExternalLink size={12} className="text-muted" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Block: Status & Quick Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* System Health Summary */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>Infrastructure Summary</h2>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Network size={14} className="text-muted" />
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Gateway Proxy</span>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--color-safe)', fontWeight: 'bold' }}>ONLINE</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={14} className="text-muted" />
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Aggregator Service</span>
                  </div>
                  <span style={{ fontSize: '12px', color: backendOnline ? 'var(--color-safe)' : 'var(--color-block)', fontWeight: 'bold' }}>
                    {backendOnline ? 'ONLINE' : 'UNREACHABLE'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Database size={14} className="text-muted" />
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Redis Cache Cluster</span>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--color-safe)', fontWeight: 'bold' }}>CONNECTED</span>
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--panel-border)', marginTop: '16px', paddingTop: '16px' }}>
                <h3 style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }}>ACTIVE SECURITY AGENTS</h3>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {agentStatusQuery.data?.agents.map(a => (
                    <span key={a.name} className="confidence-badge font-mono" style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255,255,255,0.03)', padding: '4px 8px' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: a.status === 'online' ? 'var(--color-safe)' : 'var(--color-review)' }} />
                      {a.name.replace(' Agent', '')}
                    </span>
                  )) ?? (
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Fetching agent states...</span>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Actions Panel */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>Quick Actions</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <button 
                  onClick={() => navigate('/simulator')}
                  className="btn-primary-stitch"
                  style={{ justifyContent: 'center', width: '100%' }}
                >
                  <Terminal size={14} />
                  <span>Simulator</span>
                </button>
                <button 
                  onClick={() => navigate('/reports')}
                  className="btn-secondary-stitch"
                  style={{ justifyContent: 'center', width: '100%' }}
                >
                  <FileText size={14} />
                  <span>Reports</span>
                </button>
                <button 
                  onClick={() => navigate('/settings')}
                  className="btn-secondary-stitch"
                  style={{ justifyContent: 'center', width: '100%', gridColumn: 'span 2' }}
                >
                  <Sliders size={14} />
                  <span>Configure Risk Thresholds</span>
                </button>
              </div>
            </div>

          </div>

        </div>

        {/* --- Bottom Section: Activity Feed & Top Risks --- */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
          
          {/* Recent Activity Feed */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>Audit Activity Log</h2>
            
            {deploymentsList.length === 0 ? (
              <div style={{ padding: '30px 0', textAlign: 'center', color: 'var(--text-muted)' }}>
                No events recorded.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {deploymentsList.slice(0, 4).map((dep, idx) => (
                  <div key={idx} style={{ display: 'flex', gap: '12px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: dep.decision === 'BLOCK' ? 'var(--color-block)' : 'var(--color-safe)', marginTop: '4px' }} />
                      {idx < 3 && <div style={{ width: '1px', flexGrow: 1, background: 'var(--panel-border)', margin: '4px 0' }} />}
                    </div>
                    <div>
                      <p style={{ color: '#fff' }}>
                        Canary analysis completed for <span className="font-mono" style={{ fontWeight: 'bold' }}>{dep.repository}</span>. 
                        Decision: <span style={{ color: dep.decision === 'BLOCK' ? 'var(--color-block)' : dep.decision === 'REVIEW' ? 'var(--color-review)' : 'var(--color-safe)', fontWeight: 'bold' }}>{dep.decision || 'PENDING'}</span>
                      </p>
                      <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        {dep.generated_at ? new Date(dep.generated_at).toLocaleString() : ''}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top Risks identified */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>Top Pipeline Risks</h2>
            
            {topRisks.length === 0 ? (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No active threats flagged across repositories.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {topRisks.slice(0, 3).map((risk, idx) => (
                  <div key={idx} style={{ padding: '12px', background: 'rgba(255, 180, 171, 0.05)', border: '1px solid rgba(255, 180, 171, 0.2)', borderRadius: '6px', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <AlertTriangle size={16} style={{ color: 'var(--color-block)', flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <h4 className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold' }}>{risk.repository}</h4>
                      <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Evaluated risk score of {risk.overall_score}/100. Verification checks blocked canary build deployment.
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};
export default Dashboard;
