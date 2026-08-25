export default function ConfidenceBar({ confidence = 0, label = 'normal' }) {
  const pct = Math.round(confidence * 100);
  const isThreat = label !== 'normal';
  const color = isThreat
    ? confidence > 0.85 ? 'var(--red-critical)' : 'var(--amber-warn)'
    : 'var(--blue-clear)';

  return (
    <div style={{ width: '100%' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', marginBottom: 4,
        fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)',
      }}>
        <span style={{ color, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{label}</span>
        <span style={{ color }}>{pct}%</span>
      </div>
      <div style={{ height: 3, background: 'var(--bg-border)', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct}%`,
          background: color,
          boxShadow: `0 0 8px ${color}`,
          transition: 'width 0.4s cubic-bezier(0.4,0,0.2,1)',
        }} />
      </div>
    </div>
  );
}