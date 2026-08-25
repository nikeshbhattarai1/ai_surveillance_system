import { useState } from 'react';
import CameraFeed from '../components/CameraFeed';
import DetectionFeed from '../components/DetectionFeed';

const MAX_LIVE_EVENTS = 50;

export default function LiveFeed() {
  const [liveEvents, setLiveEvents] = useState([]);
  const [threatCount, setThreatCount] = useState(0);

  const handleDetection = (evt) => {
    setLiveEvents((prev) => [...prev, evt].slice(-MAX_LIVE_EVENTS));
    setThreatCount((n) => n + 1);
  };

  return (
    <div style={styles.root}>
      <div style={styles.statsBar}>
        <Stat label="THREATS" value={threatCount} accent="var(--red-critical)" blink={threatCount > 0} />
        <Stat label="STATUS" value="ONLINE" accent="var(--green-threat)" />
        <Stat label="MODEL" value="3D-CNN" accent="var(--blue-clear)" />
      </div>

      <div style={styles.grid}>
        <div style={styles.leftCol}>
          <CameraFeed onDetection={handleDetection} />
        </div>
        <div style={styles.rightCol}>
          <DetectionFeed liveEvents={liveEvents} />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent, blink }) {
  return (
    <div style={{ textAlign: 'right' }}>
      <div style={{
        fontSize: 9,
        color: 'var(--text-dim)',
        letterSpacing: '0.15em',
        marginBottom: 2,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontSize: 16,
        fontWeight: 700,
        color: accent,
        letterSpacing: '0.1em',
        animation: blink ? 'pulse-red 1s infinite' : 'none',
      }}>
        {value}
      </div>
    </div>
  );
}

const styles = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflow: 'hidden',
  },
  statsBar: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 32,
    padding: '8px 20px',
    borderBottom: '1px solid var(--bg-border)',
    background: 'var(--bg-panel)',
    flexShrink: 0,
  },
  grid: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: '650px 1fr',
    gap: 1,
    background: 'var(--bg-border)',
    overflow: 'hidden',
  },
  leftCol: {
    overflowY: 'auto',
    background: 'var(--bg-void)',
  },
  rightCol: {
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
};