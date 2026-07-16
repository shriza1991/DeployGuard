import React from 'react';

interface HealthIndicatorProps {
  status: 'online' | 'degraded' | 'offline' | 'unknown' | 'healthy' | 'unhealthy' | string;
  label?: string;
  pulse?: boolean;
  type?: 'chip' | 'badge';
}

export const HealthIndicator: React.FC<HealthIndicatorProps> = ({
  status,
  label,
  pulse = true,
  type = 'badge'
}) => {
  const norm = (status || '').toLowerCase();
  
  let resolvedStatus: 'online' | 'degraded' | 'offline' | 'unknown' = 'unknown';
  if (norm === 'online' || norm === 'healthy' || norm === 'ok') {
    resolvedStatus = 'online';
  } else if (norm === 'degraded' || norm === 'warning' || norm === 'review') {
    resolvedStatus = 'degraded';
  } else if (norm === 'offline' || norm === 'unhealthy' || norm === 'failed' || norm === 'block') {
    resolvedStatus = 'offline';
  }

  const displayLabel = label || resolvedStatus.toUpperCase();

  if (type === 'chip') {
    return (
      <div className={`system-status-chip ${resolvedStatus === 'online' ? 'online' : 'offline'}`}>
        <span className={`status-dot ${resolvedStatus === 'online' && pulse ? 'pulse' : ''}`} />
        <span>{displayLabel}</span>
      </div>
    );
  }

  return (
    <div className={`pipeline-status-badge status-${resolvedStatus}`}>
      <span className={`status-pip ${resolvedStatus}`} />
      <span>{displayLabel}</span>
    </div>
  );
};

export default HealthIndicator;
