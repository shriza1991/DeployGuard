import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface QuickActionCardProps {
  label: string;
  description: string;
  icon: LucideIcon;
  onClick: () => void;
  primary?: boolean;
}

export const QuickActionCard: React.FC<QuickActionCardProps> = ({
  label,
  description,
  icon: Icon,
  onClick,
  primary = false
}) => {
  const cardClass = primary
    ? 'quick-action-card quick-action-card--primary glass-panel'
    : 'quick-action-card quick-action-card--secondary glass-panel';

  return (
    <button className={cardClass} onClick={onClick} style={{
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      padding: '16px 20px',
      borderRadius: '8px',
      border: '1px solid var(--panel-border)',
      background: primary 
        ? 'linear-gradient(135deg, rgba(192, 193, 255, 0.12), rgba(192, 193, 255, 0.04))' 
        : 'rgba(255, 255, 255, 0.02)',
      cursor: 'pointer',
      textAlign: 'left',
      transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
      width: '100%',
      color: primary ? 'var(--accent-cyan)' : 'var(--text-primary)',
      outline: 'none',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '10px',
        borderRadius: '8px',
        background: primary ? 'rgba(192, 193, 255, 0.1)' : 'rgba(255, 255, 255, 0.02)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        color: primary ? 'var(--accent-cyan)' : 'var(--text-secondary)',
        flexShrink: 0
      }}>
        <Icon size={20} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <span style={{ fontSize: '14px', fontWeight: 600, letterSpacing: '-0.01em' }}>{label}</span>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{description}</span>
      </div>
    </button>
  );
};

export default QuickActionCard;
