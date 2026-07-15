import React, { useEffect, useState } from 'react';
import {
  listIncidents,
  searchSimilarIncidents,
  type IncidentRecord,
  type SimilarIncidentMatch,
} from '../api/incidents';
import { Search, Calculator, ShieldAlert, CheckCircle2, HelpCircle, History, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import './IncidentHistory.css'; // Keep using the stylesheet

export const Incidents: React.FC = () => {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Playground states
  const [playgroundText, setPlaygroundText] = useState('feat: Add database migrations and disable oauth validation temporarily');
  const [calculating, setCalculating] = useState(false);
  const [similarityResults, setSimilarityResults] = useState<SimilarIncidentMatch[]>([]);

  const fetchIncidents = async () => {
    try {
      const response = await listIncidents();
      setIncidents(response.items);
    } catch (err) {
      console.error('Failed to load incidents:', err);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const filteredIncidents = incidents.filter(inc => 
    inc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inc.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inc.service.toLowerCase().includes(searchQuery.toLowerCase()) ||
    inc.incident_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const runSimilarityPlayground = async (e: React.FormEvent) => {
    e.preventDefault();
    setCalculating(true);
    try {
      const response = await searchSimilarIncidents({
        text: playgroundText,
      });
      setSimilarityResults(response.matches);
    } catch (err) {
      console.error(err);
    } finally {
      setCalculating(false);
    }
  };

  return (
    <div className="incident-history-container fade-in">
      <div className="incident-history-header">
        <h1>
          <History className="header-icon text-rose" />
          Outages &amp; Incidents Archive
        </h1>
        <p>Browse historical system failures and perform real-time vector matches against proposed pull requests.</p>
      </div>

      <div className="history-grid-layout">
        {/* Left Pane: Outages database */}
        <section className="incidents-db-panel">
          <div className="panel-header-row">
            <h2>Incident Database ({filteredIncidents.length})</h2>
            <div className="search-input-wrapper">
              <Search className="search-icon" />
              <input 
                type="text" 
                placeholder="Search database..." 
                value={searchQuery}
                onChange={handleSearch}
                style={{ width: '100%', padding: '8px 12px 8px 32px', background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '6px', color: 'var(--text-primary)' }}
                className="font-mono"
              />
            </div>
          </div>

          <div className="incidents-list" style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
            {filteredIncidents.map((inc) => {
              const sev = inc.severity.toLowerCase();
              let SevIcon = Info;
              if (sev === 'critical') SevIcon = AlertTriangle;
              else if (sev === 'high') SevIcon = AlertCircle;
              else if (sev === 'medium') SevIcon = Info;
              else if (sev === 'low') SevIcon = CheckCircle2;

              return (
                <div key={inc.incident_id} className="incident-card" style={{ padding: '16px', background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', borderRadius: '8px' }}>
                  <div className="incident-card-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span className="inc-id font-mono" style={{ fontWeight: 'bold', color: 'var(--accent-cyan)' }}>{inc.incident_id}</span>
                    <span className={`sev-badge ${sev}`} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <SevIcon className="sev-badge-icon" size={12} />
                      {sev === 'critical' ? 'CRIT' : sev.toUpperCase()}
                    </span>
                  </div>
                  <h3 className="inc-title" style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '6px' }}>{inc.title}</h3>
                  <p className="inc-desc" style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{inc.description}</p>
                  
                  {inc.root_cause && (
                    <div style={{ background: 'var(--bg-secondary)', padding: '8px', borderRadius: '4px', marginTop: '8px', fontSize: '11px' }} className="font-mono">
                      <span className="text-rose">Root Cause:</span> {inc.root_cause}
                    </div>
                  )}

                  <div className="incident-card-bottom" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
                    <span className="inc-service">Service: <span style={{ color: '#fff' }}>{inc.service}</span></span>
                    <span className="inc-env">Env: <span style={{ color: '#fff' }}>{inc.environment}</span></span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Right Pane: Similarity Lookup Playground */}
        <section className="similarity-playground-panel">
          <h2>Semantic Similarity Playground</h2>
          <p className="section-desc">Generate query embeddings on the fly and perform vector matching against historical incidents.</p>

          <form onSubmit={runSimilarityPlayground} className="playground-form" style={{ marginTop: '16px' }}>
            <div className="form-group font-mono">
              <label>Deployment Description / Commit Message</label>
              <textarea 
                rows={4} 
                value={playgroundText} 
                onChange={(e) => setPlaygroundText(e.target.value)} 
                required 
              />
            </div>

            <button type="submit" className="calculate-btn font-mono" style={{ marginTop: '12px', width: '100%', justifyContent: 'center' }} disabled={calculating}>
              <Calculator className="btn-icon" />
              <span>{calculating ? 'Analyzing Vector Space...' : 'Perform Semantic Search'}</span>
            </button>
          </form>

          {/* Results display */}
          <div className="similarity-results-container" style={{ marginTop: '24px' }}>
            <h3>Matching Vector Hits</h3>
            <p className="threshold-info">Matching threshold is set to <span style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>0.50</span>.</p>

            {similarityResults.length === 0 ? (
              <div className="results-placeholder">
                <HelpCircle className="placeholder-icon" />
                <span>Type a message above and run similarity analysis to find matching incidents in vector space.</span>
              </div>
            ) : (
              <div className="results-list" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
                {similarityResults.map((res) => {
                  const isMatched = (res.similarity || 0) >= 0.50;
                  return (
                    <div key={res.incident_id} className={`result-row ${isMatched ? 'matched' : 'unmatched'}`}>
                      <div className="result-row-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div className="result-id-group">
                          <span className="res-id font-mono">{res.incident_id}</span>
                          <h4 className="res-title">{res.title}</h4>
                        </div>
                        <div className="score-badge-group font-mono" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span className="similarity-score-label" style={{ fontSize: '10px' }}>Match:</span>
                          <span className={`similarity-score-val ${isMatched ? 'pass' : 'fail'}`} style={{ fontWeight: 'bold' }}>
                            {res.similarity}
                          </span>
                        </div>
                      </div>
                      
                      <div className="result-row-footer" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                        {isMatched ? (
                          <div className="verdict-banner matched" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <ShieldAlert className="banner-icon" size={12} />
                            <span style={{ fontSize: '10px', fontWeight: 'bold' }}>RISK MATCH DETECTED</span>
                          </div>
                        ) : (
                          <div className="verdict-banner unmatched" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <CheckCircle2 className="banner-icon" size={12} />
                            <span style={{ fontSize: '10px', fontWeight: 'bold' }}>Below Threshold</span>
                          </div>
                        )}
                        <span className="res-service font-mono" style={{ fontSize: '11px' }}>{res.service}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};
export default Incidents;
