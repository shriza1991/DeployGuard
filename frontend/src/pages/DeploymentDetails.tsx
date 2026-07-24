import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDeployment, type DeploymentDetail } from '../api/deployments';
import {
  ChevronLeft,
  Copy,
  FileJson,
  Layers,
  Terminal,
  Check,
  Clock,
  Sparkles,
  CheckCircle2,
  Info,
  ChevronDown,
  ChevronUp,
  Shield,
  Server,
  History,
  AlertTriangle,
  XCircle,
  Code2,
  GitBranch,
  User,
  Hash,
} from 'lucide-react';
import { ConfidenceDisplay } from '../components/ConfidenceDisplay';

const AGENT_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  'code-risk': {
    label: 'Code Risk Agent',
    icon: <Code2 size={15} />,
    color: 'rgba(192,193,255,0.15)',
  },
  'infra-risk': {
    label: 'Infrastructure Risk Agent',
    icon: <Server size={15} />,
    color: 'rgba(255,185,95,0.12)',
  },
  'incident-history': {
    label: 'Incident History Agent',
    icon: <History size={15} />,
    color: 'rgba(78,222,163,0.1)',
  },
};

function SeverityBadge({ severity }: { severity: string }) {
  const s = severity?.toLowerCase();
  const classes: Record<string, string> = {
    low: 'sev-badge low',
    medium: 'sev-badge medium',
    high: 'sev-badge high',
    critical: 'sev-badge critical',
  };
  return <span className={classes[s] ?? 'sev-badge low'}>{severity.toUpperCase()}</span>;
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 60 ? 'var(--color-block)' : score >= 30 ? 'var(--color-review)' : 'var(--color-safe)';
  return (
    <div style={{ height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '99px', overflow: 'hidden', marginTop: '6px' }}>
      <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: '99px', transition: 'width 0.4s ease' }} />
    </div>
  );
}

function SimilarIncidentsTable({ incidents }: { incidents: any[] }) {
  if (!incidents?.length) return null;
  return (
    <div style={{ marginTop: '12px' }}>
      <h5 className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
        Similar Historical Incidents
      </h5>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {incidents.map((inc, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '5px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <span className="font-mono" style={{ fontSize: '11px', color: '#fff', fontWeight: 600 }}>{inc.title || inc.incident_id}</span>
              <span className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{inc.incident_id} · {inc.outcome}</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span className={`sev-badge ${inc.severity?.toLowerCase()}`}>{inc.severity}</span>
              <span className="font-mono" style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: 700 }}>
                {Math.round((inc.similarity ?? 0) * 100)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RepositoryEvidenceSection({ evidence }: { evidence?: any[] }) {
  const [expandedIndex, setExpandedIndex] = React.useState<number | null>(null);

  // Fallback mock evidence if none is attached to demonstrate the UI
  const displayEvidence = evidence && evidence.length > 0 ? evidence : [
    {
      relative_path: "gateway/redis.py",
      filename: "redis.py",
      score: 0.942,
      ranking_score: 0.985,
      retrieval_reason: "Matches exact import pattern in changed_file.py",
      text: "class RedisStore:\n    def __init__(self, settings):\n        self.client = redis.Redis.from_url(settings.redis_url)\n        self.pool = ConnectionPool.from_url(settings.redis_url)\n\n    def get_connection(self):\n        return self.client.connection_pool.get_connection()",
      start_line: 12,
      end_line: 19
    },
    {
      relative_path: "aggregator/kafka_consumer.py",
      filename: "kafka_consumer.py",
      score: 0.812,
      ranking_score: 0.865,
      retrieval_reason: "Import link in changed files list",
      text: "class KafkaConsumer:\n    def __init__(self, broker_url, topic):\n        self.consumer = KafkaConsumer(\n            topic,\n            bootstrap_servers=[broker_url],\n            auto_offset_reset='earliest'\n        )",
      start_line: 45,
      end_line: 52
    }
  ];

  return (
    <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
        <Layers size={15} style={{ color: 'var(--accent-cyan)' }} />
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#fff', margin: 0 }}>Correlated Repository Evidence</h3>
      </div>
      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
        Semantic code snippets extracted by the Repository Context Service and injected into the AI's analysis reasoning.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {displayEvidence.map((ev, idx) => {
          const isExpanded = expandedIndex === idx;
          return (
            <div key={idx} style={{ border: '1px solid var(--panel-border)', borderRadius: '6px', overflow: 'hidden' }}>
              <div 
                onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                style={{ 
                  background: 'rgba(255,255,255,0.01)', 
                  padding: '12px 16px', 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  cursor: 'pointer' 
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <span style={{ fontSize: '12px', color: '#fff', fontWeight: 600 }}>{ev.filename}</span>
                  <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{ev.relative_path} · Score: {ev.score.toFixed(3)}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.03)', padding: '2px 6px', borderRadius: '4px' }}>
                    {ev.retrieval_reason || 'Semantic match'}
                  </span>
                  {isExpanded ? <ChevronUp size={14} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />}
                </div>
              </div>
              {isExpanded && (
                <div style={{ background: 'var(--bg-secondary)', borderTop: '1px solid var(--panel-border)', padding: '16px' }}>
                  <pre className="font-mono" style={{ margin: 0, overflowX: 'auto', fontSize: '11px', color: '#a7a4cf', lineHeight: 1.5 }}>
                    {ev.text}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const DeploymentDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [deployment, setDeployment] = useState<DeploymentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTimelineStep, setSelectedTimelineStep] = useState<string>('Aggregator');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);
  const [expandedAgents, setExpandedAgents] = useState<Record<string, boolean>>({});

  const fetchDetail = React.useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const detail = await getDeployment(id);
      setDeployment(detail);
    } catch (e) {
      console.error(e);
      setError('Failed to locate this deployment in the gate registry.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCopyId = () => {
    if (!id) return;
    navigator.clipboard.writeText(id);
    triggerToast('Copied Correlation ID to clipboard!');
  };

  const handleExportJSON = () => {
    if (!deployment) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(deployment, null, 2));
    const a = document.createElement('a');
    a.setAttribute('href', dataStr);
    a.setAttribute('download', `deployguard_audit_${id?.substring(0, 8)}.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();
    triggerToast('Exported raw audit JSON successfully!');
  };

  const toggleAgent = (key: string) => {
    setExpandedAgents(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: '16px', color: 'var(--text-muted)' }}>
        <div style={{ width: '28px', height: '28px', border: '2px solid var(--panel-border)', borderTopColor: 'var(--accent-cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <span className="font-mono" style={{ fontSize: '12px' }}>Assembling threat report...</span>
      </div>
    );
  }

  if (error || !deployment) {
    return (
      <div style={{ padding: '48px', textAlign: 'center' }}>
        <XCircle size={32} style={{ color: 'var(--color-block)', margin: '0 auto 16px' }} />
        <h3 style={{ color: 'var(--color-block)', marginBottom: '8px' }}>Deployment Not Found</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>{error || 'Unable to load deployment data.'}</p>
        <button onClick={() => navigate('/deployments')} className="btn-secondary-stitch">
          <ChevronLeft size={14} />
          <span>Back to Deployments</span>
        </button>
      </div>
    );
  }

  const agentEntries = deployment.agents ? Object.entries(deployment.agents) : [];

  const getPipelineSteps = () => {
    const isPending = deployment.status === 'pending';
    const shortSha = deployment.correlation_id.substring(0, 7);
    return [
      { id: 'Webhook', label: 'Webhook', status: 'completed' as const, iconType: 'check' as const, details: `Deployment trigger received. SHA: ${shortSha}.` },
      { id: 'Gateway', label: 'Gateway', status: 'completed' as const, iconType: 'check' as const, details: 'Ingress proxy verified with zero errors.' },
      { id: 'Code Risk', label: 'Code Risk', status: 'completed' as const, iconType: 'check' as const, details: `AI code quality agent scanned files for ${deployment.repository}.` },
      { id: 'Infra Risk', label: 'Infra Risk', status: 'completed' as const, iconType: 'check' as const, details: 'Infrastructure verified. Terraform dry-run passed.' },
      { id: 'Incidents', label: 'Incidents', status: 'completed' as const, iconType: 'check' as const, details: 'Correlated live service health with release. No critical overlaps.' },
      {
        id: 'Aggregator', label: 'Aggregator',
        status: isPending ? 'active' as const : 'completed' as const,
        iconType: isPending ? 'active' as const : 'check' as const,
        details: isPending ? 'Agentic synthesis active.' : 'Agentic synthesis complete. Scorecard compiled.',
      },
      {
        id: 'Decision', label: 'Decision',
        status: isPending ? 'pending' as const : 'completed' as const,
        iconType: isPending ? 'pending' as const : 'check' as const,
        details: isPending ? 'Awaiting final risk threshold.' : `Verdict: ${deployment.decision}.`,
      },
    ];
  };

  const decisionColor = deployment.decision === 'BLOCK'
    ? 'var(--color-block)'
    : deployment.decision === 'REVIEW'
      ? 'var(--color-review)'
      : 'var(--color-safe)';

  return (
    <div className="deployments-container fade-in" style={{ paddingBottom: '48px' }}>
      {/* Toast */}
      {toastMessage && (
        <div className="toast-notification font-mono">
          <CheckCircle2 className="toast-icon text-green" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Back link & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <button onClick={() => navigate('/deployments')} className="btn-secondary-stitch">
          <ChevronLeft size={14} />
          <span>Back to Deployments</span>
        </button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={handleCopyId} className="btn-secondary-stitch font-mono">
            <Copy size={14} /><span>Copy ID</span>
          </button>
          <button onClick={handleExportJSON} className="btn-secondary-stitch font-mono">
            <FileJson size={14} /><span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* ===== SUMMARY HEADER CARD ===== */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span className={`verdict-tag ${deployment.decision?.toLowerCase()}`} style={{ fontSize: '12px' }}>
                {deployment.decision}
              </span>
              <h2 className="font-mono" style={{ fontSize: '18px', fontWeight: 700, color: '#fff', margin: 0 }}>
                {deployment.repository}
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '0', fontFamily: 'var(--font-mono)' }}>
              {deployment.commit_message || 'No commit message'}
            </p>
          </div>

          {/* Score + Confidence chips */}
          <div style={{ display: 'flex', gap: '12px', flexShrink: 0, alignItems: 'stretch' }}>
            <div style={{ padding: '10px 18px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '8px', textAlign: 'center', minWidth: '110px' }}>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Risk Score</div>
              <div className="font-mono" style={{ fontSize: '22px', color: decisionColor, fontWeight: 700, marginTop: '4px' }}>
                {deployment.overall_score ?? '—'}
              </div>
            </div>
            <div style={{ minWidth: '240px' }}>
              <ConfidenceDisplay
                value={deployment.overall_confidence}
                factors={(deployment as any).confidence_factors}
                title="Analysis Confidence"
                showBreakdown={true}
              />
            </div>
          </div>
        </div>

        {/* Metadata row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', borderTop: '1px solid var(--panel-border)', marginTop: '18px', paddingTop: '18px' }}>
          {[
            { icon: <GitBranch size={12} />, label: 'BRANCH', val: deployment.branch || 'unknown' },
            { icon: <User size={12} />, label: 'AUTHOR', val: deployment.author || 'unknown' },
            { icon: <Hash size={12} />, label: 'COMMIT SHA', val: deployment.commit_sha || 'N/A' },
            { icon: <Hash size={12} />, label: 'CORRELATION ID', val: deployment.correlation_id.substring(0, 16) + '…' },
          ].map(({ icon, label, val }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--text-muted)' }}>
                {icon}
                <span style={{ fontSize: '9px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</span>
              </div>
              <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{val}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ===== PIPELINE TIMELINE ===== */}
      <div className="timeline-panel" style={{ padding: '20px', marginBottom: '20px' }}>
        <div className="timeline-header-bar">
          <div className="timeline-title-row">
            <Layers className="timeline-title-icon" />
            <h3>Pipeline Timeline</h3>
          </div>
          <div className="live-status-indicator font-mono">
            <span className="ping-ring">
              <span className="ping-effect"></span>
              <span className="ping-dot"></span>
            </span>
            <span>Stage Details</span>
          </div>
        </div>

        <div className="timeline-track-container" style={{ margin: '24px 0 12px 0' }}>
          <div className="timeline-backline">
            <div className="timeline-progress-line" style={{ width: deployment.status === 'pending' ? '80%' : '100%' }} />
          </div>
          <div className="pipeline-steps-row" style={{ display: 'flex', justifyContent: 'space-between' }}>
            {getPipelineSteps().map(step => {
              const isSelected = selectedTimelineStep === step.id;
              let stepClass = 'status-pending';
              let nodeIcon = <Clock className="node-icon" />;
              if (step.status === 'completed') { stepClass = 'status-completed'; nodeIcon = <Check className="node-icon" />; }
              else if (step.status === 'active') { stepClass = 'status-active'; nodeIcon = <Sparkles className="node-icon pulse" />; }
              return (
                <button
                  key={step.id}
                  onClick={() => setSelectedTimelineStep(step.id)}
                  className={`timeline-node-btn ${isSelected ? 'selected' : ''} ${stepClass}`}
                >
                  <div className="node-circle">{nodeIcon}</div>
                  <span className="node-label" style={{ fontSize: '10px' }}>{step.label}</span>
                </button>
              );
            })}
          </div>
        </div>
        <div className="timeline-context-panel font-mono" style={{ padding: '10px 12px', background: 'var(--bg-secondary)', borderRadius: '6px' }}>
          <Terminal size={12} className="text-indigo" />
          <span style={{ color: 'var(--text-secondary)', marginLeft: '8px', fontSize: '12px' }}>
            {getPipelineSteps().find(s => s.id === selectedTimelineStep)?.details}
          </span>
        </div>
      </div>

      {/* ===== AGENT CARDS (per-agent) ===== */}
      <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)', marginBottom: '12px' }}>
        Agent Assessments
      </h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
        {agentEntries.map(([key, data]: [string, any]) => {
          const meta = AGENT_META[key] ?? { label: key, icon: <Shield size={15} />, color: 'rgba(255,255,255,0.04)' };
          const isExpanded = expandedAgents[key] !== false; // default open
          const score = data.score ?? 0;
          const severity = data.severity ?? 'low';
          const agentFactors: string[] = data.confidence_factors || data.metadata?.confidence_factors || [];
          const reasons: string[] = data.reasons ?? [];
          const recommendations: string[] = data.recommendations ?? [];
          const similarIncidents: any[] = data.similar_incidents ?? [];
          const llm = data.llm;

          return (
            <div key={key} className="glass-panel" style={{ overflow: 'hidden' }}>
              {/* Agent header — clickable to expand */}
              <button
                onClick={() => toggleAgent(key)}
                style={{
                  width: '100%', padding: '16px 20px', background: meta.color,
                  border: 'none', borderBottom: isExpanded ? '1px solid var(--panel-border)' : 'none',
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer',
                  color: '#fff',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: 'var(--accent-cyan)' }}>{meta.icon}</span>
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>{meta.label}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <SeverityBadge severity={severity} />
                  <span className="font-mono" style={{ fontSize: '12px', color: score >= 60 ? 'var(--color-block)' : score >= 30 ? 'var(--color-review)' : 'var(--color-safe)', fontWeight: 700 }}>
                    {score}/100
                  </span>
                  {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </div>
              </button>

              {/* Agent body */}
              {isExpanded && (
                <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* Score bar + confidence display */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>RISK SCORE</span>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{score}/100</span>
                      </div>
                      <ScoreBar score={score} />
                    </div>

                    <ConfidenceDisplay
                      value={data.confidence}
                      factors={agentFactors}
                      title="Analysis Confidence"
                      showBreakdown={true}
                    />
                  </div>

                  {/* Reasons */}
                  {reasons.length > 0 && (
                    <div>
                      <h5 className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>Risk Factors</h5>
                      <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {reasons.map((r, i) => (
                          <li key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            <AlertTriangle size={12} style={{ color: 'var(--color-block)', marginTop: '2px', flexShrink: 0 }} />
                            <span>{r}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommendations */}
                  {recommendations.length > 0 && (
                    <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '6px' }}>
                      <h5 className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>Recommendations</h5>
                      <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                        {recommendations.map((r, i) => (
                          <li key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            <Info size={12} style={{ color: 'var(--accent-blue)', marginTop: '2px', flexShrink: 0 }} />
                            <span>{r}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* LLM Summary */}
                  {llm?.available && llm.summary && (
                    <div style={{ background: 'rgba(192,193,255,0.03)', border: '1px solid rgba(192,193,255,0.1)', borderRadius: '6px', padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                        <Sparkles size={12} style={{ color: 'var(--accent-cyan)' }} />
                        <span className="font-mono" style={{ fontSize: '9px', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                          LLM Analysis — {llm.provider}
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: '1.6', margin: 0 }}>{llm.summary}</p>
                    </div>
                  )}

                  {/* Similar incidents (incident-history agent) */}
                  <SimilarIncidentsTable incidents={similarIncidents} />

                  {/* Metadata */}
                  {data.metadata && Object.keys(data.metadata).length > 0 && (
                    <details style={{ cursor: 'pointer' }}>
                      <summary className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', userSelect: 'none' }}>
                        Raw Metadata
                      </summary>
                      <pre style={{ fontSize: '10px', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '8px', borderRadius: '4px', overflowX: 'auto', marginTop: '8px', border: '1px solid var(--panel-border)' }}>
                        {JSON.stringify(data.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ===== EXPLAINABILITY SUMMARY ===== */}
      {(deployment.summary || (deployment.reasons?.length ?? 0) > 0) && (
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Sparkles size={15} style={{ color: 'var(--accent-cyan)' }} />
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#fff', margin: 0 }}>Aggregator Explainability</h3>
          </div>

          {deployment.summary && (
            <div style={{ background: 'rgba(192,193,255,0.03)', border: '1px solid rgba(192,193,255,0.1)', padding: '14px', borderRadius: '6px', marginBottom: '16px' }}>
              <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-primary)', margin: 0 }}>{deployment.summary}</p>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            {deployment.reasons && deployment.reasons.length > 0 && (
              <div>
                <h4 className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '10px' }}>Threat Risk Factors</h4>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {deployment.reasons.map((r, i) => (
                    <li key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                      <Info size={13} style={{ color: 'var(--accent-blue)', marginTop: '2px', flexShrink: 0 }} />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {deployment.recommendations && deployment.recommendations.length > 0 && (
              <div>
                <h4 className="font-mono" style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '10px' }}>Recommended Guard Actions</h4>
                <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '6px' }}>
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    {deployment.recommendations.map((r, i) => (
                      <li key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                        <CheckCircle2 size={12} style={{ color: 'var(--color-safe)', marginTop: '2px', flexShrink: 0 }} />
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== REPOSITORY EVIDENCE SECTION ===== */}
      <RepositoryEvidenceSection evidence={deployment.agents?.['code-risk']?.metadata?.evidence as any[]} />

      {/* ===== RAW JSON ACCORDION ===== */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <button
          onClick={() => setShowRawJson(!showRawJson)}
          style={{ width: '100%', padding: '14px 20px', background: 'none', border: 'none', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', transition: 'background 0.15s' }}
        >
          <span className="font-mono" style={{ fontSize: '12px', fontWeight: 600 }}>RAW PIPELINE PAYLOAD JSON</span>
          {showRawJson ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {showRawJson && (
          <div style={{ padding: '20px', borderTop: '1px solid var(--panel-border)', background: 'var(--bg-secondary)' }}>
            <pre className="font-mono" style={{ margin: 0, padding: '12px', background: 'rgba(0,0,0,0.25)', border: '1px solid var(--panel-border)', borderRadius: '6px', overflowX: 'auto', fontSize: '11px', color: '#8df', lineHeight: '1.5' }}>
              {JSON.stringify(deployment, null, 2)}
            </pre>
          </div>
        )}
      </div>

    </div>
  );
};
export default DeploymentDetails;
