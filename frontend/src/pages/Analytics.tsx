import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import type { DeploymentEvent } from '../api/client';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ChevronRight,
  X,
  Plus,
  Loader2,
  Calendar,
  SlidersHorizontal,
  Download,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Ban,
  Eye,
  Info,
  Shield,
  BarChart3,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area
} from 'recharts';
import './Analytics.css';
import {
  getAnalyticsSummary,
  getAnalyticsVolume,
  getAnalyticsDecisions,
  getAnalyticsBlocks,
  exportAnalytics,
} from '../api/analytics';

import type {
  AnalyticsSummaryResponse,
  AnalyticsVolumeResponse,
  AnalyticsDecisionsResponse,
  AnalyticsBlocksResponse,
} from '../api/analytics';

import type { AnalyticsBlockRecord } from '../api/analytics';

export const Analytics: React.FC = () => {
  const [deployments, setDeployments] = useState<DeploymentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [decisionSummary, setDecisionSummary] = useState<AnalyticsDecisionsResponse | null>(null);
  const [volumeSummary, setVolumeSummary] = useState<AnalyticsVolumeResponse | null>(null);
  const [blocksSummary, setBlocksSummary] = useState<AnalyticsBlocksResponse | null>(null);

  // Stitch dynamic states
  const [timeRange, setTimeRange] = useState<'7d' | '14d' | '30d' | '90d'>('30d');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFilterDropdownOpen, setIsFilterDropdownOpen] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'>('ALL');
  
  // Modals & Triggers
  const [selectedBlock, setSelectedBlock] = useState<AnalyticsBlockRecord | null>(null);
  const [showNewDeploymentModal, setShowNewDeploymentModal] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [csvToast, setCsvToast] = useState<string | null>(null);

  // Form state for custom simulation
  const [newRepo, setNewRepo] = useState('myorg/payments-api');
  const [newBranch, setNewBranch] = useState('main');
  const [newThreatType, setNewThreatType] = useState('Hardcoded Stripe API Secret');
  const [newRiskScore, setNewRiskScore] = useState(84);

  const fetchDeployments = async () => {
    try {
      const data = await api.getDeployments();
      setDeployments(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  fetchDeployments(); // keeps sparkline/histogram working
}, []);

useEffect(() => {
  fetchAnalytics();
}, [timeRange, severityFilter, searchQuery]);

  const fetchAnalytics = async () => {
  try {
    const [summaryData, volumeData, decisionData, blocksData] =
      await Promise.all([
        getAnalyticsSummary({ range: timeRange }),
        getAnalyticsVolume({ range: timeRange }),
        getAnalyticsDecisions({ range: timeRange }),
        getAnalyticsBlocks({
          range: timeRange,
          severity:
            severityFilter === "ALL" ? undefined : severityFilter,
          search: searchQuery || undefined,
        }),
      ]);

    setSummary(summaryData);
    setVolumeSummary(volumeData);
    setDecisionSummary(decisionData);
    setBlocksSummary(blocksData);
  } catch (err) {
    console.error("Analytics fetch failed", err);
  }
};

  // Filter deployments by selected timeRange
  const timeFilteredDeployments = useMemo(() => {
    const now = Date.now();
    let days = 30;
    if (timeRange === '7d') days = 7;
    else if (timeRange === '14d') days = 14;
    else if (timeRange === '90d') days = 90;
    
    const limit = now - (days * 24 * 3600 * 1000);
    return deployments.filter(d => new Date(d.generated_at || 0).getTime() >= limit);
  }, [deployments, timeRange]);

  // Compute key metric cards
const totalAnalyzed = summary?.totalAnalyzed ?? 0;

const avgRiskScore = summary?.avgRiskScore ?? 0;

const avgConfidence =
  summary ? `${summary.avgConfidence}%` : "0.0%";

const totalBlocked = summary?.totalBlocked ?? 0;

  // Pie chart counts
  const safeCount = decisionSummary?.distribution.SAFE ?? 0;
const reviewCount = decisionSummary?.distribution.REVIEW ?? 0;
const blockCount = decisionSummary?.distribution.BLOCK ?? 0;

const pieData = useMemo(() => {
  return [
    { name: "SAFE", value: safeCount, color: "#4edea3" },
    { name: "REVIEW", value: reviewCount, color: "#ffb95f" },
    { name: "BLOCK", value: blockCount, color: "#ffb4ab" },
  ];
}, [safeCount, reviewCount, blockCount]);

  // Safe rate calculations
  const safeRate = useMemo(() => {
    const total = safeCount + reviewCount + blockCount;
    return total > 0 ? Math.round((safeCount / total) * 100) + "%" : "75%";
  }, [safeCount, reviewCount, blockCount]);

  // Volume Bar Chart Data
 const volumeData = useMemo(() => {
  if (!volumeSummary) return [];

  return volumeSummary.data.map((item) => ({
    date: item.date,
    Safe: item.safe,
    Blocked: item.blocked,
  }));
}, [volumeSummary]);
    
    // Sort and group actual time-filtered deployments
    

  // Sparkline confidence trend area data
  const confidenceTrendData = useMemo(() => {
    const list = [...timeFilteredDeployments]
      .sort((a, b) => new Date(a.generated_at || 0).getTime() - new Date(b.generated_at || 0).getTime())
      .map(d => ({
        name: d.generated_at ? new Date(d.generated_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}) : '',
        value: Math.round((d.overall_confidence || 0.9) * 100)
      }));
    if (list.length > 0) return list;

    return [
      { name: 'Oct 1', value: 93.5 },
      { name: 'Oct 5', value: 93.9 },
      { name: 'Oct 10', value: 93.8 },
      { name: 'Oct 15', value: 94.1 },
      { name: 'Oct 20', value: 94.3 },
      { name: 'Oct 25', value: 94.0 },
      { name: 'Oct 30', value: 94.2 }
    ];
  }, [timeFilteredDeployments]);

  // Risk Score Distribution Histogram bins
  const riskHistogram = useMemo(() => {
    const bins = [0, 0, 0, 0, 0]; // 0-20, 21-40, 41-60, 61-80, 81-100
    timeFilteredDeployments.forEach(d => {
      const score = d.overall_score || 0;
      if (score <= 20) bins[0]++;
      else if (score <= 40) bins[1]++;
      else if (score <= 60) bins[2]++;
      else if (score <= 80) bins[3]++;
      else bins[4]++;
    });
    
    const max = Math.max(...bins);
    const defaultHeights = ['12%', '32%', '82%', '62%', '28%'];

    return bins.map((val, idx) => {
      const percent = max > 0 ? `${Math.min(100, Math.round((val / max) * 90) + 10)}%` : defaultHeights[idx];
      const ranges = ['0-20', '21-40', '41-60', '61-80', '81-100'];
      return {
        range: ranges[idx],
        height: percent,
        count: val
      };
    });
  }, [timeFilteredDeployments]);

  // Agent averages calculations
  const agentAverages = useMemo(() => {
    let codeSum = 0, infraSum = 0, incidentSum = 0;
    let codeCount = 0, infraCount = 0, incidentCount = 0;
    
    timeFilteredDeployments.forEach(d => {
      if (d.agents) {
        if (d.agents['code-risk'] !== undefined) {
          codeSum += d.agents['code-risk'].score || 0;
          codeCount++;
        }
        if (d.agents['infra-risk'] !== undefined) {
          infraSum += d.agents['infra-risk'].score || 0;
          infraCount++;
        }
        if (d.agents['incident-history'] !== undefined) {
          incidentSum += d.agents['incident-history'].score || 0;
          incidentCount++;
        }
      }
    });

    return {
      code: codeCount > 0 ? Math.round(codeSum / codeCount) : 88,
      infra: infraCount > 0 ? Math.round(infraSum / infraCount) : 72,
      incident: incidentCount > 0 ? Math.round(incidentSum / incidentCount) : 92
    };
  }, [timeFilteredDeployments]);

  // Filter high risk blocks for the recent table
  const filteredBlocks = useMemo(() => {
  return blocksSummary?.items ?? [];
}, [blocksSummary]);

  // Toast notifier
  const triggerToast = (msg: string) => {
    setCsvToast(msg);
    setTimeout(() => setCsvToast(null), 4000);
  };
const handleExportCSV = async () => {
  try {
    const blob = await exportAnalytics({
      range: timeRange,
      format: "csv",
    });

    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `deployguard_security_analytics_${timeRange}.csv`;

    document.body.appendChild(link);
    link.click();

    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    triggerToast(
      `Successfully downloaded analytics export for ${timeRange}!`
    );
  } catch (err) {
    console.error(err);
    triggerToast("Failed to export analytics.");
  }
};

  const handleStartScanSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsScanning(true);
    setScanStep(0);

    const steps = [
      "Initializing DeployGuard pipeline hook...",
      "Cloning branch and resolving infrastructure manifests...",
      "Running Code Risk Agent scanner...",
      "Running Infrastructure Configuration validator...",
      "Executing Incident History validation matching...",
      "DeployGuard threat analysis report calculated successfully!"
    ];

    const timer = setInterval(() => {
      setScanStep(prev => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(timer);
          return prev;
        }
      });
    }, 1100);

    try {
      // Trigger real Kafka backend pipeline check
      await api.triggerDeployment(
        newRepo,
        `Simulated: ${newThreatType}`,
        `DeployGuard scan simulation. Scanned issue: ${newThreatType}. Score set: ${newRiskScore}.`,
        `fix: resolve ${newThreatType.toLowerCase()} on ${newBranch}`
      );
      
      // Wait for simulator logs transition
      await new Promise(resolve => setTimeout(resolve, 6600));
      
      // Reload deployments
      await fetchDeployments();
      
      setIsScanning(false);
      setShowNewDeploymentModal(false);
      triggerToast(`Successfully simulated scan pipeline for ${newRepo}/${newBranch}!`);
    } catch (err) {
      console.error(err);
      clearInterval(timer);
      setIsScanning(false);
      setShowNewDeploymentModal(false);
    }
  };

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    return date.toLocaleTimeString() + ' ' + date.toLocaleDateString(undefined, {month: 'numeric', day: 'numeric'});
  };

  return (
    <div className="analytics-container fade-in">
      {/* Toast Overlay */}
      {csvToast && (
        <div className="toast-notification font-mono" id="csv_toast_notification">
          <CheckCircle2 className="toast-icon" />
          <span>{csvToast}</span>
        </div>
      )}

      {/* Title & Filter Bar */}
      <div className="analytics-title-bar border-bottom">
        <div>
          <h2>Security Analytics</h2>
          <p className="subtitle">Holistic view of deployment security posture and agent performance.</p>
        </div>
        
        <div className="controls-group">
          {/* Search Box */}
          <div className="search-box-wrapper">
            <Search className="search-icon" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input font-mono"
              placeholder="Search repository..."
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="clear-search-btn">
                <X className="clear-icon" />
              </button>
            )}
          </div>

          {/* Range Select */}
          <div className="select-wrapper font-mono">
            <Calendar className="select-calendar-icon" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="range-select"
            >
              <option value="7d">Last 7 Days</option>
              <option value="14d">Last 14 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
            </select>
            <span className="dropdown-caret font-mono">▼</span>
          </div>

          {/* Advanced Filter Button */}
          <div className="relative-container">
            <button
              onClick={() => setIsFilterDropdownOpen(!isFilterDropdownOpen)}
              className={`filter-toggle-btn ${isFilterDropdownOpen ? 'active' : ''}`}
            >
              <SlidersHorizontal className="filter-sliders-icon" />
              <span>Filters</span>
              {severityFilter !== 'ALL' && (
                <span className="badge-severity font-mono">
                  {severityFilter}
                </span>
              )}
            </button>

            {isFilterDropdownOpen && (
              <>
                <div className="dropdown-backdrop" onClick={() => setIsFilterDropdownOpen(false)} />
                <div className="filter-dropdown-menu">
                  <h5>Filter Severity</h5>
                  <div className="menu-choices">
                    {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map((sev) => (
                      <button
                        key={sev}
                        onClick={() => {
                          setSeverityFilter(sev);
                          setIsFilterDropdownOpen(false);
                        }}
                        className={`choice-btn ${severityFilter === sev ? 'selected font-bold' : ''}`}
                      >
                        <span>{sev === 'ALL' ? 'All Risks' : sev}</span>
                        {severityFilter === sev && <span className="selection-dot" />}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Action buttons */}
          <button onClick={handleExportCSV} className="action-outline-btn font-mono">
            <Download className="btn-icon" />
            Export CSV
          </button>

          <button onClick={() => setShowNewDeploymentModal(true)} className="action-solid-btn font-mono">
            <Plus className="btn-icon stroke-thick" />
            Simulate Scan
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state font-mono" style={{ padding: '80px 0', gap: '14px' }}>
          <div style={{ width: '28px', height: '28px', border: '2px solid var(--panel-border)', borderTopColor: 'var(--accent-cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Loading metrics database...</span>
        </div>
      ) : (
        <div className="analytics-body-layout">
          
          {/* 4 Metric overview cards */}
          <div className="metrics-summary-grid">
            {/* CARD 1: Analyzed */}
            <div className="metric-overview-card border-primary">
              <div className="card-header">
                <span className="card-title font-mono">Total Analyzed</span>
                <div className="icon-wrap bg-primary-alpha">
                  <BarChart className="icon text-primary" />
                </div>
              </div>
              <h3 className="card-value font-mono">{totalAnalyzed}</h3>
              <div className="card-trend-row font-mono">
                <span className="trend-text text-green">
                  <TrendingUp className="trend-icon" /> +12%
                </span>
                <span className="trend-span">vs last month</span>
              </div>
              <div className="bottom-highlight bg-primary" />
            </div>

            {/* CARD 2: Score */}
            <div className="metric-overview-card border-tertiary">
              <div className="card-header">
                <span className="card-title font-mono">Avg. Risk Score</span>
                <div className="icon-wrap bg-tertiary-alpha">
                  <AlertTriangle className="icon text-tertiary" />
                </div>
              </div>
              <h3 className="card-value font-mono">{avgRiskScore}</h3>
              <div className="card-trend-row font-mono">
                <span className="trend-text text-green">
                  <TrendingDown className="trend-icon" /> -4%
                </span>
                <span className="trend-span">vs last month</span>
              </div>
              <div className="bottom-highlight bg-tertiary" />
            </div>

            {/* CARD 3: Confidence */}
            <div className="metric-overview-card border-secondary">
              <div className="card-header">
                <span className="card-title font-mono">Avg. Confidence</span>
                <div className="icon-wrap bg-secondary-alpha">
                  <ShieldCheck className="icon text-secondary" />
                </div>
              </div>
              <h3 className="card-value font-mono">{avgConfidence}</h3>
              <div className="card-trend-row font-mono">
                <span className="trend-text text-green">
                  <TrendingUp className="trend-icon" /> +0.8%
                </span>
                <span className="trend-span">vs last month</span>
              </div>
              <div className="bottom-highlight bg-secondary" />
            </div>

            {/* CARD 4: Blocked */}
            <div className="metric-overview-card border-error">
              <div className="card-header">
                <span className="card-title font-mono">Total Blocked</span>
                <div className="icon-wrap bg-error-alpha">
                  <Ban className="icon text-error" />
                </div>
              </div>
              <h3 className="card-value font-mono">{totalBlocked}</h3>
              <div className="card-trend-row font-mono">
                <span className="trend-text text-error">
                  <TrendingUp className="trend-icon" /> +22%
                </span>
                <span className="trend-span">vs last month</span>
              </div>
              <div className="bottom-highlight bg-error" />
            </div>
          </div>

          {/* Row 1: Charts Panel */}
          <div className="charts-row-grid">
            {/* Left Chart: double bar */}
            <div className="chart-panel-card double-width">
              <div className="panel-header">
                <div>
                  <h4>Deployment Volume &amp; Decisions</h4>
                  <p className="panel-desc">Visualizing blocked vs clean pipelines over time</p>
                </div>
                <div className="chart-legends font-mono">
                  <div className="legend-item">
                    <span className="legend-dot bg-secondary" />
                    <span>Safe</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot bg-error" />
                    <span>Blocked</span>
                  </div>
                </div>
              </div>

              <div className="chart-container-wrapper">
                {volumeData.length === 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '10px', color: 'var(--text-muted)' }}>
                    <BarChart3 size={28} style={{ opacity: 0.3 }} />
                    <span className="font-mono" style={{ fontSize: '12px' }}>No deployment volume data for this period.</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Run a simulation to generate data.</span>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={volumeData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }} barGap={6}>
                      <XAxis dataKey="date" stroke="#908fa0" fontSize={11} tickLine={false} axisLine={false} fontFamily="JetBrains Mono" />
                      <YAxis stroke="#908fa0" fontSize={11} tickLine={false} axisLine={false} fontFamily="JetBrains Mono" />
                      <Tooltip
                        cursor={{ fill: 'rgba(192,193,255,0.03)' }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="chart-tooltip font-mono" style={{ background: '#1b1b23', border: '1px solid #464554', borderRadius: '6px', padding: '10px 14px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}>
                                <p style={{ fontSize: '11px', color: '#908fa0', marginBottom: '6px', fontWeight: 600 }}>{payload[0].payload.date}</p>
                                <p style={{ fontSize: '12px', color: '#4edea3', margin: '3px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#4edea3', display: 'inline-block' }} />
                                  Safe: <strong>{payload[0].value}</strong>
                                </p>
                                <p style={{ fontSize: '12px', color: '#ffb4ab', margin: '3px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#ffb4ab', display: 'inline-block' }} />
                                  Blocked: <strong>{payload[1]?.value}</strong>
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Bar dataKey="Safe" fill="#4edea3" radius={[4, 4, 0, 0]} maxBarSize={30} />
                      <Bar dataKey="Blocked" fill="#ffb4ab" radius={[4, 4, 0, 0]} maxBarSize={30} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            {/* Right Chart: Donut */}
            <div className="chart-panel-card">
              <div>
                <h4>Decision Distribution</h4>
                <p className="panel-desc">Breakdown of classification results</p>
              </div>

              <div className="pie-chart-relative-container">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={75} paddingAngle={4} dataKey="value">
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                
                {/* Center Safe Rate Overlay */}
                <div className="donut-center-overlay">
                  <span className="overlay-percentage font-mono">{safeRate}</span>
                  <span className="overlay-label font-mono">Safe Rate</span>
                </div>
              </div>

              {/* Legends list */}
              <div className="pie-legends-list border-top">
                {pieData.map((entry, idx) => (
                  <div key={idx} className="pie-legend-row font-mono">
                    <div className="legend-label-group">
                      <span className="legend-box" style={{ backgroundColor: entry.color }} />
                      <span className="legend-name">{entry.name}</span>
                    </div>
                    <span className="legend-count">{entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Row 2: Histogram and Agent Lists */}
          <div className="histogram-agents-row">
            {/* Risk score histogram */}
            <div className="histogram-card">
              <div>
                <h4>Risk Score Distribution</h4>
                <p className="panel-desc">Cluster density across security risk categories</p>
              </div>

              {/* Custom CSS column bars */}
              <div className="histogram-bars-wrapper">
                {riskHistogram.map((item, idx) => (
                  <div
                    key={idx}
                    className={`histogram-bar-column ${idx === 4 ? 'bg-error' : idx >= 3 ? 'bg-tertiary' : 'bg-secondary'}`}
                    style={{ height: item.height }}
                  >
                    <div className="hover-bar-tooltip font-mono">Vol: {item.count}</div>
                  </div>
                ))}
              </div>

              <div className="histogram-labels-axis font-mono border-top">
                <span>0-20</span>
                <span>21-40</span>
                <span>41-60</span>
                <span>61-80</span>
                <span>81-100</span>
              </div>

              <div className="histogram-quote-footer border-primary-alpha">
                <p className="quote-text font-sans">
                  "Majority of deployments cluster in the low risk range, indicating stable infrastructure patterns."
                </p>
              </div>
            </div>

            {/* Agent performance breakdown */}
            <div className="agent-progress-card">
              <div>
                <h4>Agent Performance Metrics</h4>
                <p className="panel-desc">Real-time health of pre-deployment inspection bots</p>
              </div>

              <div className="progress-bars-stack">
                {/* Code Risk */}
                <div className="stack-item">
                  <div className="item-labels">
                    <span className="item-title font-sans">
                      <span className="dot bg-secondary" />
                      Code Risk Agent
                    </span>
                    <span className="item-score font-mono">{agentAverages.code}.0 Score</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill bg-secondary" style={{ width: `${agentAverages.code}%` }} />
                  </div>
                </div>

                {/* Infra Risk */}
                <div className="stack-item">
                  <div className="item-labels">
                    <span className="item-title font-sans">
                      <span className="dot bg-tertiary" />
                      Infrastructure Agent
                    </span>
                    <span className="item-score font-mono">{agentAverages.infra}.0 Score</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill bg-tertiary" style={{ width: `${agentAverages.infra}%` }} />
                  </div>
                </div>

                {/* Incident History */}
                <div className="stack-item">
                  <div className="item-labels">
                    <span className="item-title font-sans">
                      <span className="dot bg-primary" />
                      Incident History Agent
                    </span>
                    <span className="item-score font-mono">{agentAverages.incident}.0 Score</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill bg-primary" style={{ width: `${agentAverages.incident}%` }} />
                  </div>
                </div>
              </div>

              {/* Bot stats footer row */}
              <div className="bot-stats-grid border-top font-mono">
                <div className="stat-node">
                  <span className="node-title">Latency</span>
                  <span className="node-value">1.2s</span>
                </div>
                <div className="stat-node">
                  <span className="node-title">Accuracy</span>
                  <span className="node-value">96%</span>
                </div>
                <div className="stat-node">
                  <span className="node-title">Uptime</span>
                  <span className="node-value">99.9%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Row 3: Confidence Sparkline & Lists */}
          <div className="sparkline-lists-row">
            {/* Sparkline area chart */}
            <div className="sparkline-card">
              <div>
                <h4>Confidence Trend</h4>
                <p className="panel-desc">Model stability over {timeRange === '7d' ? '7 days' : timeRange === '14d' ? '14 days' : timeRange === '90d' ? '90 days' : '30 days'}</p>
              </div>

              <div className="sparkline-container-wrapper">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={confidenceTrendData} margin={{ top: 5, right: 5, left: -40, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#c0c1ff" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#c0c1ff" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="sparkline-tooltip font-mono">
                              {payload[0].value}%
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Area type="monotone" dataKey="value" stroke="#c0c1ff" strokeWidth={2} fillOpacity={1} fill="url(#colorConfidence)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="sparkline-footer border-top font-mono">
                <span className="avg-confidence">Avg: {avgConfidence}</span>
                <div className="improvement-badge text-green">
                  <TrendingUp className="trend-icon" />
                  <span>+2.1% improvement</span>
                </div>
              </div>
            </div>

            {/* Common Deployment Risks */}
            <div className="list-bars-card">
              <div>
                <h4>Common Deployment Risks</h4>
                <p className="panel-desc">Highest frequency threat vectors classified</p>
              </div>

              <div className="frequency-bars-stack">
                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">IAM OVER-PROVISIONING</span>
                    <span className="freq-count">342</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-error" style={{ width: '85%' }} />
                  </div>
                </div>

                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">SECRET LEAKAGE</span>
                    <span className="freq-count">215</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-error" style={{ width: '65%' }} />
                  </div>
                </div>

                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">UNENCRYPTED S3</span>
                    <span className="freq-count">188</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-error" style={{ width: '55%' }} />
                  </div>
                </div>

                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">PUBLIC SSH KEYS</span>
                    <span className="freq-count">104</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-error" style={{ width: '30%' }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Top Recommendations */}
            <div className="list-bars-card">
              <div>
                <h4>Top Recommendations</h4>
                <p className="panel-desc">Urgent operational task volume identified</p>
              </div>

              <div className="frequency-bars-stack">
                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">UPDATE DEPENDENCIES</span>
                    <span className="freq-count">1,402</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-primary" style={{ width: '90%' }} />
                  </div>
                </div>

                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">ROTATE API KEYS</span>
                    <span className="freq-count">894</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-primary" style={{ width: '70%' }} />
                  </div>
                </div>

                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">ENFORCE MFA</span>
                    <span className="freq-count">652</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-primary" style={{ width: '50%' }} />
                  </div>
                </div>

                <div className="freq-item">
                  <div className="freq-labels font-mono">
                    <span className="truncate">AUDIT VPC PEERING</span>
                    <span className="freq-count">412</span>
                  </div>
                  <div className="freq-track">
                    <div className="freq-fill bg-primary" style={{ width: '35%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Row 4: Recent High-Risk Blocks Table */}
          <div className="blocks-table-panel-card">
            <div className="panel-header-row border-bottom">
              <div>
                <h4>Recent High-Risk Blocks</h4>
                <p className="panel-desc">Interventions triggered by automated safety guardrails</p>
              </div>
              <div className="header-filters-row font-mono">
                <button
                  onClick={() => setSeverityFilter('CRITICAL')}
                  className="filter-pill border-error"
                >
                  View High Risk Only
                </button>
                {severityFilter !== 'ALL' && (
                  <button onClick={() => setSeverityFilter('ALL')} className="clear-pill font-sans">
                    Clear Filter
                  </button>
                )}
              </div>
            </div>

            <div className="table-responsive-wrapper">
              <table className="blocks-table">
                <thead className="font-mono border-bottom">
                  <tr>
                    <th>Time</th>
                    <th>Repository</th>
                    <th>Risk Score</th>
                    <th>Primary Threat</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="font-sans">
                  {filteredBlocks.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="empty-row font-mono">
                        No recent blocked logs matching the current criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredBlocks.map((block) => (
                      <tr
                        key={block.correlation_id}
                        className="table-row"
                        onClick={() => setSelectedBlock(block)}
                      >
                        <td className="time-cell font-mono">{formatDate(block.time)}</td>
                        <td className="repo-cell font-mono">{block.repository}</td>
                        <td className="score-cell">
                          <span className="risk-badge font-mono border-error">
                            <span className="dot bg-error" />
                            {block.risk_score}/100
                          </span>
                        </td>
                        <td className="threat-cell">{block.primary_threat || "High-Risk Deployment Blocked"}</td>
                        <td className="action-cell text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => setSelectedBlock(block)}
                            className="inspect-btn font-mono"
                            title="Inspect Block Log"
                          >
                            <Eye className="inspect-icon" />
                            <span>Inspect</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            
            <div className="table-footer border-top font-mono">
              <span>Showing {filteredBlocks.length} threat records</span>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSeverityFilter('ALL');
                }}
                className="reset-view-btn"
              >
                Reset Table View
              </button>
            </div>
          </div>

          {/* Footer */}
          <footer className="footer-bar border-top font-mono">
            <p>© 2026 DeployGuard Security Inc. All rights reserved.</p>
            <div className="footer-links">
              <a href="#">Documentation</a>
              <a href="#">Status</a>
              <a href="#">API</a>
            </div>
          </footer>
        </div>
      )}

      {/* MODAL 1: Threat Inspection Details Overlay */}
      {selectedBlock && (
        <div className="modal-overlay">
          <div className="modal-backdrop" onClick={() => setSelectedBlock(null)} />
          
          <div className="modal-card">
            {/* Header */}
            <div className="modal-header border-bottom">
              <div>
                <span className="modal-badge font-mono border-error">
                  DeployGuard Threat Intervention
                </span>
                <h3 className="modal-title font-sans">
                  {selectedBlock.primary_threat || "High-Risk Deployment Blocked"}
                </h3>
              </div>
              <button onClick={() => setSelectedBlock(null)} className="modal-close-x-btn">
                <X className="close-icon" />
              </button>
            </div>

            {/* Scope Metadata */}
            <div className="modal-meta-grid font-mono border-outline-variant">
              <div className="meta-box">
                <p className="meta-lbl">Risk Level</p>
                <p className="meta-val text-error font-bold">{selectedBlock.risk_score}/100</p>
              </div>
              <div className="meta-box">
                <p className="meta-lbl">Repository</p>
                <p className="meta-val font-bold truncate">{selectedBlock.repository}</p>
              </div>
              <div className="meta-box">
                <p className="meta-lbl">Timestamp</p>
                <p className="meta-val font-bold">{formatDate(selectedBlock.time)}</p>
              </div>
            </div>

            {/* Threat description */}
            <div className="modal-desc-section">
              <h4 className="section-title font-mono">
                <Info className="info-icon text-primary" />
                Detailed Security Report
              </h4>
              <p className="desc-text font-sans">
                {selectedBlock.details || "This deployment has triggered gate blocks on all safety analyzers due to insecure credential variables and exposed inbound traffic configurations."}
              </p>
            </div>

            {/* Sub-Agent Individual Risk Scoring */}
          <div className="modal-agent-score-section border-outline-variant">
  <h4 className="section-title font-mono">Sub-Agent Assessment Breakdown</h4>

  <div className="agent-breakdown-scores font-mono">
    <div>
      <p className="agent-label">Code Risk</p>
      <p
        className={`score-value font-bold ${
          selectedBlock.agent_scores.code_risk > 50
            ? "text-error"
            : "text-green"
        }`}
      >
        {selectedBlock.agent_scores.code_risk}%
      </p>
    </div>

    <div>
      <p className="agent-label">Infra Risk</p>
      <p
        className={`score-value font-bold ${
          selectedBlock.agent_scores.infra_risk > 50
            ? "text-error"
            : "text-green"
        }`}
      >
        {selectedBlock.agent_scores.infra_risk}%
      </p>
    </div>

    <div>
      <p className="agent-label">Incident History</p>
      <p
        className={`score-value font-bold ${
          selectedBlock.agent_scores.incident_risk > 50
            ? "text-error"
            : "text-green"
        }`}
      >
        {selectedBlock.agent_scores.incident_risk}%
      </p>
    </div>
  </div>
</div>
            {/* Recommendations */}
            <div className="modal-remedy-section">
              <h4 className="remedy-title font-mono">Remediation Steps Required</h4>
              <ul className="remedy-list font-sans">
                {selectedBlock.recommendations && selectedBlock.recommendations.length > 0 ? (
                  selectedBlock.recommendations.map((rec, i) => (
                    <li key={i} className="remedy-item">
                      <ChevronRight className="bullet-chevron text-primary" />
                      <span>{rec}</span>
                    </li>
                  ))
                ) : (
                  <li className="remedy-item">
                    <ChevronRight className="bullet-chevron text-primary" />
                    <span>Proceed with standard security cleanup and revoke credentials manually.</span>
                  </li>
                )}
              </ul>
            </div>

            {/* Dismiss Button */}
            <div className="modal-footer-row border-top">
              <button onClick={() => setSelectedBlock(null)} className="acknowledge-btn font-mono">
                Acknowledge Assessment
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: New Deployment Simulation Trigger */}
      {showNewDeploymentModal && (
        <div className="modal-overlay">
          <div className="modal-backdrop" onClick={() => !isScanning && setShowNewDeploymentModal(false)} />
          
          <div className="modal-card scan-modal">
            {/* Header */}
            <div className="modal-header border-bottom">
              <div className="modal-title-group">
                <Sparkles className="modal-title-icon text-primary" />
                <h3 className="modal-title font-sans">
                  DeployGuard Pipeline Scanner
                </h3>
              </div>
              {!isScanning && (
                <button onClick={() => setShowNewDeploymentModal(false)} className="modal-close-x-btn">
                  <X className="close-icon" />
                </button>
              )}
            </div>

            {isScanning ? (
              /* Live scan steps indicator animation */
              <div className="scanning-loader-wrapper">
                <div className="spinner-center">
                  <Loader2 className="spin loader-ring text-primary" />
                  <Shield className="loader-shield text-primary" />
                </div>
                
                <div className="loader-details-box">
                  <p className="loader-status-text font-sans">
                    Scanning code deployment commits...
                  </p>
                  
                  {/* Interactive scanning logs console */}
                  <div className="loader-console-logger font-mono border-outline-variant">
                    <p className="log-line text-green">► pipeline: triggered via branch commit</p>
                    {scanStep >= 1 && <p className="log-line text-primary">► system: code check initiated</p>}
                    {scanStep >= 2 && <p className="log-line text-tertiary">► agent-code: scanning static configs...</p>}
                    {scanStep >= 3 && <p className="log-line text-error">► agent-infra: checking ports & firewalls...</p>}
                    {scanStep >= 4 && <p className="log-line text-grey">► agent-incident: comparing previous threat maps...</p>}
                    {scanStep >= 5 && <p className="log-line text-green font-bold">► done: evaluation report generated</p>}
                  </div>
                </div>
              </div>
            ) : (
              /* Setup form */
              <form onSubmit={handleStartScanSimulation} className="modal-form font-sans">
                <p className="form-info-desc">
                  Select repository context to simulate a GitHub commit hook. DeployGuard security agents will automatically inspect code configurations and compute risk telemetry.
                </p>

                <div className="form-inputs-group">
                  {/* Repo select */}
                  <div className="form-field-group">
                    <label className="form-lbl font-mono">Target Repository</label>
                    <select
                      value={newRepo}
                      onChange={(e) => setNewRepo(e.target.value)}
                      className="form-select font-sans"
                    >
                      <option value="myorg/payments-api">myorg/payments-api</option>
                      <option value="myorg/auth-service">myorg/auth-service</option>
                      <option value="myorg/frontend-dashboard">myorg/frontend-dashboard</option>
                    </select>
                  </div>

                  {/* Branch name */}
                  <div className="form-field-group">
                    <label className="form-lbl font-mono">Branch Name</label>
                    <input
                      type="text"
                      required
                      value={newBranch}
                      onChange={(e) => setNewBranch(e.target.value)}
                      className="form-input font-mono text-white"
                      placeholder="e.g. main, fix/auth"
                    />
                  </div>

                  {/* Threat trigger selection */}
                  <div className="form-field-group">
                    <label className="form-lbl font-mono">Simulate Threat Trigger</label>
                    <select
                      value={newThreatType}
                      onChange={(e) => {
                        setNewThreatType(e.target.value);
                        if (e.target.value.includes('AWS')) setNewRiskScore(91);
                        else if (e.target.value.includes('Token')) setNewRiskScore(82);
                        else if (e.target.value.includes('Public')) setNewRiskScore(95);
                        else setNewRiskScore(76);
                      }}
                      className="form-select font-sans"
                    >
                      <option value="Hardcoded Slack Webhook Token">Hardcoded Slack Webhook Token (High)</option>
                      <option value="Plaintext AWS Credentials in Commit">Plaintext AWS Credentials in Commit (Critical)</option>
                      <option value="Public ElasticSearch Node Exposure">Public ElasticSearch Node Exposure (Critical)</option>
                      <option value="Outdated vulnerable Log4j dependency">Outdated vulnerable Log4j dependency (Medium)</option>
                    </select>
                  </div>

                  {/* Risk score slider */}
                  <div className="form-field-group">
                    <div className="slider-label-row font-mono">
                      <span>Simulated Risk Score</span>
                      <span className="slider-score-val text-error">{newRiskScore}/100</span>
                    </div>
                    <input
                      type="range"
                      min="45"
                      max="99"
                      value={newRiskScore}
                      onChange={(e) => setNewRiskScore(Number(e.target.value))}
                      className="slider-input accent-primary"
                    />
                  </div>
                </div>

                <div className="modal-footer-row border-top">
                  <button
                    type="button"
                    onClick={() => setShowNewDeploymentModal(false)}
                    className="cancel-btn font-mono"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="submit-scan-btn font-mono"
                  >
                    <Shield className="shield-icon fill-primary" />
                    Trigger Scan Hook
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

