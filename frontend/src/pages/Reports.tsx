import React, { useState } from 'react';
import { exportAnalytics } from '../api/analytics';
import { 
  ClipboardList, 
  Download, 
  FileText, 
  Loader2, 
  CheckCircle2
} from 'lucide-react';
import './Dashboard.css';

export const Reports: React.FC = () => {
  const [timeRange, setTimeRange] = useState<'7d' | '14d' | '30d' | '90d'>('7d');
  const [reportType, setReportType] = useState<string>('executive-summary');
  const [generating, setGenerating] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleExport = async () => {
    setGenerating(true);
    try {
      const format = reportType === 'raw-json' ? 'json' : 'csv';
      const blob = await exportAnalytics({
        range: timeRange,
        format: format as any
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `deployguard_report_${reportType}_${timeRange}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      triggerToast(`Report downloaded successfully in ${format.toUpperCase()} format!`);
    } catch (e) {
      console.error(e);
      triggerToast("Failed to generate and export report file.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="dashboard-container fade-in" style={{ maxWidth: '800px', margin: '0 auto', paddingBottom: '48px' }}>
      
      {/* Toast */}
      {toastMessage && (
        <div className="toast-notification font-mono">
          <CheckCircle2 className="toast-icon text-green" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="dashboard-header-container" style={{ marginBottom: '24px' }}>
        <div className="dashboard-header-left">
          <div className="title-area" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ClipboardList size={24} className="text-indigo" />
            <h1>Security Reports Hub</h1>
          </div>
          <p className="description">
            Generate, preview, and download compliance audits and risk metrics.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
        
        {/* Report Builder configuration */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600, marginBottom: '16px' }}>Report Configurations</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* Type selector */}
            <div className="form-group font-mono">
              <label>Select Report Template</label>
              <select 
                value={reportType} 
                onChange={(e) => setReportType(e.target.value)}
                style={{ width: '100%', padding: '10px', background: 'var(--bg-secondary)', border: '1px solid var(--panel-border)', borderRadius: '6px', color: '#fff' }}
              >
                <option value="executive-summary">Executive DevSecOps Summary (CSV)</option>
                <option value="agent-performance">Agent Reliability &amp; Latency Audit (CSV)</option>
                <option value="raw-json">Complete Raw Pipeline Registry (JSON)</option>
              </select>
            </div>

            {/* Timeframe */}
            <div className="form-group font-mono">
              <label>Aggregation Period</label>
              <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                {(['7d', '14d', '30d', '90d'] as const).map((range) => (
                  <button
                    key={range}
                    type="button"
                    onClick={() => setTimeRange(range)}
                    className={`time-btn font-mono ${timeRange === range ? 'active' : ''}`}
                    style={{ flexGrow: 1, padding: '8px' }}
                  >
                    {range === '7d' ? '7 Days' : range === '14d' ? '14 Days' : range === '30d' ? '30 Days' : '90 Days'}
                  </button>
                ))}
              </div>
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
              <button 
                onClick={handleExport}
                className="btn-primary-stitch font-mono"
                style={{ flexGrow: 1, justifyContent: 'center', minHeight: '42px' }}
                disabled={generating}
              >
                {generating ? (
                  <>
                    <Loader2 className="spin" size={16} />
                    <span>Compiling database...</span>
                  </>
                ) : (
                  <>
                    <Download size={16} />
                    <span>Download Audit Report</span>
                  </>
                )}
              </button>
              
              <button 
                onClick={() => triggerToast("PDF Export requires licensing standard enterprise tier.")}
                className="btn-secondary-stitch font-mono"
                style={{ minHeight: '42px', padding: '0 16px' }}
              >
                <FileText size={16} />
                <span>Export PDF</span>
              </button>
            </div>

          </div>
        </div>

        {/* Report Preview simulation */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '15px', color: '#fff', fontWeight: 600, marginBottom: '12px' }}>Preview Sample Metrics ({timeRange})</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', border: '1px solid var(--panel-border)', borderRadius: '6px', overflow: 'hidden' }} className="font-mono">
            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.01)', borderRight: '1px solid var(--panel-border)' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>COMPLIANCE RATE</span>
              <p style={{ fontSize: '18px', color: 'var(--color-safe)', fontWeight: 'bold', marginTop: '4px' }}>96.5%</p>
            </div>
            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.01)', borderRight: '1px solid var(--panel-border)' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>BLOCKED RELEASES</span>
              <p style={{ fontSize: '18px', color: 'var(--color-block)', fontWeight: 'bold', marginTop: '4px' }}>4</p>
            </div>
            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.01)' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>CRITICAL DRIFTS</span>
              <p style={{ fontSize: '18px', color: '#fff', fontWeight: 'bold', marginTop: '4px' }}>0</p>
            </div>
          </div>
          
          <div style={{ marginTop: '16px', padding: '10px', borderLeft: '3px solid var(--accent-blue)', background: 'var(--bg-secondary)', fontSize: '11px', color: 'var(--text-secondary)' }} className="font-mono">
            <span>Security audit preview corresponds directly to verified SOC2 compliance checklists.</span>
          </div>
        </div>

      </div>

    </div>
  );
};
export default Reports;
