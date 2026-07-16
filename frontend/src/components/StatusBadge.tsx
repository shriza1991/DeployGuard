import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'small' | 'medium';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'small' }) => {
  const norm = (status || '').trim().toUpperCase();
  let className = 'verdict-tag-small pending';
  
  if (norm === 'SAFE' || norm === 'ONLINE' || norm === 'HEALTHY') {
    className = 'verdict-tag-small safe';
  } else if (norm === 'BLOCK' || norm === 'OFFLINE' || norm === 'UNHEALTHY' || norm === 'FAILED') {
    className = 'verdict-tag-small block';
  } else if (norm === 'REVIEW' || norm === 'DEGRADED') {
    className = 'verdict-tag-small review';
  } else if (norm === 'PENDING' || norm === 'INDEXING') {
    className = 'verdict-tag-small pending';
  }

  const style: React.CSSProperties = size === 'medium' ? {
    padding: '6px 12px',
    fontSize: '11px',
  } : {};

  return (
    <span className={`${className} font-mono`} style={style}>
      {norm}
    </span>
  );
};

export default StatusBadge;
