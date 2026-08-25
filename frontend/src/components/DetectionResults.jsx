const STATUS_COLOR = {
  threat: 'var(--red-critical)',
  clear: 'var(--green-threat)',
  idle: 'var(--text-dim)',
};

const MONITORING_COLOR = {
  active: 'var(--blue-clear)',
  complete: 'var(--blue-clear)',
  idle: 'var(--text-dim)',
};

export default function DetectionResults({
  isThreat,        // boolean | null  (null = no data yet)
  label,           // e.g. 'violence', 'normal'
  streamSource,    // e.g. 'Live CCTV Feed', 'Webcam', 'Uploaded Video'
  monitoringStatus // e.g. 'Active', 'Analysis Complete', 'Idle'
}) {
  const hasResult = isThreat !== null && isThreat !== undefined;

  const statusText = !hasResult
    ? 'No Data'
    : isThreat
      ? `${(label || 'Violence').toUpperCase()} DETECTED`
      : 'No Violence Detected';

  const statusColor = !hasResult
    ? STATUS_COLOR.idle
    : isThreat
      ? STATUS_COLOR.threat
      : STATUS_COLOR.clear;

  const monitorKey = (monitoringStatus || '').toLowerCase().includes('active')
    ? 'active'
    : (monitoringStatus || '').toLowerCase().includes('complete')
      ? 'complete'
      : 'idle';

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>DETECTION RESULTS</span>
      </div>

      <Row label="STATUS" value={statusText} valueColor={statusColor} />
      <Row label="STREAM SOURCE" value={streamSource || '—'} valueColor="var(--text-primary)" />
      <Row
        label="MONITORING STATUS"
        value={monitoringStatus || 'Idle'}
        valueColor={MONITORING_COLOR[monitorKey]}
      />
    </div>
  );
}

function Row({ label, value, valueColor }) {
  return (
    <div style={styles.row}>
      <div style={styles.rowLabel}>{label}:</div>
      <div style={{ ...styles.rowValue, color: valueColor }}>{value}</div>
    </div>
  );
}

const styles = {
  panel: {
    background: 'var(--bg-panel)', border: '1px solid var(--bg-border)',
    display: 'flex', flexDirection: 'column', gap: 1,
  },
  header: {
    padding: '12px 16px', borderBottom: '1px solid var(--bg-border)',
  },
  title: {
    fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700,
    letterSpacing: '0.15em', color: 'var(--text-primary)',
  },
  row: {
    padding: '14px 16px', background: 'var(--bg-raised)',
    borderBottom: '1px solid var(--bg-border)',
  },
  rowLabel: {
    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
    letterSpacing: '0.12em', color: 'var(--text-dim)', marginBottom: 6,
  },
  rowValue: {
    fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 700,
    letterSpacing: '0.05em',
  },
};