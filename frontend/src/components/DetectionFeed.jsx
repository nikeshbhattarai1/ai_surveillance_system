import ConfidenceBar from './ConfidenceBar';

const EVENT_COLOR = {
  violence: 'var(--red-critical)',
  anomaly: 'var(--amber-warn)',
  intrusion: 'var(--amber-warn)',
  fire: 'var(--red-critical)',
  normal: 'var(--blue-clear)',
};

export default function DetectionFeed({ liveEvents = [] }) {
  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>DETECTION FEED</span>
        <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
          LIVE · {liveEvents.length} EVENTS
        </span>
      </div>
      <div style={styles.list}>
        {liveEvents.length === 0 && (
          <div style={styles.empty}>
            <span style={{ color: 'var(--text-dim)', letterSpacing: '0.1em', fontSize: 11 }}>
              AWAITING EVENTS...
            </span>
          </div>
        )}
        {[...liveEvents].reverse().map((evt, i) => (
          <EventRow key={`${evt.frame_id}-${i}`} evt={evt} isNew={i === 0} />
        ))}
      </div>
    </div>
  );
}

function EventRow({ evt, isNew }) {
  const color = EVENT_COLOR[evt.event_type] || 'var(--text-secondary)';
  const time = new Date().toLocaleTimeString('en-US', { hour12: false });
  return (
    <div style={{
      ...styles.row, borderLeftColor: color,
      animation: isNew ? 'slide-in-right 0.25s ease-out' : 'none',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{
          fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700,
          color, letterSpacing: '0.1em',
        }}>
          {evt.event_type?.toUpperCase() ?? 'UNKNOWN'}
        </span>
        <span style={{ color: 'var(--text-dim)', fontSize: 10 }}>
          {time} · FRM {String(evt.frame_id).padStart(6, '0')}
        </span>
      </div>
      <ConfidenceBar confidence={evt.confidence} label={evt.event_type} />
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
  title: {
    fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700, letterSpacing: '0.15em',
  },
  list: { overflowY: 'auto', flex: 1, padding: '8px 0' },
  empty: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: 120 },
  row: {
    padding: '10px 16px', borderLeft: '2px solid', marginLeft: 8, marginBottom: 2,
    background: 'var(--bg-raised)', transition: 'background 0.2s', cursor: 'default',
  },
};