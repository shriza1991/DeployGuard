import React, { useEffect, useState } from 'react';
import {
  listIncidents,
  searchSimilarIncidents,
  type IncidentRecord,
  type SimilarIncidentMatch,
} from '../api/incidents';
import { Search, Calculator, ShieldAlert, CheckCircle2, HelpCircle, History, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import './IncidentHistory.css';

export const IncidentHistory: React.FC = () => {
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
    
      const response = await searchSimilarIncidents({
  text: playgroundText,
});

setSimilarityResults(response.matches);
  };

  return (
    <div className="incident-history-container fade-in">
      <div className="incident-history-header">
        <h1>
          <History className="header-icon" />
          Incident History Database
        </h1>
        <p>Analyze historical failures and perform real-time semantic similarity lookups against previous outages.</p>
      </div>

      <div className="history-grid-layout">
        {/* Left Pane: Seeded Incidents Database */}
        <section className="incidents-db-panel">
          <div className="panel-header-row">
            <h2>Outage Database ({filteredIncidents.length})</h2>
            <div className="search-input-wrapper">
              <Search className="search-icon" />
              <input 
                type="text" 
                placeholder="Search incidents..." 
                value={searchQuery}
                onChange={handleSearch}
              />
            </div>
          </div>

          <div className="incidents-list">
            {filteredIncidents.map((inc) => {
              const sev = inc.severity.toLowerCase();
              let SevIcon = Info;
              if (sev === 'critical') SevIcon = AlertTriangle;
              else if (sev === 'high') SevIcon = AlertCircle;
              else if (sev === 'medium') SevIcon = Info;
              else if (sev === 'low') SevIcon = CheckCircle2;

              return (
                <div key={inc.incident_id} className="incident-card">
                  <div className="incident-card-top">
                    <span className="inc-id">{inc.incident_id}</span>
                    <span className={`sev-badge ${sev}`}>
                      <SevIcon className="sev-badge-icon" />
                      {sev === 'critical' ? 'CRIT' : sev.toUpperCase()}
                    </span>
                  </div>
                  <h3 className="inc-title">{inc.title}</h3>
                  <p className="inc-desc">{inc.description}</p>
                  <div className="incident-card-bottom">
                    <span className="inc-service">Service: <span>{inc.service}</span></span>
                    <span className="inc-env">Env: <span>{inc.environment}</span></span>
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

          <form onSubmit={runSimilarityPlayground} className="playground-form">
            <div className="form-group">
              <label>Deployment Description / Commit Message</label>
              <textarea 
                rows={4} 
                value={playgroundText} 
                onChange={(e) => setPlaygroundText(e.target.value)} 
                required 
              />
            </div>

            <button type="submit" className="calculate-btn" disabled={calculating}>
              <Calculator className="btn-icon" />
              <span>{calculating ? 'Analyzing Vector Space...' : 'Perform Semantic Search'}</span>
            </button>
          </form>

          {/* Results display */}
          <div className="similarity-results-container">
            <h3>Matching Vector Hits</h3>
            <p className="threshold-info">Matching threshold is set to <span>0.50</span>.</p>

            {similarityResults.length === 0 ? (
              <div className="results-placeholder">
                <HelpCircle className="placeholder-icon" />
                <span>Type a message above and run similarity analysis to find matching incidents in vector space.</span>
              </div>
            ) : (
              <div className="results-list">
                {similarityResults.map((res) => {
                  const isMatched = (res.similarity || 0) >= 0.50;
                  return (
                    <div key={res.incident_id} className={`result-row ${isMatched ? 'matched' : 'unmatched'}`}>
                      <div className="result-row-header">
                        <div className="result-id-group">
                          <span className="res-id">{res.incident_id}</span>
                          <h4 className="res-title">{res.title}</h4>
                        </div>
                        <div className="score-badge-group">
                          <span className="similarity-score-label">Similarity:</span>
                          <span className={`similarity-score-val ${isMatched ? 'pass' : 'fail'}`}>
                            {res.similarity}
                          </span>
                        </div>
                      </div>
                      
                      <div className="result-row-footer">
                        {isMatched ? (
                          <div className="verdict-banner matched">
                            <ShieldAlert className="banner-icon" />
                            <span>RISK MATCH DETECTED</span>
                          </div>
                        ) : (
                          <div className="verdict-banner unmatched">
                            <CheckCircle2 className="banner-icon" />
                            <span>Below Threshold</span>
                          </div>
                        )}
                        <span className="res-service">{res.service}</span>
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

