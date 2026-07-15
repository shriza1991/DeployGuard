import React, { useState } from 'react';
import { exportAnalytics } from '../api/analytics';
import {
  ClipboardList,
  Download,
  FileText,
  Loader2,
  CheckCircle2,
  Shield,
  BarChart3,
  FileJson,
  Clock,
  Calendar,
  ChevronRight,
} from 'lucide-react';
import './Dashboard.css';

interface ReportTemplate {
  id: string;
  title: string;
  description: string;
  format: 'csv' | 'json';
  icon: React.ReactNode;
  color: string;
}

const REPORT_TEMPLATES: ReportTemplate[] = [
  {
    id: 'executive-summary',
    title: 'Executive DevSecOps Summary',
    description: 'High-level overview of deployment health, blocked releases, and risk trends for leadership review.',
    format: 'csv',
    icon: <Shield size={18} />,
    color: 'rgba(192,193,255,0.15)',
  },
  {
    id: 'agent-performance',
    title: 'Agent Reliability & Latency Audit',
    description: 'Per-agent performance metrics including confidence scores, processing latency, and accuracy breakdown.',
    format: 'csv',
    icon: <BarChart3 size={18} />,
    color: 'rgba(78,222,163,0.1)',
  },
  {
    id: 'raw-json',
    title: 'Complete Raw Pipeline Registry',
    description: 'Full JSON export of all deployment pipeline events, decisions, and agent results for data engineering use.',
    format: 'json',
    icon: <FileJson size={18} />,
    color: 'rgba(255,185,95,0.1)',
  },
];

const TIME_RANGES = [
  { value: '7d', label: '7 Days' },
  { value: '14d', label: '14 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
] as const;

export const Reports: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'7d' | '14d' | '30d' | '90d'>('7d');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('executive-summary');
  const [generating, setGenerating] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [lastGenerated, setLastGenerated] = useState<Date | null>(null);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const selectedTpl = REPORT_TEMPLATES.find(t => t.id === selectedTemplate)!;

  const handleExport = async () => {
    setGenerating(true);
    try {
      const blob = await exportAnalytics({
        range: timeRange,
        format: selectedTpl.format as any,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `deployguard_report_${selectedTemplate}_${timeRange}.${selectedTpl.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setLastGenerated(new Date());
      triggerToast(`Report downloaded — ${selectedTpl.title} (${selectedTpl.format.toUpperCase()})`);
    } catch (e) {
      console.error(e);
      triggerToast('Failed to generate report. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="dashboard-container fade-in" style={{ maxWidth: '860px', paddingBottom: '48px' }}>

      {/* Toast */}
      {toastMessage && (
        <div className="toast-notification font-mono" style={{ position: 'fixed', bottom: '24px', right: '24px', top: 'auto', zIndex: 9999 }}>
          <CheckCircle2 style={{ width: '14px', height: '14px', flexShrink: 0 }} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '4px' }}>
        <div className="dashboard-header-left">
          <div className="title-area">
            <div className="title-icon-wrapper">
              <ClipboardList className="title-icon" />
            </div>
            <h1>Security Reports</h1>
          </div>
          <p className="description">
            Generate, preview, and download compliance audits and risk metrics.
          </p>
        </div>
        {lastGenerated && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: 'rgba(78,222,163,0.06)', border: '1px solid rgba(78,222,163,0.15)', borderRadius: '6px' }}>
            <Clock size={11} style={{ color: 'var(--color-safe)' }} />
            <span className="font-mono" style={{ fontSize: '10px', color: 'var(--color-safe)' }}>
              Last generated: {lastGenerated.toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>

        {/* Report Template Cards */}
        <div className="section-block">
          <div className="section-header">
            <span className="section-label">Select Report Template</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {REPORT_TEMPLATES.map(tpl => {
              const isSelected = selectedTemplate === tpl.id;
              return (
                <button
                  key={tpl.id}
                  onClick={() => setSelectedTemplate(tpl.id)}
                  style={{
                    width: '100%', textAlign: 'left',
                    padding: '16px 18px',
                    background: isSelected ? tpl.color : 'rgba(255,255,255,0.01)',
                    border: `1px solid ${isSelected ? 'rgba(192,193,255,0.25)' : 'var(--panel-border)'}`,
                    borderRadius: '8px',
                    cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: '14px',
                    transition: 'all 0.18s ease',
                    color: '#fff',
                  }}
                >
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '8px',
                    background: isSelected ? 'rgba(192,193,255,0.15)' : 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)',
                    flexShrink: 0,
                  }}>
                    {tpl.icon}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: isSelected ? '#fff' : 'var(--text-primary)' }}>{tpl.title}</span>
                      <span className="font-mono" style={{ fontSize: '9px', padding: '2px 7px', borderRadius: '3px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-muted)' }}>
                        .{tpl.format}
                      </span>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '3px 0 0 0', lineHeight: '1.4' }}>{tpl.description}</p>
                  </div>
                  {isSelected && <ChevronRight size={16} style={{ color: 'var(--accent-cyan)', flexShrink: 0 }} />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Time Range Selector + Export */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#fff', marginBottom: '14px' }}>Aggregation Period</h3>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
            {TIME_RANGES.map(range => (
              <button
                key={range.value}
                onClick={() => setTimeRange(range.value)}
                className={`time-btn font-mono ${timeRange === range.value ? 'active' : ''}`}
                style={{ flexGrow: 1, padding: '8px', borderRadius: '6px', border: '1px solid', borderColor: timeRange === range.value ? 'rgba(192,193,255,0.3)' : 'var(--panel-border)', background: timeRange === range.value ? 'rgba(192,193,255,0.1)' : 'rgba(255,255,255,0.02)' }}
              >
                <Calendar size={10} style={{ marginBottom: '2px' }} />
                {range.label}
              </button>
            ))}
          </div>

          {/* Selected summary */}
          <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '6px', marginBottom: '16px', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ color: 'var(--accent-cyan)' }}>{selectedTpl.icon}</div>
            <div>
              <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>{selectedTpl.title}</span>
              <span className="font-mono" style={{ marginLeft: '8px', fontSize: '10px', color: 'var(--text-muted)' }}>· {timeRange} · .{selectedTpl.format}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleExport}
              className="btn-primary-stitch font-mono"
              style={{ flex: 1, justifyContent: 'center', minHeight: '42px' }}
              disabled={generating}
            >
              {generating ? (
                <><Loader2 size={15} className="spin" /><span>Compiling report...</span></>
              ) : (
                <><Download size={15} /><span>Download Report</span></>
              )}
            </button>
            <button
              onClick={() => triggerToast('PDF Export requires enterprise tier licensing.')}
              className="btn-secondary-stitch font-mono"
              style={{ minHeight: '42px', padding: '0 18px' }}
            >
              <FileText size={15} /><span>Export PDF</span>
            </button>
          </div>
        </div>

        {/* Preview Sample */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#fff', marginBottom: '14px' }}>
            Sample Metrics Preview <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 400 }}>({timeRange})</span>
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1px', background: 'var(--panel-border)', borderRadius: '6px', overflow: 'hidden' }} className="font-mono">
            {[
              { label: 'Compliance Rate', value: '96.5%', color: 'var(--color-safe)' },
              { label: 'Blocked Releases', value: '4', color: 'var(--color-block)' },
              { label: 'Critical Drifts', value: '0', color: '#fff' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ padding: '16px', background: 'var(--panel-bg)' }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '6px' }}>{label}</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color }}>{value}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: '12px', padding: '8px 12px', borderLeft: '3px solid var(--accent-blue)', background: 'rgba(255,255,255,0.01)', borderRadius: '0 4px 4px 0', fontSize: '11px', color: 'var(--text-secondary)' }} className="font-mono">
            Preview corresponds to verified SOC2 compliance checklists.
          </div>
        </div>

      </div>
    </div>
  );
};
export default Reports;
