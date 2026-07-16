import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchRepository, type SearchHit } from '../api/repository';
import { Search, FileCode, Check, Copy, Tag, MessageSquare, Award, Compass } from 'lucide-react';
import './Dashboard.css'; // Reuse design system and glass-panel rules

export const SearchRepository: React.FC = () => {
  const [queryText, setQueryText] = useState('');
  const [activeQuery, setActiveQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Default parameters
  const repoName = 'shriza1991/DeployGuard';
  const branchName = 'main';

  // Search query using React Query
  const searchQuery = useQuery({
    queryKey: ['repoSearch', repoName, activeQuery, branchName],
    queryFn: () => searchRepository(repoName, activeQuery, branchName, 6),
    enabled: activeQuery.trim().length > 0,
    retry: false
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (queryText.trim()) {
      setActiveQuery(queryText);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const results = searchQuery.data?.results ?? [];

  // Group chunks by file path for cleaner UX
  const filesMap: Record<string, SearchHit[]> = {};
  results.forEach(hit => {
    const path = hit.payload.relative_path;
    if (!filesMap[path]) filesMap[path] = [];
    filesMap[path].push(hit);
  });

  return (
    <div className="dashboard-container fade-in">
      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '24px' }}>
        <div className="dashboard-header-left">
          <div className="title-area" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Compass size={24} className="text-indigo" />
            <h1>Semantic Code Search</h1>
          </div>
          <p className="description">
            Query the vector database to search across the entire code repository for patterns, classes, and logic.
          </p>
        </div>
      </div>

      {/* Search Input Panel */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '8px' }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px' }}>
          <div style={{ position: 'relative', flexGrow: 1 }}>
            <Search size={18} style={{ position: 'absolute', left: '14px', top: '14px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="e.g. Redis client initialization or FastAPI webhook routers"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--panel-border)',
                borderRadius: '6px',
                padding: '12px 16px 12px 42px',
                color: '#fff',
                fontSize: '14px',
                fontFamily: 'inherit',
                outline: 'none',
                transition: 'border-color 0.15s'
              }}
              onFocus={(e) => e.target.style.borderColor = 'rgba(192, 193, 255, 0.4)'}
              onBlur={(e) => e.target.style.borderColor = 'var(--panel-border)'}
            />
          </div>
          <button
            type="submit"
            className="btn-primary-stitch font-mono"
            style={{
              padding: '0 24px',
              height: '45px',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '13px',
              background: 'linear-gradient(135deg, rgba(192, 193, 255, 0.2), rgba(192, 193, 255, 0.08))',
              border: '1px solid rgba(192, 193, 255, 0.25)',
              color: 'var(--accent-cyan)',
              cursor: 'pointer'
            }}
          >
            Query Vector
          </button>
        </form>
      </div>

      {/* Main Layout Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
        {searchQuery.isLoading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '30vh', gap: '16px', color: 'var(--text-muted)' }}>
            <span style={{ animation: 'spin 1s linear infinite', fontSize: '20px' }}>⏳</span>
            <span>Searching vector space for matches...</span>
          </div>
        )}

        {searchQuery.isError && (
          <div className="glass-panel" style={{ padding: '24px', borderLeft: '4px solid var(--color-block)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <h3 style={{ color: 'var(--color-block)', fontWeight: 600, fontSize: '15px' }}>Retrieval Service Unreachable</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              The Repository Context Service on port 8003 could not be contacted. Searching will become functional when the indexing container is active.
            </p>
          </div>
        )}

        {activeQuery && !searchQuery.isLoading && !searchQuery.isError && results.length === 0 && (
          <div className="glass-panel" style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Search size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <h3>No relevant chunks found</h3>
            <p style={{ fontSize: '13px', marginTop: '4px' }}>Try searching using different concepts or verify repository is indexed.</p>
          </div>
        )}

        {results.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '24px', alignItems: 'start' }}>
            
            {/* Sidebar matching file names */}
            <div className="glass-panel" style={{ padding: '16px' }}>
              <h3 style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', paddingLeft: '8px' }}>
                RELEVANT FILES ({Object.keys(filesMap).length})
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {Object.entries(filesMap).map(([path, chunks]) => (
                  <div
                    key={path}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 10px',
                      borderRadius: '4px',
                      background: 'rgba(255, 255, 255, 0.01)',
                      border: '1px solid rgba(255, 255, 255, 0.03)'
                    }}
                  >
                    <FileCode size={13} style={{ color: 'var(--accent-cyan)' }} />
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      <span style={{ fontSize: '12px', color: '#fff', fontWeight: 500, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                        {path.split('/').pop()}
                      </span>
                      <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>
                        {path} • {chunks.length} {chunks.length === 1 ? 'chunk' : 'chunks'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Results chunks list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {results.map((hit, idx) => (
                <div key={hit.id} className="glass-panel" style={{ padding: '20px' }}>
                  
                  {/* Meta header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--panel-border)', paddingBottom: '12px', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '11px', background: 'rgba(192, 193, 255, 0.1)', color: 'var(--accent-cyan)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                          #{idx + 1}
                        </span>
                        <h4 style={{ fontSize: '14px', color: '#fff', fontWeight: 600 }}>{hit.payload.filename}</h4>
                      </div>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {hit.payload.relative_path} : L{hit.payload.start_line}-L{hit.payload.end_line}
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        onClick={() => handleCopy(hit.id, hit.payload.text)}
                        style={{
                          background: 'rgba(255, 255, 255, 0.02)',
                          border: '1px solid var(--panel-border)',
                          borderRadius: '4px',
                          padding: '6px',
                          color: 'var(--text-secondary)',
                          cursor: 'pointer'
                        }}
                        title="Copy Code Chunk"
                      >
                        {copiedId === hit.id ? <Check size={13} style={{ color: 'var(--color-safe)' }} /> : <Copy size={13} />}
                      </button>
                    </div>
                  </div>

                  {/* Similarity scores block */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', background: 'rgba(255, 255, 255, 0.01)', border: '1px solid var(--panel-border)', borderRadius: '6px', padding: '12px 16px', marginBottom: '16px' }}>
                    
                    <div>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>
                        <Award size={10} /> HEURISTIC SCORE
                      </span>
                      <p className="font-mono" style={{ fontSize: '14px', color: 'var(--accent-cyan)', fontWeight: 700, marginTop: '2px' }}>
                        {(hit.ranking_score ?? hit.score ?? 0.0).toFixed(4)}
                      </p>
                    </div>

                    <div>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>
                        <Award size={10} /> SEMANTIC SIMILARITY
                      </span>
                      <p className="font-mono" style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: 600, marginTop: '2px' }}>
                        {hit.score.toFixed(4)}
                      </p>
                    </div>

                    <div>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>
                        <MessageSquare size={10} /> REASON
                      </span>
                      <p style={{ fontSize: '12px', color: '#fff', fontWeight: 500, marginTop: '2px' }}>
                        {hit.retrieval_reason || 'Semantic Similarity'}
                      </p>
                    </div>

                    <div>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>
                        <Tag size={10} /> LANGUAGE
                      </span>
                      <p className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 500, marginTop: '2px' }}>
                        {(hit.payload.language || 'unknown').toUpperCase()}
                      </p>
                    </div>

                  </div>

                  {/* Code viewport */}
                  <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '6px', overflow: 'hidden' }}>
                    <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '6px 16px', borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {hit.payload.relative_path}
                      </span>
                      <span style={{ fontSize: '9px', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                        {hit.payload.kind || 'source'}
                      </span>
                    </div>
                    <pre style={{ margin: 0, padding: '16px', overflowX: 'auto', maxHeight: '300px' }} className="font-mono">
                      <code style={{ fontSize: '11px', color: '#a7a4cf', lineHeight: 1.5 }}>
                        {hit.payload.text}
                      </code>
                    </pre>
                  </div>

                </div>
              ))}
            </div>

          </div>
        )}
      </div>
    </div>
  );
};

export default SearchRepository;
