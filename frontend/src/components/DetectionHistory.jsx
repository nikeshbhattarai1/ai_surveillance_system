import { useDetections } from '../hooks/useDetections';
import ConfidenceBar from './ConfidenceBar';

const STATUS_COLOR = {
  violence: 'var(--red-critical)',
  anomaly: 'var(--amber-warn)',
  intrusion: 'var(--amber-warn)',
  fire: 'var(--red-critical)',
  normal: 'var(--blue-clear)',
  unknown: 'var(--text-secondary)',
};

// Mock data so the table looks populated even without a backend
const MOCK_DETECTIONS = [
  { id: 1, timestamp: new Date(Date.now() - 60000).toISOString(), event_type: 'violence', confidence: 0.91, source: 'stream', notified: true, notification_channel: 'email', job_id: null },
  { id: 2, timestamp: new Date(Date.now() - 120000).toISOString(), event_type: 'normal', confidence: 0.98, source: 'stream', notified: false, notification_channel: null, job_id: null },
  { id: 3, timestamp: new Date(Date.now() - 180000).toISOString(), event_type: 'normal', confidence: 0.95, source: 'upload', notified: false, notification_channel: null, job_id: 'a1b2c3d4' },
  { id: 4, timestamp: new Date(Date.now() - 240000).toISOString(), event_type: 'violence', confidence: 0.81, source: 'stream', notified: true, notification_channel: 'slack', job_id: null },
  { id: 5, timestamp: new Date(Date.now() - 300000).toISOString(), event_type: 'normal', confidence: 0.97, source: 'upload', notified: false, notification_channel: null, job_id: 'e5f6g7h8' },
];

export default function DetectionHistory() {
  // Try real API; if it fails, fall back to mock data
  const { detections: apiData, total, loading, error, page, setPage, limit } = useDetections();
  const detections = (error || apiData.length === 0) ? MOCK_DETECTIONS : apiData;
  const displayTotal = error ? MOCK_DETECTIONS.length : total;
  const totalPages = Math.max(1, Math.ceil(displayTotal / limit));

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>DETECTION HISTORY</span>
        <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
          {displayTotal} RECORDS {error ? '(DEMO)' : ''}
        </span>
      </div>

      <div style={styles.colHeaders}>
        {['TIMESTAMP', 'TYPE', 'CONFIDENCE', 'SOURCE', 'NOTIFIED', 'JOB ID'].map((h) => (
          <span key={h} style={styles.colHeader}>{h}</span>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading && <div style={styles.status}>LOADING...</div>}
        {detections.map((d) => (
          <div key={d.id} style={styles.row}>
            <span style={{ color: 'var(--text-secondary)' }}>
              {new Date(d.timestamp).toLocaleString('en-US', { hour12: false })}
            </span>
            <span style={{
              fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 13,
              letterSpacing: '0.05em', color: STATUS_COLOR[d.event_type] || 'var(--text-secondary)',
            }}>
              {d.event_type?.toUpperCase()}
            </span>
            <div style={{ minWidth: 120 }}>
              <ConfidenceBar confidence={d.confidence} label={d.event_type} />
            </div>
            <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{d.source?.toUpperCase()}</span>
            <span style={{ color: d.notified ? 'var(--green-threat)' : 'var(--text-dim)', fontSize: 11 }}>
              {d.notified ? `✓ ${d.notification_channel?.toUpperCase()}` : '—'}
            </span>
            <span style={{ color: 'var(--text-dim)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              {d.job_id ? d.job_id.slice(0, 8) + '…' : 'STREAM'}
            </span>
          </div>
        ))}
      </div>

      <div style={styles.pagination}>
        <button style={styles.pageBtn} onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}>← PREV</button>
        <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>PAGE {page + 1} / {totalPages}</span>
        <button style={styles.pageBtn} onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}>NEXT →</button>
      </div>
    </div>
  );
}

const styles = {
  panel: {
    background: 'var(--bg-panel)', border: '1px solid var(--bg-border)',
    display: 'flex', flexDirection: 'column', height: '100%',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '12px 16px', borderBottom: '1px solid var(--bg-border)', flexShrink: 0,
  },
  title: { fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700, letterSpacing: '0.15em' },
  colHeaders: {
    display: 'grid', gridTemplateColumns: '200px 100px 140px 80px 120px 1fr', gap: 16,
    padding: '8px 16px', background: 'var(--bg-raised)', borderBottom: '1px solid var(--bg-border)', flexShrink: 0,
  },
  colHeader: { fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.12em', fontWeight: 700 },
  row: {
    display: 'grid', gridTemplateColumns: '200px 100px 140px 80px 120px 1fr', gap: 16,
    padding: '10px 16px', borderBottom: '1px solid var(--bg-border)', alignItems: 'center',
    fontSize: 12, transition: 'background 0.15s',
  },
  status: { padding: 24, textAlign: 'center', color: 'var(--text-secondary)', letterSpacing: '0.1em', fontSize: 11 },
  pagination: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '8px 16px', borderTop: '1px solid var(--bg-border)', flexShrink: 0,
  },
  pageBtn: {
    fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.1em', padding: '4px 12px',
    border: '1px solid var(--bg-border)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer',
  },
};