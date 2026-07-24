import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { triggerDeployment } from '../api/dashboard';
import { getDecision } from '../api/deployments';
import { isFinalDecision, type PendingDecisionResponse } from '../api/types';
import { 
  Terminal, 
  Play, 
  Loader2
} from 'lucide-react';
import './Dashboard.css'; // Reuse CSS configurations

const POLL_INTERVAL_MS = 2_000;
const POLL_TIMEOUT_MS = 60_000;

export const WebhookSimulator: React.FC = () => {
  const navigate = useNavigate();

  // Form Fields
  const [repository, setRepository] = useState('shriza1991/DeployGuard');
  const [branch, setBranch] = useState('main');
  const [commitSha, setCommitSha] = useState('');
  const [author, setAuthor] = useState('sre-lead');
  const [prTitle, setPrTitle] = useState('');
  const [prBody, setPrBody] = useState('');
  const [commitMsg, setCommitMsg] = useState('');

  // Simulation state
  const [activeCorrelationId, setActiveCorrelationId] = useState<string | null>(null);
  const [collectedAgents, setCollectedAgents] = useState<string[]>([]);
  const [pipelineComplete, setPipelineComplete] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Sample Presets Loaders
  const loadPreset = (type: 'safe' | 'medium' | 'critical') => {
    if (type === 'safe') {
      setRepository('shriza1991/DeployGuard');
      setBranch('patch-documentation-links');
      setCommitSha('e4b3c9aef10022ff');
      setAuthor('docs-bot');
      setPrTitle('docs: update deployment guidelines and README instructions');
      setPrBody('Only changes style assets, markdown contents, and local navigation helper text in dashboard guide.');
      setCommitMsg('docs: align markdown styling with styling guides');
    } else if (type === 'medium') {
      setRepository('shriza1991/DeployGuard');
      setBranch('feature/catalog-queries-v2');
      setCommitSha('b8c4d21eab99ff22');
      setAuthor('developer');
      setPrTitle('feat: add index keys to relational product tables');
      setPrBody('Adding database queries and changing backend SQL schema to improve lookup execution times.');
      setCommitMsg('feat: deploy database migration rules');
    } else if (type === 'critical') {
      setRepository('shriza1991/DeployGuard');
      setBranch('hotfix/bypass-verification');
      setCommitSha('c1a2b3c4d5e6f7a8');
      setAuthor('security-admin');
      setPrTitle('hotfix: disable security policies temporarily');
      setPrBody('Adds root privileged securityContext in Kubernetes YAML configurations to allow catalog daemon to bind directly.');
      setCommitMsg('security: override container privileges on production namespace');
    }
  };

  // --- Mutation ---
  const triggerMutation = useMutation({
    mutationFn: triggerDeployment,
    onSuccess: (data) => {
      const cid = data.correlation_id ?? null;
      setActiveCorrelationId(cid);
      setCollectedAgents([]);
      setPipelineComplete(false);
      setStatusMsg('Webhook received by Gateway. Streaming event to Kafka...');
    },
  });

  const handleSendWebhook = (e: React.FormEvent) => {
    e.preventDefault();
    triggerMutation.mutate({
      repository,
      pullRequestTitle: prTitle,
      pullRequestBody: prBody,
      commitMessage: commitMsg,
      author,
    });
  };

  // --- Polling Logic ---
  useEffect(() => {
    if (!activeCorrelationId || pipelineComplete) return;

    const startTime = Date.now();

    const poll = async () => {
      if (Date.now() - startTime > POLL_TIMEOUT_MS) {
        setStatusMsg('Security evaluation timed out.');
        setActiveCorrelationId(null);
        return;
      }

      try {
        const result = await getDecision(activeCorrelationId);
        
        if (result.status === 202) {
          // In progress
          const pendingData = result.data as PendingDecisionResponse;
          const agents = pendingData.collected_agents || [];
          setCollectedAgents(agents);
          setStatusMsg(`Analysis active. Collected agents: ${agents.join(', ') || 'none yet'}`);
        } else if (result.status === 200 && isFinalDecision(result.data)) {
          // Final decision complete
          setPipelineComplete(true);
          setCollectedAgents(['code-risk', 'infra-risk', 'incident-history']);
          setStatusMsg(`Risk evaluation completed successfully. Decision: ${result.data.decision}. Redirecting...`);
          
          // Delayed navigate so user can see completion
          setTimeout(() => {
            navigate(`/deployments/${activeCorrelationId}`);
          }, 2000);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [activeCorrelationId, pipelineComplete, navigate]);

  return (
    <div className="dashboard-container fade-in" style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '48px' }}>
      
      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '24px' }}>
        <div className="dashboard-header-left">
          <div className="title-area" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={24} className="text-indigo" />
            <h1>Deployment Webhook Simulator</h1>
          </div>
          <p className="description">
            Submit a custom pull request webhook event payload to trigger risk gate bots.
          </p>
        </div>
      </div>

      {/* Preset buttons */}
      <div className="glass-panel" style={{ padding: '16px', marginBottom: '24px' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">LOAD SAMPLE PRESET TEMPLATES:</span>
        <div style={{ display: 'flex', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
          <button onClick={() => loadPreset('safe')} className="btn-secondary-stitch font-mono" style={{ borderColor: 'rgba(78, 222, 163, 0.3)', color: 'var(--color-safe)' }}>
            🟢 Load Safe Preset
          </button>
          <button onClick={() => loadPreset('medium')} className="btn-secondary-stitch font-mono" style={{ borderColor: 'rgba(255, 185, 95, 0.3)', color: 'var(--color-review)' }}>
            🟡 Load Warning Preset
          </button>
          <button onClick={() => loadPreset('critical')} className="btn-secondary-stitch font-mono" style={{ borderColor: 'rgba(255, 180, 171, 0.3)', color: 'var(--color-block)' }}>
            🔴 Load Critical Preset
          </button>
        </div>
      </div>

      {/* Form */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <form onSubmit={handleSendWebhook} className="simulator-form" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group font-mono">
              <label>Target Repository</label>
              <input
                type="text"
                value={repository}
                onChange={e => setRepository(e.target.value)}
                required
              />
            </div>
            <div className="form-group font-mono">
              <label>Target Branch</label>
              <input
                type="text"
                value={branch}
                onChange={e => setBranch(e.target.value)}
                required
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group font-mono">
              <label>Commit SHA</label>
              <input
                type="text"
                value={commitSha}
                onChange={e => setCommitSha(e.target.value)}
                placeholder="Auto-generated if empty"
              />
            </div>
            <div className="form-group font-mono">
              <label>Author / Sender</label>
              <input
                type="text"
                value={author}
                onChange={e => setAuthor(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group font-mono">
            <label>Pull Request Title</label>
            <input
              type="text"
              value={prTitle}
              onChange={e => setPrTitle(e.target.value)}
              required
            />
          </div>

          <div className="form-group font-mono">
            <label>PR Description</label>
            <textarea
              rows={3}
              value={prBody}
              onChange={e => setPrBody(e.target.value)}
              required
            />
          </div>

          <div className="form-group font-mono">
            <label>Commit Message</label>
            <input
              type="text"
              value={commitMsg}
              onChange={e => setCommitMsg(e.target.value)}
              required
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary-stitch font-mono" 
            style={{ width: '100%', justifyContent: 'center', minHeight: '42px', marginTop: '8px' }}
            disabled={triggerMutation.isPending || activeCorrelationId !== null}
          >
            {triggerMutation.isPending ? (
              <>
                <Loader2 className="spin" size={16} />
                <span>Triggering Webhook Ingress...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Send GitHub Webhook Push Event</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Active Pipeline Status Progress tracker */}
      {activeCorrelationId && (
        <div className="glass-panel" style={{ padding: '24px', marginTop: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '14px', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={14} className="text-indigo" />
              <span>Pipeline Audit Track: {activeCorrelationId.substring(0, 12)}...</span>
            </h3>
            <Loader2 className="spin text-indigo" size={14} />
          </div>

          <p className="font-mono" style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '10px', borderRadius: '4px', borderLeft: '3px solid var(--accent-blue)', marginBottom: '20px' }}>
            {statusMsg}
          </p>

          {/* Chronological stage bars progress */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Webhook Ingress</span>
              <span className="font-mono text-green" style={{ fontWeight: 'bold' }}>✓ Dispatched</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Gateway Proxy Gate</span>
              <span className="font-mono text-green" style={{ fontWeight: 'bold' }}>✓ Received</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Kafka Message Queueing</span>
              <span className="font-mono text-green" style={{ fontWeight: 'bold' }}>✓ Dispatched</span>
            </div>
            
            {/* Code Risk agent evaluation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Code Risk Agent evaluation</span>
              <span className="font-mono" style={{ color: collectedAgents.includes('code-risk') ? 'var(--color-safe)' : 'var(--text-muted)', fontWeight: 'bold' }}>
                {collectedAgents.includes('code-risk') ? '✓ Completed' : '⌛ Evaluating'}
              </span>
            </div>
            
            {/* Infra Risk Agent evaluation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Infrastructure Drift scanner</span>
              <span className="font-mono" style={{ color: collectedAgents.includes('infra-risk') ? 'var(--color-safe)' : 'var(--text-muted)', fontWeight: 'bold' }}>
                {collectedAgents.includes('infra-risk') ? '✓ Completed' : '⌛ Evaluating'}
              </span>
            </div>

            {/* Incident History agent evaluation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Regression Analyzer database check</span>
              <span className="font-mono" style={{ color: collectedAgents.includes('incident-history') ? 'var(--color-safe)' : 'var(--text-muted)', fontWeight: 'bold' }}>
                {collectedAgents.includes('incident-history') ? '✓ Completed' : '⌛ Evaluating'}
              </span>
            </div>

            {/* Aggregator */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
              <span>Decision Aggregator synthesis</span>
              <span className="font-mono" style={{ color: pipelineComplete ? 'var(--color-safe)' : 'var(--text-muted)', fontWeight: 'bold' }}>
                {pipelineComplete ? '✓ Safe Gate Verdict' : '⌛ Processing'}
              </span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
export default WebhookSimulator;
