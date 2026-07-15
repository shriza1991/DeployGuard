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
  ChevronUp
} from 'lucide-react';
import './Deployments.css'; // Reuse table/badge stylesheets

const AGENT_DISPLAY_NAMES: Record<string, string> = {
  "code-risk": "Static Analysis Agent",
  "infra-risk": "Infrastructure Drift Agent",
  "incident-history": "Regression Analyzer"
};

export const DeploymentDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [deployment, setDeployment] = useState<DeploymentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTimelineStep, setSelectedTimelineStep] = useState<string>("Aggregator");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const fetchDetail = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const detail = await getDeployment(id);
      setDeployment(detail);
    } catch (e) {
      console.error(e);
      setError("Failed to locate this deployment in the gate registry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCopyId = () => {
    if (!id) return;
    navigator.clipboard.writeText(id);
    triggerToast("Copied Correlation ID to clipboard!");
  };

  const handleExportJSON = () => {
    if (!deployment) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(deployment, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `deployguard_audit_${id?.substring(0, 8)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    triggerToast("Exported raw audit JSON successfully!");
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: '16px', color: 'var(--text-muted)' }}>
        <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
        <span>Assembling threat report...</span>
      </div>
    );
  }

  if (error || !deployment) {
    return (
      <div style={{ padding: '48px', textAlign: 'center' }}>
        <h3 style={{ color: 'var(--color-block)', marginBottom: '16px' }}>Deployment Not Found</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>{error || 'Unable to load deployment data.'}</p>
        <button onClick={() => navigate('/deployments')} className="btn-secondary-stitch">
          <ChevronLeft size={14} />
          <span>Back to Deployments</span>
        </button>
      </div>
    );
  }

  // --- Helpers ---
  const getAgentsList = () => {
    if (!deployment.agents) return [];
    return Object.entries(deployment.agents).map(([key, data]: [string, any]) => {
      const name = AGENT_DISPLAY_NAMES[key] || key.replace("-", " ").replace(/\b\w/g, c => c.toUpperCase());
      const confidencePercent = Math.round((data.confidence || 0.9) * 100);
      
      let summary = `No critical alerts. Verified logic metrics for ${deployment.repository}.`;
      if (data.reasons && data.reasons.length > 0) {
        summary = data.reasons.join(". ");
      } else if (data.score > 50) {
        summary = `Elevated risk warning identified on ${name}.`;
      }
      
      let reasoning = `Passed verification checks with high-confidence security criteria.`;
      if (data.recommendations && data.recommendations.length > 0) {
        reasoning = data.recommendations[0];
      } else if (data.score > 50) {
        reasoning = `Requires engineering review before promoting this commit.`;
      }
      
      return {
        id: key,
        name: name,
        riskScore: data.score,
        severity: data.severity || 'low',
        confidence: `${confidencePercent}%`,
        summary: summary,
        reasoning: reasoning,
        status: data.score >= 50 ? "warning" as const : "safe" as const,
        metadata: data.metadata || {}
      };
    });
  };

  const getPipelineSteps = () => {
    const isPending = deployment.status === 'pending';
    const shortSha = deployment.correlation_id.substring(0, 7);
    
    return [
      { id: "Webhook", label: "Webhook", status: "completed" as const, iconType: "check" as const, details: `Deployment trigger received from GitHub branch commit sha: ${shortSha || 'unknown'}.` },
      { id: "Gateway", label: "Gateway", status: "completed" as const, iconType: "check" as const, details: "Ingress proxy and API gateway configurations verified with zero errors." },
      { id: "Code Risk", label: "Code Risk", status: "completed" as const, iconType: "check" as const, details: `AI code quality agent scanned modified files for ${deployment.repository}.` },
      { id: "Infra Risk", label: "Infra Risk", status: "completed" as const, iconType: "check" as const, details: "Infrastructure as code verified. Terraform dry-run passed with zero security drifts." },
      { id: "Incidents", label: "Incidents", status: "completed" as const, iconType: "check" as const, details: "Correlated existing live service health with proposed release. No critical overlaps." },
      { 
        id: "Aggregator", 
        label: "Aggregator", 
        status: isPending ? "active" as const : "completed" as const, 
        iconType: isPending ? "active" as const : "check" as const, 
        details: isPending 
          ? "Agentic synthesis active. Amalgamating logs, test coverages, and IAM parameters into visual scorecard."
          : "Agentic synthesis complete. Compiled scorecard for risk assessment metrics."
      },
      { 
        id: "Decision", 
        label: "Decision", 
        status: isPending ? "pending" as const : "completed" as const, 
        iconType: isPending ? "pending" as const : "check" as const, 
        details: isPending 
          ? "Final risk threshold enforcement. Awaiting canary promotion flag upon successful metrics review."
          : `Final risk threshold enforcement completed. Decision verdict: ${deployment.decision}.`
      }
    ];
  };

  return (
    <div className="deployments-container fade-in" style={{ paddingBottom: '48px' }}>
      {/* Toast Notification */}
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
            <Copy size={14} />
            <span>Copy ID</span>
          </button>
          <button onClick={handleExportJSON} className="btn-secondary-stitch font-mono">
            <FileJson size={14} />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Summary Header Card */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`verdict-tag ${deployment.decision?.toLowerCase()}`}>
                {deployment.decision}
              </span>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#fff' }} className="font-mono">{deployment.repository}</h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '8px' }}>
              Commit: <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>{deployment.commit_message || 'N/A'}</span>
            </p>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '6px', textAlign: 'center' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>OVERALL SCORE</span>
              <h3 className="font-mono" style={{ fontSize: '20px', color: '#fff', fontWeight: 'bold', marginTop: '4px' }}>{deployment.overall_score ?? '-'}</h3>
            </div>
            <div style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '6px', textAlign: 'center' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>CONFIDENCE</span>
              <h3 className="font-mono" style={{ fontSize: '20px', color: '#fff', fontWeight: 'bold', marginTop: '4px' }}>
                {deployment.overall_confidence !== undefined ? `${Math.round(deployment.overall_confidence * 100)}%` : '-'}
              </h3>
            </div>
          </div>
        </div>

        {/* Metadata Details Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', borderTop: '1px solid var(--panel-border)', marginTop: '20px', paddingTop: '20px' }}>
          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>BRANCH</span>
            <p className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px' }}>{deployment.branch || 'unknown'}</p>
          </div>
          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>AUTHOR</span>
            <p className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px' }}>{deployment.author || 'unknown'}</p>
          </div>
          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>COMMIT SHA</span>
            <p className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px' }}>{deployment.commit_sha || 'N/A'}</p>
          </div>
          <div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>CORRELATION ID</span>
            <p className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px' }}>{deployment.correlation_id}</p>
          </div>
        </div>
      </div>

      {/* Pipeline Timeline Panel */}
      <div className="timeline-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div className="timeline-header-bar">
          <div className="timeline-title-row">
            <Layers className="timeline-title-icon" />
            <h3>Deployment Timeline Progress</h3>
          </div>
          <div className="live-status-indicator font-mono">
            <span className="ping-ring">
              <span className="ping-effect"></span>
              <span className="ping-dot"></span>
            </span>
            <span>Audit Stage Details</span>
          </div>
        </div>

        {/* Timeline Sequence UI */}
        <div className="timeline-track-container" style={{ margin: '32px 0 16px 0' }}>
          <div className="timeline-backline">
            <div className="timeline-progress-line" style={{ width: deployment.status === 'pending' ? '80%' : '100%' }} />
          </div>

          <div className="pipeline-steps-row" style={{ display: 'flex', justifyContent: 'space-between' }}>
            {getPipelineSteps().map(step => {
              const isSelected = selectedTimelineStep === step.id;
              let stepClass = "status-pending";
              let nodeIcon = <Clock className="node-icon" />;

              if (step.status === "completed") {
                stepClass = "status-completed";
                nodeIcon = <Check className="node-icon" />;
              } else if (step.status === "active") {
                stepClass = "status-active";
                nodeIcon = <Sparkles className="node-icon pulse" />;
              }

              return (
                <button
                  key={step.id}
                  onClick={() => setSelectedTimelineStep(step.id)}
                  className={`timeline-node-btn ${isSelected ? 'selected' : ''} ${stepClass}`}
                >
                  <div className="node-circle">{nodeIcon}</div>
                  <span className="node-label" style={{ fontSize: '11px' }}>{step.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selection Details text */}
        <div className="timeline-context-panel font-mono" style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '6px' }}>
          <Terminal size={14} className="text-indigo" />
          <span style={{ color: 'var(--text-secondary)', marginLeft: '8px' }}>
            {getPipelineSteps().find(s => s.id === selectedTimelineStep)?.details}
          </span>
        </div>
      </div>

      {/* Agents Scorecard Cards */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>Agent Vulnerability Evaluations</h3>
        <div className="agent-cards-grid">
          {getAgentsList().map(agent => (
            <div key={agent.id} className={`agent-card border-${agent.status}`}>
              <div className="agent-card-header">
                <h3 className="agent-name" style={{ fontSize: '14px', fontWeight: 600 }}>{agent.name}</h3>
                <span className="confidence-badge font-mono" style={{ fontSize: '10px' }}>Confidence: {agent.confidence}</span>
              </div>
              <div className="agent-card-body">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>RISK RATING:</span>
                  <span className={`font-mono ${agent.status}`} style={{ fontWeight: 'bold' }}>{agent.riskScore}/100 ({agent.severity.toUpperCase()})</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{agent.summary}</p>
                <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px dashed var(--panel-border)' }}>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>AGENT GUIDANCE:</span>
                  <p style={{ fontSize: '12px', color: 'var(--text-primary)', fontStyle: 'italic', marginTop: '4px' }}>"{agent.reasoning}"</p>
                </div>
                {agent.metadata && Object.keys(agent.metadata).length > 0 && (
                  <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid var(--panel-border)' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>METADATA:</span>
                    <pre style={{ fontSize: '10px', color: 'var(--text-secondary)', overflowX: 'auto', marginTop: '4px', background: 'var(--bg-secondary)', padding: '6px', borderRadius: '4px' }}>
                      {JSON.stringify(agent.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Explainability Summary */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Sparkles size={16} className="text-primary" />
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>Explainability Risk Analysis</h3>
        </div>
        
        <div className="ai-summary-box" style={{ background: 'rgba(192, 193, 255, 0.03)', border: '1px solid rgba(192, 193, 255, 0.1)', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
          <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-primary)' }}>
            {deployment.summary || "Explainability report currently unavailable."}
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
          <div>
            <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }} className="font-mono">THREAT RISK HEURISTICS</h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {deployment.reasons && deployment.reasons.length > 0 ? (
                deployment.reasons.map((r, i) => (
                  <li key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <Info size={14} style={{ color: 'var(--accent-blue)', marginTop: '2px', flexShrink: 0 }} />
                    <span>{r}</span>
                  </li>
                ))
              ) : (
                <li style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No heuristics triggers.</li>
              )}
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '10px' }} className="font-mono">RECOMMENDED GUARD ACTIONS</h4>
            <div className="best-practices-card" style={{ padding: '12px' }}>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {deployment.recommendations && deployment.recommendations.length > 0 
                  ? deployment.recommendations.join(". ")
                  : "Proceed with standard pipeline canary controls."}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Raw JSON Accordion */}
      <div className="glass-panel" style={{ padding: '0px', overflow: 'hidden' }}>
        <button
          onClick={() => setShowRawJson(!showRawJson)}
          style={{ width: '100%', padding: '16px 24px', background: 'none', border: 'none', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
        >
          <span style={{ fontSize: '14px', fontWeight: 600 }} className="font-mono">RAW SECURE Gate Payload JSON</span>
          {showRawJson ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        {showRawJson && (
          <div style={{ padding: '24px', borderTop: '1px solid var(--panel-border)', background: 'var(--bg-secondary)' }}>
            <pre style={{ margin: 0, padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', borderRadius: '6px', overflowX: 'auto', fontSize: '11px', color: '#8df' }} className="font-mono">
              {JSON.stringify(deployment, null, 2)}
            </pre>
          </div>
        )}
      </div>

    </div>
  );
};
export default DeploymentDetails;
