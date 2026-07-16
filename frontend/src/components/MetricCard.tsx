import React from 'react';

interface MetricCardProps {
  title: string;
  value: React.ReactNode;
  subtitle: string;
  type?: 'neutral' | 'danger' | 'warn' | 'safe';
  progress?: number; // 0 to 100
  progressColor?: string;
  valueStyle?: React.CSSProperties;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  type = 'neutral',
  progress,
  progressColor,
  valueStyle
}) => {
  let cardClass = 'kpi-card glass-panel kpi-card--neutral';
  if (type === 'danger') cardClass = 'kpi-card glass-panel kpi-card--danger';
  else if (type === 'warn') cardClass = 'kpi-card glass-panel kpi-card--warn';
  else if (type === 'safe') cardClass = 'kpi-card glass-panel kpi-card--safe';

  return (
    <div className={cardClass}>
      <span className="kpi-title">{title}</span>
      <div className="kpi-value font-mono" style={valueStyle}>
        {value}
      </div>
      {progress !== undefined && (
        <div className="kpi-progress-bar">
          <div
            className="kpi-progress-fill"
            style={{
              width: `${Math.min(100, Math.max(0, progress))}%`,
              background: progressColor || 'var(--color-safe)'
            }}
          />
        </div>
      )}
      <p className="kpi-sub">{subtitle}</p>
    </div>
  );
};

export default MetricCard;
