import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { DeploymentEvent } from '../api/client';
import { 
  Shield, 
  Play, 
  Loader2, 
  ArrowRight,
  Search,
  Sliders,
  ChevronDown,
  Bell,
  Calendar,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Check,
  X
} from 'lucide-react';

import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const [deployments, setDeployments] = useState<DeploymentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Webhook form states
  const [repository, setRepository] = useState('myorg/checkout-service');
  const [prTitle, setPrTitle] = useState('feat: Add database migrations and disable oauth validation temporarily');
  const [prBody, setPrBody] = useState('This pull request modifies security rules and updates table indexing.');
  const [commitMsg, setCommitMsg] = useState('feat: migration and temporarily bypass oauth check');
  const [submitting, setSubmitting] = useState(false);
  const [activeCorrelationId, setActiveCorrelationId] = useState<string | null>(null);

  // Search & Filter controls
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('all');

  // Header Dropdown/Mock Selector States
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [timePeriod, setTimePeriod] = useState<'24h' | '7d' | '30d'>('24h');
  const [isCustomDateOpen, setIsCustomDateOpen] = useState(false);

  // Notification Alerts
  const [notifications, setNotifications] = useState([
    { id: 1, message: "Critical block on auth-service", time: "1h ago", unread: true, type: "block" },
    { id: 2, message: "Policy evaluation completed for dg-api", time: "2h ago", unread: true, type: "safe" },
    { id: 3, message: "High latency spike detected US-East-1", time: "4h ago", unread: false, type: "alert" }
  ]);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

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
    fetchDeployments();
    
    // Poll for active pending deployments
    const interval = setInterval(async () => {
      let hasPending = false;
      const current = await api.getDeployments();
      
      for (const d of current) {
        if (d.status === 'pending') {
          hasPending = true;
          await api.getDecision(d.correlation_id);
        }
      }
      
      if (hasPending) {
        fetchDeployments();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleSimulateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const correlationId = await api.triggerDeployment(repository, prTitle, prBody, commitMsg);
      setActiveCorrelationId(correlationId);
      await fetchDeployments();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  // Compute metrics (global across all deployments)
  const total = deployments.length;
  const safe = deployments.filter(d => d.decision === 'SAFE').length;
  const blocked = deployments.filter(d => d.decision === 'BLOCK').length;
  const avgScore = total > 0 ? Math.round(deployments.reduce((acc, d) => acc + (d.overall_score || 0), 0) / total) : 0;

  // Filter list of deployments based on user search queries and selector values
  const filteredDeployments = deployments.filter(dep => {
    const query = searchQuery.toLowerCase().trim();
    const matchesSearch = query === '' ||
      dep.repository.toLowerCase().includes(query) ||
      dep.commit_message.toLowerCase().includes(query) ||
      dep.correlation_id.toLowerCase().includes(query);

    const matchesVerdict = verdictFilter === 'all' ||
      (dep.decision && dep.decision.toLowerCase() === verdictFilter.toLowerCase()) ||
      (dep.status === 'pending' && verdictFilter === 'pending');

    return matchesSearch && matchesVerdict;
  });

  // Pagination bounds
  const totalPages = Math.ceil(filteredDeployments.length / itemsPerPage) || 1;
  const paginatedDeployments = filteredDeployments.slice(
    (currentPage - 1) * itemsPerPage,
    (currentPage - 1) * itemsPerPage + itemsPerPage
  );

  return (
    <div className="dashboard-container fade-in">
      {/* Header controls layout mimicking Stitch */}
      <div className="dashboard-header-container">
        <div className="dashboard-header-left">
          <div className="title-area">
            <div className="title-icon-wrapper">
              <Shield className="title-icon" />
            </div>
            <h1>Platform Dashboard</h1>
          </div>
          <p className="description">
            Real-time security auditing and risk gating pipeline analytics.
          </p>
        </div>

        <div className="dashboard-header-right">
          {/* Project selector */}
          <div className="relative-container">
            <button
              onClick={() => setIsProjectDropdownOpen(!isProjectDropdownOpen)}
              className="control-btn font-mono"
            >
              <span>shriza1991/DeployGuard</span>
              <ChevronDown className={`chevron-icon ${isProjectDropdownOpen ? 'rotated' : ''}`} />
            </button>
            {isProjectDropdownOpen && (
              <div className="dropdown-menu project-menu">
                <div className="menu-header">Active Repository</div>
                <div className="menu-item active">
                  <div className="item-title font-mono">
                    <span>shriza1991/DeployGuard</span>
                    <Check className="check-icon" />
                  </div>
                  <p className="item-desc">Primary workspace codebase repository.</p>
                </div>
              </div>
            )}
          </div>

          {/* Notifications bell */}
          <div className="relative-container">
            <button
              onClick={() => setIsAlertsOpen(!isAlertsOpen)}
              className="control-btn bell-btn"
            >
              <Bell className="bell-icon" />
              {notifications.some(n => n.unread) && <span className="notification-dot" />}
            </button>
            {isAlertsOpen && (
              <div className="dropdown-menu alerts-menu">
                <div className="menu-header flex-header">
                  <span>Security Log</span>
                  <button
                    onClick={() => setNotifications(prev => prev.map(n => ({ ...n, unread: false })))}
                    className="mark-read-btn"
                  >
                    Mark all read
                  </button>
                </div>
                <div className="alerts-list">
                  {notifications.map(n => (
                    <div key={n.id} className={`alert-item ${n.unread ? 'unread' : ''}`}>
                      <div className="alert-meta">
                        <span className="alert-time">{n.time}</span>
                        <span className={`alert-dot ${n.type}`} />
                      </div>
                      <p className="alert-msg">{n.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Time range selector */}
          <div className="timeframe-selector">
            <button
              onClick={() => setTimePeriod('24h')}
              className={`time-btn ${timePeriod === '24h' ? 'active' : ''}`}
            >
              24h
            </button>
            <button
              onClick={() => setTimePeriod('7d')}
              className={`time-btn ${timePeriod === '7d' ? 'active' : ''}`}
            >
              7d
            </button>
            <button
              onClick={() => setTimePeriod('30d')}
              className={`time-btn ${timePeriod === '30d' ? 'active' : ''}`}
            >
              30d
            </button>
            <div className="divider-line" />
            <button
              onClick={() => setIsCustomDateOpen(!isCustomDateOpen)}
              className="calendar-btn"
            >
              <Calendar className="calendar-icon" />
              <span>
                {timePeriod === '24h'
                  ? 'Jul 07 - Jul 08, 2026'
                  : timePeriod === '7d'
                  ? 'Jul 01 - Jul 08, 2026'
                  : 'Jun 08 - Jul 08, 2026'}
              </span>
            </button>
            {isCustomDateOpen && (
              <div className="dropdown-menu calendar-dropdown">
                <div className="calendar-header">
                  <span>Custom Timeframe</span>
                  <button onClick={() => setIsCustomDateOpen(false)} className="close-btn"><X className="x-icon" /></button>
                </div>
                <div className="calendar-body">
                  <div className="date-group">
                    <label>Start Date</label>
                    <input type="date" defaultValue="2026-07-01" readOnly className="date-input" />
                  </div>
                  <div className="date-group">
                    <label>End Date</label>
                    <input type="date" defaultValue="2026-07-08" readOnly className="date-input" />
                  </div>
                  <button onClick={() => setIsCustomDateOpen(false)} className="apply-btn">Apply Filter</button>
                </div>
              </div>
            )}
          </div>

          {/* New deployment scroll button */}
          <button
            onClick={() => {
              const el = document.getElementById('webhook-simulator-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="new-deployment-btn font-mono"
          >
            New Deployment
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card total-card">
          <div className="kpi-card-header">
            <span className="kpi-title">TOTAL AUDITED</span>
            <span className="trend-badge">
              <TrendingUp className="trend-icon" />
              12%
            </span>
          </div>
          <div className="kpi-card-value font-mono">{total}</div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill primary" style={{ width: '80%' }} />
          </div>
        </div>

        <div className="kpi-card safe-card">
          <div className="kpi-card-header">
            <span className="kpi-title">PASSED SAFE</span>
          </div>
          <div className="kpi-card-value-group">
            <span className="kpi-card-value safe-text font-mono">{safe}</span>
            <span className="kpi-percentage font-mono">
              {total > 0 ? ((safe / total) * 100).toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="kpi-progress-bar">
            <div 
              className="kpi-progress-fill secondary" 
              style={{ width: `${total > 0 ? (safe / total) * 100 : 0}%` }} 
            />
          </div>
        </div>

        <div className="kpi-card blocked-card">
          <div className="kpi-card-header">
            <span className="kpi-title">ROLLOUT BLOCKED</span>
          </div>
          <div className="kpi-card-value-group">
            <span className="kpi-card-value error-text font-mono">{blocked}</span>
            <span className="kpi-percentage font-mono">
              {total > 0 ? ((blocked / total) * 100).toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="kpi-progress-bar">
            <div 
              className="kpi-progress-fill error" 
              style={{ width: `${total > 0 ? (blocked / total) * 100 : 0}%` }} 
            />
          </div>
        </div>

        <div className="kpi-card risk-card">
          <div className="kpi-card-header">
            <span className="kpi-title">AVERAGE RISK SCORE</span>
          </div>
          <div className="kpi-card-value-group">
            <span className="kpi-card-value font-mono">{avgScore}</span>
            <span className="kpi-score-max font-mono">/100</span>
          </div>
          <div className="risk-level-tag font-mono">
            {avgScore >= 60 ? (
              <span className="tag-high">HIGH RISK</span>
            ) : avgScore >= 30 ? (
              <span className="tag-medium">MEDIUM RISK</span>
            ) : (
              <span className="tag-low">LOW RISK</span>
            )}
          </div>
          <div className="kpi-progress-bar">
            <div 
              className={`kpi-progress-fill ${avgScore >= 60 ? 'error' : avgScore >= 30 ? 'tertiary' : 'secondary'}`} 
              style={{ width: `${avgScore}%` }} 
            />
          </div>
        </div>
      </div>

      <div className="dashboard-content-layout">
        {/* Webhook Simulator Section */}
        <section id="webhook-simulator-section" className="webhook-simulator-panel">
          <h2>Simulate GitHub Webhook</h2>
          <p className="section-desc">Submit a mock pull request payload to trigger the multi-agent Kafka pipeline.</p>
          
          <form onSubmit={handleSimulateWebhook} className="simulator-form">
            <div className="form-group font-mono">
              <label>Target Repository</label>
              <input 
                type="text" 
                value={repository} 
                onChange={(e) => setRepository(e.target.value)} 
                required 
              />
            </div>
            
            <div className="form-group font-mono">
              <label>Pull Request Title</label>
              <input 
                type="text" 
                value={prTitle} 
                onChange={(e) => setPrTitle(e.target.value)} 
                required 
              />
            </div>

            <div className="form-group font-mono">
              <label>PR Description</label>
              <textarea 
                rows={2} 
                value={prBody} 
                onChange={(e) => setPrBody(e.target.value)} 
                required 
              />
            </div>

            <div className="form-group font-mono">
              <label>Commit Message</label>
              <input 
                type="text" 
                value={commitMsg} 
                onChange={(e) => setCommitMsg(e.target.value)} 
                required 
              />
            </div>

            <button type="submit" className="simulate-btn font-mono" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="btn-icon spin" />
                  <span>Dispatching...</span>
                </>
              ) : (
                <>
                  <Play className="btn-icon" />
                  <span>Send GitHub Webhook Event</span>
                </>
              )}
            </button>
          </form>

          {activeCorrelationId && (
            <div className="active-pipeline-status">
              <div className="pipeline-header">
                <h3>Active Audit: <span className="font-mono">{activeCorrelationId.substring(0, 10)}...</span></h3>
                <Loader2 className="spin pipe-loader" />
              </div>
              <div className="pipeline-steps font-mono">
                <div className="step active">Gateway</div>
                <div className="step-arrow"><ArrowRight size={14} /></div>
                <div className="step active">Kafka Topic</div>
                <div className="step-arrow"><ArrowRight size={14} /></div>
                <div className="step active">Agents</div>
                <div className="step-arrow"><ArrowRight size={14} /></div>
                <div className="step">Aggregator</div>
              </div>
            </div>
          )}
        </section>

        {/* Recent Audits list */}
        <section className="recent-audits-panel">
          <div className="panel-header-row">
            <div className="title-desc-group">
              <h2>Recent Deployment Audits</h2>
              <p className="section-desc">Audit results compiled from the distributed evaluation engine.</p>
            </div>
            
            <div className="controls-row">
              {/* Search Bar */}
              <div className="search-bar-wrapper">
                <Search className="search-icon" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Filter by ID or Repo..."
                  className="search-input font-mono"
                />
              </div>

              {/* Verdict Filter */}
              <div className="filter-dropdown-wrapper">
                <Sliders className="filter-icon" />
                <select
                  value={verdictFilter}
                  onChange={(e) => {
                    setVerdictFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="filter-select font-mono"
                >
                  <option value="all">Decision: All</option>
                  <option value="safe">SAFE</option>
                  <option value="review">REVIEW</option>
                  <option value="block">BLOCK</option>
                  <option value="pending">PENDING</option>
                </select>
              </div>
            </div>
          </div>

          <div className="audits-table-wrapper">
            {loading ? (
              <div className="loading-state">
                <Loader2 className="spin load-spinner" />
                <span>Loading deployments...</span>
              </div>
            ) : filteredDeployments.length === 0 ? (
              <div className="empty-state">No audits match current filters.</div>
            ) : (
              <>
                <table className="audits-table font-mono">
                  <thead>
                    <tr>
                      <th className="repo-th">Repo</th>
                      <th className="score-th">Score</th>
                      <th className="verdict-th">Verdict</th>
                      <th className="status-th">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedDeployments.map((dep) => (
                      <tr key={dep.correlation_id} className="table-row">
                        <td className="repo-col">
                          <span className="repo-name">{dep.repository}</span>
                          <span className="commit-desc">{dep.commit_message}</span>
                        </td>
                        <td>
                          {dep.status === 'pending' ? (
                            <span className="score-pending">-</span>
                          ) : (
                            <span className={`score-badge ${
                              dep.overall_score! >= 60 ? 'high' : dep.overall_score! >= 30 ? 'medium' : 'low'
                            }`}>
                              {dep.overall_score}
                            </span>
                          )}
                        </td>
                        <td>
                          {dep.status === 'pending' ? (
                            <span className="verdict-tag pending">PENDING</span>
                          ) : (
                            <span className={`verdict-tag ${dep.decision?.toLowerCase()}`}>
                              {dep.decision}
                            </span>
                          )}
                        </td>
                        <td>
                          {dep.status === 'pending' ? (
                            <span className="status-label processing">
                              <Loader2 className="spin badge-spinner" />
                              Evaluating
                            </span>
                          ) : (
                            <span className="status-label completed">Done</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pagination Controls */}
                <div className="table-pagination">
                  <p className="pagination-text">
                    Showing <span className="highlight">{(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, filteredDeployments.length)}</span> of <span className="highlight">{filteredDeployments.length}</span> deployments
                  </p>
                  <div className="pagination-buttons">
                    <button
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      className="page-nav-btn"
                    >
                      <ChevronLeft className="nav-chevron" />
                    </button>
                    {Array.from({ length: totalPages }).map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setCurrentPage(i + 1)}
                        className={`page-num-btn font-mono ${currentPage === i + 1 ? 'active' : ''}`}
                      >
                        {i + 1}
                      </button>
                    ))}
                    <button
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                      className="page-nav-btn"
                    >
                      <ChevronRight className="nav-chevron" />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

