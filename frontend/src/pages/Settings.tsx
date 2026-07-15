import React, { useState } from 'react';
import { Settings as SettingsIcon, Sliders, Bell, Eye, Save } from 'lucide-react';
import './Dashboard.css';

export const Settings: React.FC = () => {
  const [blockThreshold, setBlockThreshold] = useState(60);
  const [reviewThreshold, setReviewThreshold] = useState(30);
  const [agentTimeout, setAgentTimeout] = useState(5.0);
  const [enableSlack, setEnableSlack] = useState(true);
  const [slackWebhook, setSlackWebhook] = useState('');
  const [enableEmail, setEnableEmail] = useState(false);
  const [themeMode, setThemeMode] = useState('glass-dark');

  // UI state
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveStatus(null);
    setTimeout(() => {
      setSaving(false);
      setSaveStatus("System configurations saved successfully!");
      setTimeout(() => setSaveStatus(null), 3000);
    }, 1000);
  };

  return (
    <div className="dashboard-container fade-in" style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '48px' }}>

      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '24px' }}>
        <div className="dashboard-header-left">
          <div className="title-area" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SettingsIcon size={24} className="text-indigo" />
            <h1>Settings &amp; Policies</h1>
          </div>
          <p className="description">
            Configure risk thresholds, notifications routing, and telemetry rules.
          </p>
        </div>
      </div>

      <form onSubmit={handleSaveSettings} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

        {/* Risk Threshold Limits */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Sliders size={18} className="text-indigo" />
            <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600 }}>Decisions Risk Thresholds</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }} className="font-mono">

            {/* Auto Block Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>BLOCK VERDICT THRESHOLD LIMIT</label>
                <span style={{ color: 'var(--color-block)', fontWeight: 'bold' }}>&gt;= {blockThreshold} score</span>
              </div>
              <input
                type="range"
                min="50"
                max="90"
                value={blockThreshold}
                onChange={(e) => setBlockThreshold(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--color-block)' }}
              />
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Deployments with overall score equal or higher than this will trigger automatic pipeline cancellation.</p>
            </div>

            {/* Auto Review Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>REVIEW REQUIRED THRESHOLD LIMIT</label>
                <span style={{ color: 'var(--color-review)', fontWeight: 'bold' }}>&gt;= {reviewThreshold} score</span>
              </div>
              <input
                type="range"
                min="20"
                max="45"
                value={reviewThreshold}
                onChange={(e) => setReviewThreshold(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--color-review)' }}
              />
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>Deployments score higher than this value will require manual SRE approval flags.</p>
            </div>

            {/* Timeouts */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', borderTop: '1px solid var(--panel-border)', paddingTop: '20px', marginTop: '10px' }}>
              <div className="form-group">
                <label>AGENT TIMEOUT LIMIT (SEC)</label>
                <input
                  type="number"
                  step="0.5"
                  value={agentTimeout}
                  onChange={(e) => setAgentTimeout(Number(e.target.value))}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '4px', color: '#fff' }}
                />
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
                <span>Maximum wait time for distributed agents to report findings before decision aggregation defaults.</span>
              </div>
            </div>

          </div>
        </div>

        {/* Notifications routing */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Bell size={18} className="text-indigo" />
            <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600 }}>Notifications Routing</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} className="font-mono">
            {/* Slack Toggle */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '12px', color: '#fff' }}>Slack Integration Alerts</span>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Publish threat scorecards directly to incident response channel.</p>
              </div>
              <input
                type="checkbox"
                checked={enableSlack}
                onChange={(e) => setEnableSlack(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-blue)' }}
              />
            </div>

            {enableSlack && (
              <div className="form-group" style={{ paddingLeft: '16px' }}>
                <label style={{ fontSize: '10px' }}>SLACK INCOMING WEBHOOK URI</label>
                <input
                  type="text"
                  value={slackWebhook}
                  onChange={(e) => setSlackWebhook(e.target.value)}
                  style={{ width: '100%', padding: '8px', background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '4px', color: 'var(--text-secondary)' }}
                />
              </div>
            )}

            {/* Email reports */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--panel-border)', paddingTop: '16px' }}>
              <div>
                <span style={{ fontSize: '12px', color: '#fff' }}>Email Weekly Reports</span>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>Receive summary metrics PDF sheet in administration emails.</p>
              </div>
              <input
                type="checkbox"
                checked={enableEmail}
                onChange={(e) => setEnableEmail(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--accent-blue)' }}
              />
            </div>
          </div>
        </div>

        {/* Visual theme settings */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Eye size={18} className="text-indigo" />
            <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600 }}>Preferences</h3>
          </div>

          <div className="form-group font-mono">
            <label>Interface Theme Mode</label>
            <select
              value={themeMode}
              onChange={(e) => setThemeMode(e.target.value)}
              style={{ width: '100%', padding: '10px', background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '6px', color: '#fff' }}
            >
              <option value="glass-dark">Sophisticated Glassmorphism Dark (Recommended)</option>
              <option value="solid-dark">Solid Dark Matte Mode</option>
              <option value="light">Classic Light Mode (Standard placeholders)</option>
            </select>
          </div>
        </div>

        {/* Save button & status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            type="submit"
            className="btn-primary-stitch font-mono"
            style={{ padding: '12px 24px', fontSize: '13px' }}
            disabled={saving}
          >
            <Save size={16} />
            <span>{saving ? 'Saving...' : 'Apply Configurations'}</span>
          </button>

          {saveStatus && (
            <span style={{ fontSize: '13px', color: 'var(--color-safe)', fontWeight: 'bold' }} className="font-mono">
              ✓ {saveStatus}
            </span>
          )}
        </div>

      </form>
    </div>
  );
};
export default Settings;
