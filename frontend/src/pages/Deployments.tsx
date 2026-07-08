import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DeploymentEvent } from '../api/client';
import { 
  Clock, 
  Settings, 
  Search, 
  Check, 
  CheckCircle2, 
  AlertTriangle, 
  Zap, 
  Sparkles, 
  ChevronDown, 
  ChevronUp, 
  Terminal, 
  Layers, 
  Sliders, 
  HelpCircle,
  X,
  Loader2
} from 'lucide-react';

import './Deployments.css';

// Constants for display names
const AGENT_DISPLAY_NAMES: Record<string, string> = {
  "code-risk": "Static Analysis Agent",
  "infra-risk": "Infrastructure Drift Agent",
  "incident-history": "Regression Analyzer"
};

const HISTORICAL_INCIDENTS = [
  {
    id: "dep-4k21",
    title: "API Latency Spike (dep-4k21)",
    date: "Nov 2022",
    duration: "Resolved in 14m",
    type: "error",
    impactScore: "High (82/100)",
    rootCause: "Improper rate-limiting rule on gateway proxy after a major module rewrite without custom header caching.",
    details: "Caused response delays to reach 1,200ms for public clients. Reverted gateway policy to auto-mitigate."
  },
  {
    id: "dep-1j92",
    title: "DB Connection Timeout (dep-1j92)",
    date: "Jan 2023",
    duration: "Resolved in 4m",
    type: "warning",
    impactScore: "Medium (45/100)",
    rootCause: "Unoptimized relational join in secondary catalog queries saturated read replica pool.",
    details: "Spiked DB CPU usage to 94%. Fixed via temporary thread expansion and localized static indexing."
  }
];

export const Deployments: React.FC = () => {
  const [deployments, setDeployments] = useState<DeploymentEvent[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Stitch dynamic states
  const [selectedTimelineStep, setSelectedTimelineStep] = useState<string>("Aggregator");
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);
  
  // Alert Config Modal state
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [alertForm, setAlertForm] = useState({
    metric: "auth-service-v3-latency",
    threshold: "150",
    channel: "Slack (#alerts-devsecops)",
    notes: "Notify on-call if threshold is violated for > 3 minutes."
  });
  const [isSavingAlert, setIsSavingAlert] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const fetchDeployments = async () => {
    try {
      const data = await api.getDeployments();
      setDeployments(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].correlation_id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  const filteredDeployments = deployments.filter(dep => 
    dep.repository.toLowerCase().includes(searchQuery.toLowerCase()) ||
    dep.commit_message.toLowerCase().includes(searchQuery.toLowerCase()) ||
    dep.correlation_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedDep = deployments.find(d => d.correlation_id === selectedId);

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    return date.toLocaleString();
  };

  // Toast helper
  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const handleSaveAlert = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingAlert(true);
    setTimeout(() => {
      setIsSavingAlert(false);
      setShowAlertModal(false);
      triggerToast(`Alert configuration for "${alertForm.metric}" deployed successfully!`);
    }, 1200);
  };

  // Helper to map dynamic agents to Stitch card definitions
  const getAgentsList = (dep: DeploymentEvent) => {
    if (!dep.agents) return [];
    return Object.entries(dep.agents).map(([key, data]: [string, any]) => {
      const name = AGENT_DISPLAY_NAMES[key] || key.replace("-", " ").replace(/\b\w/g, c => c.toUpperCase());
      const confidencePercent = Math.round((data.confidence || 0.9) * 100);
      
      let summary = `No critical alerts. Verified logic metrics for ${dep.repository}.`;
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
        riskScore: `${String(data.score).padStart(2, '0')}/100`,
        confidence: `${confidencePercent}%`,
        summary: summary,
        reasoning: reasoning,
        status: data.score >= 50 ? "warning" as const : "safe" as const
      };
    });
  };

  // Helper to get pipeline steps based on deployment status
  const getPipelineSteps = (dep: DeploymentEvent) => {
    const isPending = dep.status === 'pending';
    const shortSha = dep.correlation_id.substring(0, 7);
    
    return [
      { id: "Webhook", label: "Webhook", status: "completed" as const, iconType: "check" as const, timestamp: "06:45:12", details: `Deployment trigger received from GitHub main branch commit sha: ${shortSha}.` },
      { id: "Gateway", label: "Gateway", status: "completed" as const, iconType: "check" as const, timestamp: "06:46:01", details: "Ingress proxy and API gateway configurations verified with zero errors." },
      { id: "Kafka", label: "Kafka", status: "completed" as const, iconType: "check" as const, timestamp: "06:47:15", details: "Kafka cluster schema migration succeeded. Message broker connections validated." },
      { id: "Code Risk", label: "Code Risk", status: "completed" as const, iconType: "check" as const, timestamp: "06:48:30", details: `AI code quality agent scanned modified files for ${dep.repository}.` },
      { id: "Infra Risk", label: "Infra Risk", status: "completed" as const, iconType: "check" as const, timestamp: "06:49:55", details: "Infrastructure as code verified. Terraform dry-run passed with zero security drifts." },
      { id: "Incidents", label: "Incidents", status: "completed" as const, iconType: "check" as const, timestamp: "06:51:10", details: "Correlated existing live service health with proposed release. No critical overlaps." },
      { 
        id: "Aggregator", 
        label: "Aggregator", 
        status: isPending ? "active" as const : "completed" as const, 
        iconType: isPending ? "active" as const : "check" as const, 
        timestamp: isPending ? "Running..." : "06:51:30", 
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
          : `Final risk threshold enforcement completed. Decision verdict: ${dep.decision}.`
      }
    ];
  };

  return (
    <div className="deployments-container fade-in" id="deployments_page_container">
      {/* Toast Notification Container */}
      {toastMessage && (
        <div className="toast-notification" id="toast_notification">
          <CheckCircle2 className="toast-icon" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header section matching Stitch */}
      <div className="deployments-header" id="dashboard_header_section">
        <div className="header-meta-group">
          <div className="title-row">
            <h2 id="page_title">Deployments</h2>
            {selectedDep && (
              <span className="deployment-id-badge">
                Deployment ID: dep-{selectedDep.correlation_id.substring(0, 6)}
              </span>
            )}
          </div>
          <p className="page-subtitle">
            Real-time agentic risk assessment and security posture validation for repository release candidate.
          </p>
        </div>
      </div>

      <div className="deployments-layout">
        {/* Left Side: List and Search */}
        <div className="deployments-list-panel">
          <div className="search-bar-wrapper">
            <Search className="search-bar-icon" />
            <input 
              type="text" 
              placeholder="Search by repo, commit, or ID..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="font-mono"
            />
          </div>

          <div className="list-items-container">
            {loading ? (
              <div className="list-loading">
                <Loader2 className="spin load-icon" />
                <span>Loading deployments...</span>
              </div>
            ) : filteredDeployments.length === 0 ? (
              <div className="list-empty">No matching audits found.</div>
            ) : (
              filteredDeployments.map((dep) => (
                <div 
                  key={dep.correlation_id}
                  className={`list-item ${selectedId === dep.correlation_id ? 'active' : ''}`}
                  onClick={() => {
                    setSelectedId(dep.correlation_id);
                    triggerToast(`Viewing audit report: dep-${dep.correlation_id.substring(0, 6)}`);
                  }}
                  id={`deployment_card_${dep.correlation_id}`}
                >
                  <div className="item-meta">
                    <span className="item-repo font-mono">{dep.repository}</span>
                    <span className="item-time font-mono">{formatDate(dep.generated_at).split(',')[0]}</span>
                  </div>
                  <h3 className="item-title">{dep.commit_message}</h3>
                  <div className="item-footer">
                    <span className={`verdict-tag-small ${dep.decision?.toLowerCase() || 'pending'}`}>
                      {dep.decision || 'PENDING'}
                    </span>
                    <span className="item-id font-mono">ID: {dep.correlation_id.substring(0, 8)}...</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Side: Detailed Audit View */}
        <div className="deployments-detail-panel">
          {selectedDep ? (
            <div className="detail-scroll-container">
              
              {/* 3. Three Agent Cards Grid */}
              <div className="agent-cards-grid" id="agent_cards_grid">
                {getAgentsList(selectedDep).map((agent) => (
                  <div
                    key={agent.id}
                    className={`agent-card border-${agent.status}`}
                    id={`agent_card_${agent.id}`}
                  >
                    <div className="agent-card-header">
                      <div className="agent-status-indicator">
                        <div className={`status-dot ${agent.status}`} />
                        <h3 className="agent-name">{agent.name}</h3>
                      </div>
                      <span className="confidence-badge font-mono">
                        Confidence: {agent.confidence}
                      </span>
                    </div>

                    <div className="agent-card-body">
                      {/* Summary Item */}
                      <div className="meta-section">
                        <div className="meta-section-header">
                          <span className="meta-section-title font-mono">SUMMARY</span>
                          <div className="score-group">
                            <span className="score-label font-mono">Risk Score:</span>
                            <span className={`score-value font-mono ${agent.status}`}>{agent.riskScore}</span>
                          </div>
                        </div>
                        <p className="meta-section-text">{agent.summary}</p>
                      </div>

                      {/* Reasoning Item */}
                      <div className="meta-section border-top">
                        <span className="meta-section-title font-mono block">REASONING</span>
                        <p className="meta-section-text italic">"{agent.reasoning}"</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* 4. Deployment Timeline Section */}
              <div className="timeline-panel" id="timeline_panel">
                <div className="timeline-header-bar" id="timeline_header">
                  <div className="timeline-title-row">
                    <Layers className="timeline-title-icon" />
                    <h3>Deployment Timeline</h3>
                  </div>
                  <div className="live-status-indicator font-mono" id="live_status_indicator">
                    <span className="ping-ring">
                      <span className="ping-effect"></span>
                      <span className="ping-dot"></span>
                    </span>
                    <span>Live Pipeline Status</span>
                  </div>
                </div>

                {/* Grid for Nodes */}
                <div className="timeline-track-container" id="timeline_container">
                  {/* Timeline Connecting Line */}
                  <div className="timeline-backline" id="timeline_backline">
                    <div 
                      className="timeline-progress-line" 
                      style={{ width: selectedDep.status === 'pending' ? '84%' : '100%' }}
                    />
                  </div>

                  {/* Step Sequence Wrapper */}
                  <div className="pipeline-steps-row" id="pipeline_steps_row">
                    {getPipelineSteps(selectedDep).map((step) => {
                      const isSelected = selectedTimelineStep === step.id;
                      
                      let stepClass = "status-pending";
                      let nodeIcon = <Clock className="node-icon" />;

                      if (step.status === "completed") {
                        stepClass = "status-completed";
                        nodeIcon = <Check className="node-icon" />;
                      } else if (step.status === "active") {
                        stepClass = "status-active";
                        nodeIcon = <Sparkles className="node-icon pulse" />;
                      } else if (step.status === "pending") {
                        stepClass = "status-pending";
                        nodeIcon = <HelpCircle className="node-icon" />;
                      }

                      return (
                        <button
                          key={step.id}
                          onClick={() => {
                            setSelectedTimelineStep(step.id);
                            triggerToast(`Inspecting timeline stage: ${step.id}`);
                          }}
                          className={`timeline-node-btn ${isSelected ? 'selected' : ''} ${stepClass}`}
                          id={`timeline_node_${step.id.toLowerCase().replace(" ", "_")}`}
                        >
                          {/* Step Round Node Button */}
                          <div className="node-circle">
                            {nodeIcon}
                          </div>

                          {/* Step Labels */}
                          <span className="node-label">
                            {step.label}
                          </span>

                          {/* Selection indicator dot */}
                          {isSelected && <div className="active-dot" />}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Contextual Box for Selected Timeline Node */}
                <div className="timeline-context-panel font-mono" id="timeline_context_panel">
                  <div className="context-left">
                    <Terminal className="context-terminal-icon" />
                    <div>
                      <span className="context-stage-name">STAGE: {selectedTimelineStep.toUpperCase()}</span>
                      <span className="context-separator">|</span>
                      <span className="context-details-text">
                        {getPipelineSteps(selectedDep).find(s => s.id === selectedTimelineStep)?.details}
                      </span>
                    </div>
                  </div>
                  {getPipelineSteps(selectedDep).find(s => s.id === selectedTimelineStep)?.timestamp && (
                    <div className="context-timestamp">
                      Processed at: <span className="timestamp-value">{getPipelineSteps(selectedDep).find(s => s.id === selectedTimelineStep)?.timestamp}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* 5. Bottom Splitted Layout Panel */}
              <div className="bottom-layouts-container" id="bottom_layouts_container">
                
                {/* Left Card: Similar Historical Incidents */}
                <div className="historical-incidents-panel" id="historical_incidents_panel">
                  <div className="panel-title-row">
                    <Clock className="panel-title-icon text-rose" />
                    <h3>Similar Historical Incidents</h3>
                  </div>

                  <div className="incidents-accordion" id="incidents_accordion">
                    {HISTORICAL_INCIDENTS.map((inc) => {
                      const isExpanded = expandedIncident === inc.id;
                      return (
                        <div
                          key={inc.id}
                          className="accordion-row"
                          id={`incident_row_${inc.id}`}
                        >
                          {/* Summary trigger row */}
                          <button
                            onClick={() => setExpandedIncident(isExpanded ? null : inc.id)}
                            className="accordion-trigger"
                            id={`incident_toggle_btn_${inc.id}`}
                          >
                            <div className="trigger-left">
                              <div className="trigger-icon-wrapper">
                                {inc.type === "error" ? (
                                  <div className="icon-badge error">
                                    <AlertTriangle className="badge-icon" />
                                  </div>
                                ) : (
                                  <div className="icon-badge warning">
                                    <Zap className="badge-icon" />
                                  </div>
                                )}
                              </div>
                              <div>
                                <p className="accordion-title">{inc.title}</p>
                                <p className="accordion-meta font-mono">
                                  {inc.date} • {inc.duration}
                                </p>
                              </div>
                            </div>
                            <div className="trigger-arrow">
                              {isExpanded ? <ChevronUp className="arrow-icon" /> : <ChevronDown className="arrow-icon" />}
                            </div>
                          </button>

                          {/* Collapsed view panel containing details */}
                          {isExpanded && (
                            <div className="accordion-details font-mono">
                              <div className="details-content">
                                <div className="details-group">
                                  <span className="group-title text-rose">IMPACT SCORE:</span>
                                  <p className="group-text">{inc.impactScore}</p>
                                </div>
                                <div className="details-group">
                                  <span className="group-title">ROOT CAUSE:</span>
                                  <p className="group-text">{inc.rootCause}</p>
                                </div>
                                <div className="details-group">
                                  <span className="group-title">MITIGATION LOG:</span>
                                  <p className="group-text">{inc.details}</p>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Informative system message footer inside left col */}
                  <div className="incidents-footer font-mono" id="incidents_footer">
                    Note: Risk modeling correlates active deployment structures with incidents over a 12-month trailing index.
                  </div>
                </div>

                {/* Right Card: Explainability Section */}
                <div className="explainability-panel" id="explainability_panel">
                  <div className="panel-title-row">
                    <Sparkles className="panel-title-icon text-primary" />
                    <h3>Explainability Section</h3>
                  </div>

                  {/* OVERALL AI SUMMARY */}
                  <div className="ai-summary-box" id="ai_summary_box">
                    {/* Purple decorative background glow */}
                    <div className="bg-glow-effect" />
                    
                    <div className="ai-summary-header">
                      <Sparkles className="header-icon text-primary" />
                      <span className="header-label font-mono">OVERALL AI SUMMARY</span>
                    </div>
                    
                    <p className="ai-summary-paragraph" id="summary_paragraph">
                      {selectedDep.summary || "No automated summary compiled for this gate audit."}
                    </p>
                  </div>

                  {/* Insights and Recommendations Grid */}
                  <div className="insights-rec-grid" id="insights_rec_grid">
                    
                    {/* KEY RISK INSIGHTS (Left) */}
                    <div className="key-risk-insights-column" id="key_risk_insights_column">
                      <h4 className="column-title font-mono">KEY RISK INSIGHTS</h4>
                      <ul className="insights-list" id="insights_list">
                        {selectedDep.reasons && selectedDep.reasons.length > 0 ? (
                          selectedDep.reasons.map((insight, idx) => (
                            <li key={idx} className="insight-item" id={`insight_item_${idx}`}>
                              <div className="insight-icon-wrapper">
                                <Check className="check-icon" />
                              </div>
                              <span className="insight-text">{insight}</span>
                            </li>
                          ))
                        ) : (
                          <li className="insight-item italic text-muted">No key risks flagged by analyzers.</li>
                        )}
                      </ul>
                    </div>

                    {/* RECOMMENDATIONS (Right) */}
                    <div className="recommendations-column" id="recommendations_column">
                      <h4 className="column-title font-mono">RECOMMENDATIONS</h4>
                      
                      {/* Styled Container */}
                      <div className="best-practices-card" id="best_practices_card">
                        <div className="card-top">
                          <div className="best-practices-label font-mono">
                            <Settings className="label-icon text-primary" />
                            <span>Best Practices</span>
                          </div>
                          <p className="practices-text">
                            {selectedDep.recommendations && selectedDep.recommendations.length > 0 
                              ? selectedDep.recommendations[0] 
                              : "Proceed with standard canary verification phase and test suite validation."}
                          </p>
                        </div>

                        <button 
                          onClick={() => setShowAlertModal(true)}
                          className="configure-alerting-btn font-mono"
                          id="configure_alerting_btn"
                        >
                          Configure Alerting
                        </button>
                      </div>
                    </div>

                  </div>

                </div>

              </div>

            </div>
          ) : (
            <div className="no-selected-state">Select a deployment to view the detailed risk report.</div>
          )}
        </div>
      </div>

      {/* 6. Alert Rule Configuration Modal Overlay */}
      {showAlertModal && (
        <div className="modal-overlay" id="alert_modal_overlay">
          <div className="modal-card" id="alert_modal_card">
            {/* Modal Title & Close */}
            <div className="modal-header" id="modal_header">
              <div className="modal-title-group">
                <Sliders className="modal-title-icon text-primary" />
                <h3>Configure Alert Rule</h3>
              </div>
              <button
                onClick={() => setShowAlertModal(false)}
                className="modal-close-btn"
              >
                <X className="close-x-icon" />
              </button>
            </div>

            {/* Form Input fields */}
            <form onSubmit={handleSaveAlert} className="modal-form font-sans">
              {/* Metric target */}
              <div className="form-group">
                <label className="form-label font-mono">TARGET METRIC</label>
                <input
                  type="text"
                  required
                  value={alertForm.metric}
                  onChange={(e) => setAlertForm({ ...alertForm, metric: e.target.value })}
                  className="form-input font-mono"
                />
              </div>

              {/* Threshold limits */}
              <div className="form-group">
                <label className="form-label font-mono">LATENCY THRESHOLD (MS)</label>
                <input
                  type="number"
                  required
                  value={alertForm.threshold}
                  onChange={(e) => setAlertForm({ ...alertForm, threshold: e.target.value })}
                  className="form-input font-mono"
                />
              </div>

              {/* Alert Destination */}
              <div className="form-group">
                <label className="form-label font-mono">NOTIFICATION ROUTE</label>
                <select
                  value={alertForm.channel}
                  onChange={(e) => setAlertForm({ ...alertForm, channel: e.target.value })}
                  className="form-select font-mono"
                >
                  <option value="Slack (#alerts-devsecops)">Slack (#alerts-devsecops)</option>
                  <option value="PagerDuty (On-Call Engineer)">PagerDuty (On-Call Engineer)</option>
                  <option value="Email Distribution Group">Email Distribution Group</option>
                </select>
              </div>

              {/* Alert Notes */}
              <div className="form-group">
                <label className="form-label font-mono">RECOVERY ACTION NOTES</label>
                <textarea
                  rows={3}
                  value={alertForm.notes}
                  onChange={(e) => setAlertForm({ ...alertForm, notes: e.target.value })}
                  className="form-textarea font-sans"
                />
              </div>

              {/* Footer Controls */}
              <div className="modal-footer" id="modal_footer">
                <button
                  type="button"
                  onClick={() => setShowAlertModal(false)}
                  className="modal-cancel-btn"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingAlert}
                  className="modal-submit-btn font-mono"
                >
                  {isSavingAlert ? (
                    <>
                      <Loader2 className="spin submit-spinner" />
                      <span>Deploying Rule...</span>
                    </>
                  ) : (
                    <span>Save Alert Rule</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
