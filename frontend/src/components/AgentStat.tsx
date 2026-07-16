import React from 'react';

interface AgentStatProps {
  label: string;
  value: React.ReactNode;
}

export const AgentStat: React.FC<AgentStatProps> = ({ label, value }) => {
  return (
    <div>
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      <p className="font-mono" style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold', marginTop: '2px' }}>
        {value !== undefined && value !== null && value !== '' ? value : '--'}
      </p>
    </div>
  );
};

export default AgentStat;
