import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { listDeployments, type DeploymentSummary } from '../api/dashboard';
import { 
  Rocket, 
  Search, 
  Copy, 
  FileJson, 
  ExternalLink, 
  ChevronLeft, 
  ChevronRight, 
  SlidersHorizontal,
  Check,
  Terminal,
  RefreshCw,
} from 'lucide-react';
import { ConfidenceDisplay } from '../components/ConfidenceDisplay';
import './Deployments.css';

export const Deployments: React.FC = () => {
  const navigate = useNavigate();
  const [deployments, setDeployments] = useState<DeploymentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [authorFilter, setAuthorFilter] = useState<string>('ALL');
  const [projectFilter, setProjectFilter] = useState<string>('');
  
  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);



  // UI toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const fetchDeployments = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch deployments from backend using filters
      const response = await listDeployments({
        project: projectFilter || undefined,
        decision: decisionFilter === 'ALL' ? undefined : decisionFilter as any,
        page,
        page_size: pageSize,
      });

      setDeployments(response.items);
      setTotal(response.total);
    } catch (e) {
      console.error('Failed to fetch deployments:', e);
    } finally {
      setLoading(false);
    }
  }, [page, decisionFilter, projectFilter, pageSize]);

  useEffect(() => {
    fetchDeployments();
  }, [fetchDeployments]);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    triggerToast(`Copied Correlation ID: ${id.substring(0, 12)}...`);
  };

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(deployments, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `deployguard_deployments_page_${page}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    triggerToast("Exported deployments to JSON successfully!");
  };

  // Get unique list of authors in current page for the author filter options
  const uniqueAuthors = Array.from(new Set(deployments.map(d => d.branch || 'unknown')));

  // Local client side filtering for variables that are not fully filtered by backend API
  const filteredItems = deployments.filter(dep => {
    const matchesSearch = searchQuery === '' || 
      dep.repository.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dep.correlation_id.toLowerCase().includes(searchQuery.toLowerCase());
      
    const matchesSeverity = severityFilter === 'ALL' || 
      (dep.severity && dep.severity.toUpperCase() === severityFilter.toUpperCase());

    const matchesAuthor = authorFilter === 'ALL' || 
      (dep.branch && dep.branch === authorFilter);

    return matchesSearch && matchesSeverity && matchesAuthor;
  });

  const totalPages = Math.ceil(total / pageSize) || 1;

  const formatDate = (isoStr?: string) => {
    if (!isoStr) return '';
    return new Date(isoStr).toLocaleString();
  };

  return (
    <div className="deployments-container fade-in">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="toast-notification font-mono">
          <Check className="toast-icon text-green" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="deployments-header">
        <div className="header-meta-group">
          <div className="title-row" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Rocket size={24} className="text-indigo" />
            <h2>Deployment Audits</h2>
          </div>
          <p className="page-subtitle">
            Browse, search, and audit all deployment releases processed by risk gates.
          </p>
        </div>

        <button onClick={handleExportJSON} className="btn-secondary-stitch font-mono">
          <FileJson size={14} />
          <span>Export JSON</span>
        </button>
      </div>

      {/* Filters Panel */}
      <div className="glass-panel" style={{ padding: '16px', marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          
          {/* Search bar */}
          <div className="search-bar-wrapper" style={{ flexGrow: 1, minWidth: '240px' }}>
            <Search className="search-bar-icon" />
            <input 
              type="text" 
              placeholder="Search by ID or repository..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="font-mono"
            />
          </div>

          {/* Project search */}
          <div style={{ position: 'relative', width: '200px' }}>
            <input 
              type="text" 
              placeholder="Filter repository..." 
              value={projectFilter}
              onChange={(e) => {
                setProjectFilter(e.target.value);
                setPage(1);
              }}
              style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '6px', color: 'var(--text-primary)' }}
              className="font-mono"
            />
          </div>

          {/* Decision filter */}
          <div className="filter-dropdown-wrapper">
            <SlidersHorizontal size={14} className="filter-icon" />
            <select
              value={decisionFilter}
              onChange={(e) => {
                setDecisionFilter(e.target.value);
                setPage(1);
              }}
              className="filter-select font-mono"
            >
              <option value="ALL">Decision: All</option>
              <option value="SAFE">SAFE</option>
              <option value="REVIEW">REVIEW</option>
              <option value="BLOCK">BLOCK</option>
            </select>
          </div>

          {/* Severity filter */}
          <div className="filter-dropdown-wrapper">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="filter-select font-mono"
              style={{ paddingLeft: '12px' }}
            >
              <option value="ALL">Severity: All</option>
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          {/* Author/branch filter */}
          <div className="filter-dropdown-wrapper">
            <select
              value={authorFilter}
              onChange={(e) => setAuthorFilter(e.target.value)}
              className="filter-select font-mono"
              style={{ paddingLeft: '12px' }}
            >
              <option value="ALL">Branch: All</option>
              {uniqueAuthors.map(auth => (
                <option key={auth} value={auth}>{auth}</option>
              ))}
            </select>
          </div>

        </div>
      </div>

      {/* Deployments Table */}
      <div className="glass-panel" style={{ padding: '0px', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px', gap: '14px', color: 'var(--text-muted)' }}>
            <div style={{ width: '24px', height: '24px', border: '2px solid var(--panel-border)', borderTopColor: 'var(--accent-cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            <span className="font-mono" style={{ fontSize: '12px' }}>Fetching deployments archive...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div style={{ padding: '64px 32px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px' }}>
            <Rocket size={32} style={{ color: 'var(--text-muted)', opacity: 0.35 }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', margin: 0 }}>No deployment analyses found</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '380px', lineHeight: '1.5', margin: 0 }}>
              {searchQuery || decisionFilter !== 'ALL' || projectFilter
                ? 'No results match your active filters. Try broadening your search criteria.'
                : 'No deployment analyses yet. Connect a GitHub repository or run a simulated scan to begin.'}
            </p>
            {!searchQuery && decisionFilter === 'ALL' && !projectFilter && (
              <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                <button onClick={() => navigate('/simulator')} className="btn-primary-stitch font-mono">
                  <Terminal size={13} /> Run Simulation
                </button>
                <button onClick={() => navigate('/')} className="btn-secondary-stitch font-mono">
                  <RefreshCw size={13} /> Go to Dashboard
                </button>
              </div>
            )}
          </div>
        ) : (
          <>
            <table className="blocks-table font-mono" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--panel-border)', background: 'rgba(255,255,255,0.01)' }}>
                  <th style={{ padding: '16px' }}>Repository</th>
                  <th style={{ padding: '16px' }}>Decision</th>
                  <th style={{ padding: '16px' }}>Risk Score</th>
                  <th style={{ padding: '16px' }}>Analysis Confidence</th>
                  <th style={{ padding: '16px' }}>Branch</th>
                  <th style={{ padding: '16px' }}>Created Time</th>
                  <th style={{ padding: '16px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((dep) => (
                  <tr 
                    key={dep.correlation_id}
                    style={{ borderBottom: '1px solid var(--panel-border)' }}
                    className="table-row-hover"
                  >
                    <td style={{ padding: '16px', fontWeight: 'bold', color: '#fff' }}>{dep.repository}</td>
                    <td style={{ padding: '16px' }}>
                      <span className={`verdict-tag-small ${dep.decision?.toLowerCase() || 'pending'}`}>
                        {dep.decision || 'PENDING'}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }}>
                      <span className={`score-badge ${(dep.overall_score ?? 0) >= 60 ? 'high' : (dep.overall_score ?? 0) >= 30 ? 'medium' : 'low'}`}>
                        {dep.overall_score ?? '-'}
                      </span>
                    </td>
                    <td style={{ padding: '16px' }}>
                      <ConfidenceDisplay value={dep.overall_confidence} compact={true} />
                    </td>
                    <td style={{ padding: '16px', color: 'var(--text-secondary)' }}>{dep.branch || '-'}</td>
                    <td style={{ padding: '16px', color: 'var(--text-muted)' }}>{formatDate(dep.generated_at)}</td>
                    <td style={{ padding: '16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        <button 
                          onClick={() => handleCopyId(dep.correlation_id)}
                          className="control-btn"
                          title="Copy Correlation ID"
                          style={{ padding: '6px' }}
                        >
                          <Copy size={12} />
                        </button>
                        <button 
                          onClick={() => navigate(`/deployments/${dep.correlation_id}`)}
                          className="btn-primary-stitch"
                          style={{ minHeight: '28px', padding: '4px 10px' }}
                        >
                          <ExternalLink size={12} />
                          <span>Details</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderTop: '1px solid var(--panel-border)' }}>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Showing <span style={{ color: '#fff', fontWeight: 'bold' }}>{filteredItems.length}</span> of <span style={{ color: '#fff', fontWeight: 'bold' }}>{total}</span> total audits
              </p>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  disabled={page === 1}
                  onClick={() => setPage(prev => Math.max(1, prev - 1))}
                  className="page-nav-btn"
                  style={{ display: 'flex', alignItems: 'center', padding: '6px 12px', background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', color: page === 1 ? 'var(--text-muted)' : '#fff', cursor: page === 1 ? 'not-allowed' : 'pointer', borderRadius: '4px' }}
                >
                  <ChevronLeft size={14} />
                  <span>Previous</span>
                </button>
                <div style={{ display: 'flex', alignItems: 'center', padding: '0 12px', color: 'var(--text-secondary)', fontSize: '13px' }} className="font-mono">
                  Page {page} of {totalPages}
                </div>
                <button
                  disabled={page === totalPages}
                  onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                  className="page-nav-btn"
                  style={{ display: 'flex', alignItems: 'center', padding: '6px 12px', background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', color: page === totalPages ? 'var(--text-muted)' : '#fff', cursor: page === totalPages ? 'not-allowed' : 'pointer', borderRadius: '4px' }}
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
export default Deployments;
