import React, { useState } from "react";
import { 
  Shield, 
  Activity, 
  Bot, 
  Clock, 
  TrendingUp, 
  Settings, 
  Search, 
  Bell, 
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
  Volume2, 
  HelpCircle,
  X,
  Plus,
  Send,
  Loader2
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

// --- Types ---
interface AgentCard {
  id: string;
  name: string;
  riskScore: string;
  confidence: string;
  summary: string;
  reasoning: string;
  status: "safe" | "warning" | "info";
}

interface PipelineStep {
  id: string;
  label: string;
  status: "completed" | "active" | "pending";
  iconType: "check" | "active" | "pending";
  timestamp?: string;
  details: string;
}

interface HistoricalIncident {
  id: string;
  title: string;
  date: string;
  duration: string;
  type: "error" | "warning";
  details: string;
  impactScore: string;
  rootCause: string;
}

export default function Deployments() {
  // --- State Managers ---
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

  // --- Static and Agent Data ---
  const initialAgents: AgentCard[] = [
    {
      id: "agent-1",
      name: "Static Analysis Agent",
      riskScore: "15/100",
      confidence: "99%",
      summary: "No critical vulnerabilities found. 12 minor linting warnings ignored by policy.",
      reasoning: "Static analysis passed with 0 security hotspots. Dependency tree matches the signed manifest.",
      status: "safe"
    },
    {
      id: "agent-2",
      name: "Infrastructure Drift Agent",
      riskScore: "08/100",
      confidence: "97%",
      summary: "Terraform plan verified. No drift detected in production state.",
      reasoning: "No IAM over-provisioning detected. Security group rules follow the 'least privilege' principle.",
      status: "safe"
    },
    {
      id: "agent-3",
      name: "Regression Analyzer",
      riskScore: "12/100",
      confidence: "98%",
      summary: "No recurring regression patterns detected for these service modules.",
      reasoning: "Similar logic changes in the last 6 months have 0 incident correlation in Datadog/Sentry logs.",
      status: "safe"
    }
  ];

  const pipelineSteps: PipelineStep[] = [
    { id: "Webhook", label: "Webhook", status: "completed", iconType: "check", timestamp: "06:45:12", details: "Deployment trigger received from GitHub main branch commit sha: 8f2a58d." },
    { id: "Gateway", label: "Gateway", status: "completed", iconType: "check", timestamp: "06:46:01", details: "Ingress proxy and API gateway configurations verified with zero errors." },
    { id: "Kafka", label: "Kafka", status: "completed", iconType: "check", timestamp: "06:47:15", details: "Kafka cluster schema migration succeeded. Message broker connections validated." },
    { id: "Code Risk", label: "Code Risk", status: "completed", iconType: "check", timestamp: "06:48:30", details: "AI code quality agent scanned 14 files, 1,240 LOC modified, safety index is 98.8%." },
    { id: "Infra Risk", label: "Infra Risk", status: "completed", iconType: "check", timestamp: "06:49:55", details: "Infrastructure as code verified. Terraform dry-run passed against AWS region us-east-1." },
    { id: "Incidents", label: "Incidents", status: "completed", iconType: "check", timestamp: "06:51:10", details: "Correlated existing live service health with proposed release. No critical overlaps." },
    { id: "Aggregator", label: "Aggregator", status: "active", iconType: "active", timestamp: "Running...", details: "Agentic synthesis active. Amalgamating logs, test coverages, and IAM parameters into visual scorecard." },
    { id: "Decision", label: "Decision", status: "pending", iconType: "pending", details: "Final risk threshold enforcement. Awaiting canary promotion flag upon successful metrics review." }
  ];

  const historicalIncidents: HistoricalIncident[] = [
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

  const keyRiskInsights = [
    "Minor configuration change in Gateway could affect p99 latency by ~5ms.",
    "New telemetry tags added; ensure Prometheus scraping intervals remain stable."
  ];

  // Trigger temporary notification
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

  return (
    <div className="w-full min-h-screen bg-[#0d0d15] text-[#e4e1ed] font-sans antialiased p-8 space-y-6" id="deployments_page_container">
      
      {/* Toast Notification Container */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-4 right-4 z-50 flex items-center gap-2 bg-[#1f1f27] border border-[#4edea3] text-[#4edea3] px-4 py-3 rounded-lg shadow-xl text-sm font-mono"
            id="toast_notification"
          >
            <CheckCircle2 className="w-4 h-4 text-[#4edea3]" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header Description & Search State Alert */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4" id="dashboard_header_section">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold tracking-tight text-white font-sans" id="page_title">Deployments</h2>
            <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/10 text-[#c0c1ff] font-mono border border-indigo-500/20 uppercase font-semibold">
              Deployment ID: dep-8f2a
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time agentic risk assessment and security posture validation for transaction service release candidate.
          </p>
        </div>
      </div>

      {/* 3. Three Agent Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6" id="agent_cards_grid">
        {initialAgents.map((agent, idx) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            whileHover={{ borderColor: "var(--color-brand-border-hover)" }}
            className="bg-[#13131b] border border-[#27272a] rounded-lg p-5 flex flex-col justify-between hover:shadow-xl transition-all relative"
            id={`agent_card_${agent.id}`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse" />
                <h3 className="text-sm font-bold text-white tracking-tight">{agent.name}</h3>
              </div>
              <span className="font-mono text-xs font-semibold text-[#4edea3] bg-[#4edea3]/10 px-2.5 py-1 rounded-full border border-[#4edea3]/20">
                Confidence: {agent.confidence}
              </span>
            </div>

            <div className="space-y-4">
              {/* Summary Item */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold tracking-wider text-zinc-500 uppercase">SUMMARY</span>
                  {/* Risk score pill aligned on right for readability */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono text-zinc-500">Risk Score:</span>
                    <span className="font-mono text-xs text-emerald-400 font-semibold">{agent.riskScore}</span>
                  </div>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed font-sans">{agent.summary}</p>
              </div>

              {/* Reasoning Item */}
              <div className="space-y-1 pt-3 border-t border-[#1f1f27]">
                <span className="text-[10px] font-mono font-bold tracking-wider text-zinc-500 uppercase block">REASONING</span>
                <p className="text-xs text-zinc-400 leading-relaxed font-sans italic">"{agent.reasoning}"</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* 4. Deployment Timeline Section */}
      <div className="bg-[#13131b] border border-[#27272a] rounded-lg p-6" id="timeline_panel">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#27272a] pb-4 mb-6 gap-2" id="timeline_header">
          <div className="flex items-center gap-2">
            <Layers className="w-4.5 h-4.5 text-[#c0c1ff]" />
            <h3 className="font-semibold text-sm text-white tracking-tight">Deployment Timeline</h3>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#4edea3]" id="live_status_indicator">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span>Live Pipeline Status</span>
          </div>
        </div>

        {/* Grid for Nodes */}
        <div className="relative py-4 overflow-x-auto scrollbar-thin" id="timeline_container">
          {/* Timeline Connecting Line */}
          <div className="absolute top-[38px] left-[4%] right-[4%] h-[2px] bg-zinc-800 -z-10" id="timeline_backline">
            {/* Simulated Green Highlight fill line */}
            <div className="h-full bg-gradient-to-r from-emerald-500 to-indigo-500/80 w-[84%]" />
          </div>

          {/* Step Sequence Wrapper */}
          <div className="flex justify-between items-start min-w-[760px] px-2" id="pipeline_steps_row">
            {pipelineSteps.map((step) => {
              const isSelected = selectedTimelineStep === step.id;
              
              // Render based on status
              let stepBg = "bg-zinc-900 border-zinc-700 text-zinc-500";
              let nodeIcon = <Clock className="w-4 h-4" />;

              if (step.status === "completed") {
                stepBg = "bg-emerald-950/80 border-emerald-500 text-[#4edea3] hover:bg-emerald-900/30";
                nodeIcon = <Check className="w-4 h-4 text-[#4edea3]" />;
              } else if (step.status === "active") {
                stepBg = "bg-indigo-950 border-indigo-500 text-[#c0c1ff] ring-4 ring-indigo-500/20";
                nodeIcon = <Sparkles className="w-4 h-4 text-[#c0c1ff] animate-pulse" />;
              } else if (step.status === "pending") {
                stepBg = "bg-[#0d0d15] border-zinc-800 text-zinc-600";
                nodeIcon = <HelpCircle className="w-4 h-4 text-zinc-600" />;
              }

              return (
                <button
                  key={step.id}
                  onClick={() => {
                    setSelectedTimelineStep(step.id);
                    triggerToast(`Inspecting timeline stage: ${step.id}`);
                  }}
                  className="flex flex-col items-center text-center focus:outline-none group relative shrink-0"
                  style={{ width: "11%" }}
                  id={`timeline_node_${step.id.toLowerCase().replace(" ", "_")}`}
                >
                  {/* Step Round Node Button */}
                  <div className={`w-11 h-11 rounded-full flex items-center justify-center border-2 transition-all cursor-pointer ${stepBg} ${
                    isSelected ? "scale-110 shadow-lg shadow-indigo-500/10 border-white" : "hover:scale-105"
                  }`}>
                    {nodeIcon}
                  </div>

                  {/* Step Labels */}
                  <span className={`text-xs font-medium mt-3 transition-colors ${
                    isSelected ? "text-white font-semibold" : "text-zinc-400 group-hover:text-zinc-200"
                  }`}>
                    {step.label}
                  </span>

                  {/* Interactive Selection Ring */}
                  {isSelected && (
                    <motion.div
                      layoutId="timelineNodeActive"
                      className="absolute -bottom-2 w-1.5 h-1.5 bg-[#c0c1ff] rounded-full"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Contextual Box for Selected Timeline Node */}
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedTimelineStep}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="mt-6 bg-[#0d0d15] border border-[#27272a] rounded-lg p-4 font-mono text-xs flex flex-col md:flex-row md:items-center justify-between gap-4"
            id="timeline_context_panel"
          >
            <div className="flex items-start md:items-center gap-3">
              <Terminal className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5 md:mt-0" />
              <div>
                <span className="text-[#c0c1ff] font-bold">STAGE: {selectedTimelineStep.toUpperCase()}</span>
                <span className="mx-2 text-zinc-600">|</span>
                <span className="text-zinc-300">
                  {pipelineSteps.find(s => s.id === selectedTimelineStep)?.details}
                </span>
              </div>
            </div>
            {pipelineSteps.find(s => s.id === selectedTimelineStep)?.timestamp && (
              <div className="text-zinc-500 shrink-0 text-right">
                Processed at: <span className="text-zinc-400 font-semibold">{pipelineSteps.find(s => s.id === selectedTimelineStep)?.timestamp}</span>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* 5. Bottom Splitted Layout Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="bottom_layouts_container">
        
        {/* Left Card: Similar Historical Incidents (4 Cols) */}
        <div className="lg:col-span-4 bg-[#13131b] border border-[#27272a] rounded-lg p-5 flex flex-col justify-between" id="historical_incidents_panel">
          <div>
            <div className="flex items-center gap-2 mb-4 border-b border-[#27272a] pb-3">
              <Clock className="w-4.5 h-4.5 text-rose-400" />
              <h3 className="font-semibold text-sm text-white tracking-tight">Similar Historical Incidents</h3>
            </div>

            <div className="space-y-3" id="incidents_accordion">
              {historicalIncidents.map((inc) => {
                const isExpanded = expandedIncident === inc.id;
                return (
                  <div
                    key={inc.id}
                    className="border border-[#27272a] rounded-lg bg-[#0d0d15] overflow-hidden transition-all"
                    id={`incident_row_${inc.id}`}
                  >
                    {/* Summary trigger row */}
                    <button
                      onClick={() => setExpandedIncident(isExpanded ? null : inc.id)}
                      className="w-full flex items-start justify-between p-3.5 hover:bg-zinc-900/60 transition-colors text-left"
                      id={`incident_toggle_btn_${inc.id}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          {inc.type === "error" ? (
                            <div className="p-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                              <AlertTriangle className="w-3.5 h-3.5" />
                            </div>
                          ) : (
                            <div className="p-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <Zap className="w-3.5 h-3.5" />
                            </div>
                          )}
                        </div>
                        <div>
                          <p className="text-xs font-bold text-white leading-snug">{inc.title}</p>
                          <p className="text-[10px] font-mono text-zinc-500 mt-1">
                            {inc.date} • {inc.duration}
                          </p>
                        </div>
                      </div>
                      <div className="text-zinc-500 hover:text-white pt-1">
                        {isExpanded ? <ChevronUp className="w-4.5 h-4.5" /> : <ChevronDown className="w-4.5 h-4.5" />}
                      </div>
                    </button>

                    {/* Collapsed view panel containing details */}
                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="border-t border-[#1f1f27] bg-[#13131b]/50 text-xs font-mono"
                        >
                          <div className="p-4 space-y-3 text-zinc-400">
                            <div>
                              <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider block mb-1">IMPACT SCORE:</span>
                              <p className="text-zinc-300">{inc.impactScore}</p>
                            </div>
                            <div>
                              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">ROOT CAUSE:</span>
                              <p className="text-zinc-300 leading-relaxed">{inc.rootCause}</p>
                            </div>
                            <div>
                              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">MITIGATION LOG:</span>
                              <p className="text-zinc-300 leading-relaxed">{inc.details}</p>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Informative system message footer inside left col */}
          <div className="pt-4 mt-4 border-t border-[#27272a] text-[10px] font-mono text-zinc-500" id="incidents_footer">
            Note: Risk modeling correlates active deployment structures with incidents over a 12-month trailing index.
          </div>
        </div>

        {/* Right Card: Explainability Section (8 Cols) */}
        <div className="lg:col-span-8 bg-[#13131b] border border-[#27272a] rounded-lg p-5" id="explainability_panel">
          <div className="flex items-center gap-2 mb-5 border-b border-[#27272a] pb-3">
            <Sparkles className="w-4.5 h-4.5 text-[#c0c1ff]" />
            <h3 className="font-semibold text-sm text-white tracking-tight">Explainability Section</h3>
          </div>

          {/* OVERALL AI SUMMARY */}
          <div className="bg-[#1b1b23] border border-[#27272a] rounded-lg p-5 mb-5 relative overflow-hidden" id="ai_summary_box">
            {/* Purple decorative background glow */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#c0c1ff]/5 rounded-full blur-2xl pointer-events-none" />
            
            <div className="flex items-center gap-2 mb-2.5">
              <Sparkles className="w-3.5 h-3.5 text-[#c0c1ff]" />
              <span className="text-[10px] font-mono font-bold tracking-wider text-indigo-300 uppercase">OVERALL AI SUMMARY</span>
            </div>
            
            <p className="text-xs text-zinc-300 leading-relaxed font-sans" id="summary_paragraph">
              The deployment of <span className="font-mono text-white font-semibold">dep-8f2a</span> is classified as <span className="text-[#4edea3] font-bold font-mono">SAFE</span> with a total risk score of <span className="text-[#4edea3] font-bold font-mono">12/100</span>. Our agents analyzed the PR delta and infrastructure changes, finding no direct correlation with past high-severity incidents. The codebase exhibits high test coverage (<span className="text-white font-semibold">94%</span>) and the static analysis engine reported zero high-risk security patterns. We recommend proceeding with the automated canary rollout as planned.
            </p>
          </div>

          {/* Insights and Recommendations Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5" id="insights_rec_grid">
            
            {/* KEY RISK INSIGHTS (Left) */}
            <div className="space-y-3.5" id="key_risk_insights_column">
              <h4 className="text-[11px] font-mono font-bold tracking-wider text-zinc-500 uppercase">KEY RISK INSIGHTS</h4>
              <ul className="space-y-3" id="insights_list">
                {keyRiskInsights.map((insight, idx) => (
                  <li key={idx} className="flex items-start gap-3" id={`insight_item_${idx}`}>
                    <div className="p-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 shrink-0 mt-0.5">
                      <Check className="w-3 h-3" />
                    </div>
                    <span className="text-xs text-zinc-300 leading-relaxed font-sans">{insight}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* RECOMMENDATIONS (Right) */}
            <div className="space-y-3.5" id="recommendations_column">
              <h4 className="text-[11px] font-mono font-bold tracking-wider text-zinc-500 uppercase">RECOMMENDATIONS</h4>
              
              {/* Styled Container */}
              <div className="bg-[#0d0d15] border border-[#27272a] rounded-lg p-4 flex flex-col justify-between h-[120px]" id="best_practices_card">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-zinc-400 text-xs font-mono font-semibold" id="best_practices_label">
                    <Settings className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Best Practices</span>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed font-sans">
                    Monitor the <code className="text-amber-300 font-mono text-[11px]">auth-service-v3</code> metrics for the first 10 minutes of the canary phase.
                  </p>
                </div>

                <button 
                  onClick={() => setShowAlertModal(true)}
                  className="w-full mt-3 py-1.5 rounded bg-[#13131b] border border-[#27272a] text-xs font-medium text-white hover:border-[#c0c1ff] hover:text-[#c0c1ff] active:scale-[0.99] transition-all"
                  id="configure_alerting_btn"
                >
                  Configure Alerting
                </button>
              </div>
            </div>

          </div>

        </div>

      </div>

      {/* 6. Alert Rule Configuration Modal Overlay */}
      <AnimatePresence>
        {showAlertModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" id="alert_modal_overlay">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#13131b] border border-[#27272a] w-full max-w-md rounded-lg shadow-2xl p-6"
              id="alert_modal_card"
            >
              {/* Modal Title & Close */}
              <div className="flex items-center justify-between border-b border-[#27272a] pb-3.5 mb-4" id="modal_header">
                <div className="flex items-center gap-2">
                  <Sliders className="w-4.5 h-4.5 text-[#c0c1ff]" />
                  <h3 className="font-semibold text-sm text-white">Configure Alert Rule</h3>
                </div>
                <button
                  onClick={() => setShowAlertModal(false)}
                  className="text-zinc-500 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Form Input fields */}
              <form onSubmit={handleSaveAlert} className="space-y-4 font-sans text-xs">
                {/* Metric target */}
                <div className="space-y-1.5">
                  <label className="text-zinc-400 font-mono font-semibold uppercase tracking-wider block text-[10px]">TARGET METRIC</label>
                  <input
                    type="text"
                    required
                    value={alertForm.metric}
                    onChange={(e) => setAlertForm({ ...alertForm, metric: e.target.value })}
                    className="w-full bg-[#0d0d15] border border-[#27272a] rounded p-2.5 text-xs text-[#e4e1ed] placeholder-zinc-500 focus:outline-none focus:border-[#c0c1ff] font-mono"
                  />
                </div>

                {/* Threshold limits */}
                <div className="space-y-1.5">
                  <label className="text-zinc-400 font-mono font-semibold uppercase tracking-wider block text-[10px]">LATENCY THRESHOLD (MS)</label>
                  <input
                    type="number"
                    required
                    value={alertForm.threshold}
                    onChange={(e) => setAlertForm({ ...alertForm, threshold: e.target.value })}
                    className="w-full bg-[#0d0d15] border border-[#27272a] rounded p-2.5 text-xs text-[#e4e1ed] placeholder-zinc-500 focus:outline-none focus:border-[#c0c1ff] font-mono"
                  />
                </div>

                {/* Alert Destination */}
                <div className="space-y-1.5">
                  <label className="text-zinc-400 font-mono font-semibold uppercase tracking-wider block text-[10px]">NOTIFICATION ROUTE</label>
                  <select
                    value={alertForm.channel}
                    onChange={(e) => setAlertForm({ ...alertForm, channel: e.target.value })}
                    className="w-full bg-[#0d0d15] border border-[#27272a] rounded p-2.5 text-xs text-[#e4e1ed] focus:outline-none focus:border-[#c0c1ff] font-mono"
                  >
                    <option value="Slack (#alerts-devsecops)">Slack (#alerts-devsecops)</option>
                    <option value="PagerDuty (On-Call Engineer)">PagerDuty (On-Call Engineer)</option>
                    <option value="Email Distribution Group">Email Distribution Group</option>
                  </select>
                </div>

                {/* Alert Notes */}
                <div className="space-y-1.5">
                  <label className="text-zinc-400 font-mono font-semibold uppercase tracking-wider block text-[10px]">RECOVERY ACTION NOTES</label>
                  <textarea
                    rows={3}
                    value={alertForm.notes}
                    onChange={(e) => setAlertForm({ ...alertForm, notes: e.target.value })}
                    className="w-full bg-[#0d0d15] border border-[#27272a] rounded p-2.5 text-xs text-[#e4e1ed] placeholder-zinc-500 focus:outline-none focus:border-[#c0c1ff] leading-relaxed resize-none font-sans"
                  />
                </div>

                {/* Footer Controls */}
                <div className="flex items-center justify-end gap-3.5 pt-3.5 border-t border-[#27272a] mt-6" id="modal_footer">
                  <button
                    type="button"
                    onClick={() => setShowAlertModal(false)}
                    className="px-4 py-2 rounded bg-zinc-900 border border-[#27272a] text-zinc-400 hover:text-white transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSavingAlert}
                    className="px-4 py-2 rounded bg-indigo-600 text-white font-medium hover:bg-indigo-500 transition-all flex items-center gap-1.5 disabled:opacity-60"
                  >
                    {isSavingAlert ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Deploying Rule...
                      </>
                    ) : (
                      "Save Alert Rule"
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
