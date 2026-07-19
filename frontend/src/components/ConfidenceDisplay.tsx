import React, { useState } from 'react';
import { ChevronDown, ChevronUp, CheckCircle2, ShieldCheck } from 'lucide-react';
import {
  normalizeConfidence,
  getConfidenceColor,
  getConfidenceLabel,
  getDefaultConfidenceFactors,
} from '../utils/confidence';

interface ConfidenceDisplayProps {
  value: number | null | undefined;
  factors?: string[];
  title?: string;
  showBreakdown?: boolean;
  compact?: boolean;
}

export const ConfidenceDisplay: React.FC<ConfidenceDisplayProps> = ({
  value,
  factors,
  title = 'Analysis Confidence',
  showBreakdown = false,
  compact = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const pct = normalizeConfidence(value);
  const color = getConfidenceColor(pct);
  const label = getConfidenceLabel(pct);

  const displayFactors =
    factors && factors.length > 0
      ? factors
      : getDefaultConfidenceFactors(pct);

  if (compact) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
        <div
          style={{
            width: '40px',
            height: '4px',
            borderRadius: '2px',
            background: 'rgba(255,255,255,0.1)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${pct ?? 0}%`,
              height: '100%',
              backgroundColor: color,
              borderRadius: '2px',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
        <span
          className="font-mono"
          style={{ fontSize: '12px', fontWeight: 600, color }}
        >
          {pct !== null ? `${pct}%` : '—'}
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '12px 16px',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid var(--panel-border)',
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheck size={14} style={{ color }} />
          <span
            style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}
          >
            {title}
          </span>
        </div>
        <span
          style={{
            fontSize: '10px',
            fontWeight: 600,
            color,
            padding: '2px 6px',
            borderRadius: '4px',
            background: `${color}15`,
            fontFamily: 'var(--font-mono)',
          }}
        >
          {label}
        </span>
      </div>

      {/* Main Percentage + Progress Bar */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
        <div
          className="font-mono"
          style={{
            fontSize: '24px',
            fontWeight: 700,
            color,
            lineHeight: 1,
          }}
        >
          {pct !== null ? `${pct}%` : '—'}
        </div>

        <div style={{ flex: 1 }}>
          <div
            style={{
              height: '6px',
              width: '100%',
              borderRadius: '3px',
              background: 'rgba(255,255,255,0.08)',
              overflow: 'hidden',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.3)',
            }}
          >
            <div
              style={{
                width: `${pct ?? 0}%`,
                height: '100%',
                backgroundColor: color,
                borderRadius: '3px',
                transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                boxShadow: `0 0 8px ${color}66`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Collapsible "Based on:" breakdown section */}
      {showBreakdown && (
        <div style={{ marginTop: '4px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '6px' }}>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              cursor: 'pointer',
              padding: '2px 0',
            }}
          >
            <span>Based on:</span>
            {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {isExpanded && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                marginTop: '6px',
                paddingLeft: '2px',
              }}
            >
              {displayFactors.map((factor, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11px',
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <CheckCircle2 size={12} style={{ color, flexShrink: 0 }} />
                  <span>{factor}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
