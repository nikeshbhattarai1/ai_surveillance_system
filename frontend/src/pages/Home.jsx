import { useNavigate } from 'react-router-dom';

export default function Home() {
  const navigate = useNavigate();

  return (
    <div style={styles.root}>
      <div style={styles.hero}>
        <div style={styles.heroContent}>
          <div style={styles.badge}>AI-POWERED · REAL-TIME · MULTI-THREAT</div>
          <h1 style={styles.title}>AI SURVEILLANCE<br />SYSTEM</h1>
          <p style={styles.subtitle}>
            Responsive crime monitoring and instant classification
            utilizing deep learning on live CCTV feeds and uploaded video.
          </p>

          <div style={styles.btnRow}>
            <HeroButton
              label="▶  LIVE FEED"
              accent="var(--green-threat)"
              glow="var(--green-glow)"
              onClick={() => navigate('/live-feed')}
            />
            <HeroButton
              label="▲  VIDEO UPLOAD"
              accent="var(--amber-warn)"
              glow="var(--amber-glow)"
              onClick={() => navigate('/video-upload')}
            />
          </div>
        </div>

        <div style={styles.scanBox}>
          <ScanLine />
          <div style={styles.crosshair}>
            <span style={styles.chTop} />
            <span style={styles.chBottom} />
            <span style={styles.chLeft} />
            <span style={styles.chRight} />
            <span style={styles.chLabel}>DETECTION ACTIVE</span>
          </div>
        </div>
      </div>

      <div style={styles.features}>
        {FEATURES.map((f) => (
          <FeatureCard key={f.label} {...f} />
        ))}
      </div>
    </div>
  );
}

function HeroButton({ label, accent, glow, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontFamily: 'var(--font-display)',
        fontSize: 16,
        fontWeight: 700,
        letterSpacing: '0.15em',
        padding: '14px 36px',
        border: `1px solid ${accent}`,
        background: glow,
        color: accent,
        cursor: 'pointer',
        transition: 'all 0.2s',
        minWidth: 200,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = accent;
        e.currentTarget.style.color = 'var(--bg-void)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = glow;
        e.currentTarget.style.color = accent;
      }}
    >
      {label}
    </button>
  );
}

function FeatureCard({ icon, label, desc, accent }) {
  return (
    <div style={{ ...styles.card, borderTop: `2px solid ${accent}` }}>
      <span style={{ fontSize: 28, marginBottom: 10, display: 'block' }}>{icon}</span>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontSize: 15,
        fontWeight: 700,
        letterSpacing: '0.1em',
        color: accent,
        marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.7 }}>
        {desc}
      </div>
    </div>
  );
}

function ScanLine() {
  return (
    <div style={{
      position: 'absolute',
      inset: 0,
      overflow: 'hidden',
      pointerEvents: 'none',
    }}>
      <div style={{
        position: 'absolute',
        left: 0,
        right: 0,
        height: 1,
        background: 'linear-gradient(90deg, transparent, var(--green-threat), transparent)',
        opacity: 0.5,
        animation: 'scanMove 3s linear infinite',
      }} />
      <style>{`
        @keyframes scanMove {
          0%   { top: 0%; }
          100% { top: 100%; }
        }
      `}</style>
    </div>
  );
}

const FEATURES = [
  {
    icon: '🎯',
    label: 'HIGH ACCURACY',
    desc: '96.50% accuracy classifying violent activities using ResNet50 + LSTM model.',
    accent: 'var(--green-threat)',
  },
  {
    icon: '⚡',
    label: 'REAL-TIME',
    desc: 'Optimised for live video stream analysis with WebSocket frame streaming at 5 FPS.',
    accent: 'var(--amber-warn)',
  },
  {
    icon: '📊',
    label: 'ADVANCED METRICS',
    desc: '96.52% F1 Score and 70.70% mAP for reliable multi-class threat detection.',
    accent: 'var(--blue-clear)',
  },
  {
    icon: '🔒',
    label: 'PRECISE CLASSIFICATION',
    desc: '95.57% Precision and 96.52% Recall across violence, intrusion, fire, and anomaly classes.',
    accent: 'var(--red-critical)',
  },
];

const styles = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflowY: 'auto',
    background: 'var(--bg-void)',
  },
  hero: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '60px 60px 48px',
    gap: 40,
    borderBottom: '1px solid var(--bg-border)',
    flexWrap: 'wrap',
  },
  heroContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
    maxWidth: 560,
  },
  badge: {
    fontFamily: 'var(--font-mono)',
    fontSize: 10,
    letterSpacing: '0.2em',
    color: 'var(--green-dim)',
    padding: '4px 10px',
    border: '1px solid var(--green-dim)',
    display: 'inline-block',
    width: 'fit-content',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: 52,
    fontWeight: 700,
    letterSpacing: '0.1em',
    lineHeight: 1.1,
    color: 'var(--text-primary)',
  },
  subtitle: {
    fontFamily: 'var(--font-mono)',
    fontSize: 13,
    color: 'var(--text-secondary)',
    lineHeight: 1.8,
    maxWidth: 480,
  },
  btnRow: {
    display: 'flex',
    gap: 16,
    flexWrap: 'wrap',
    marginTop: 8,
  },
  scanBox: {
    position: 'relative',
    width: 280,
    height: 280,
    border: '1px solid var(--bg-border)',
    background: 'var(--bg-panel)',
    flexShrink: 0,
    overflow: 'hidden',
  },
  crosshair: {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  chTop: {
    position: 'absolute',
    top: 24,
    left: '50%',
    transform: 'translateX(-50%)',
    width: 1,
    height: 40,
    background: 'var(--green-threat)',
    opacity: 0.5,
  },
  chBottom: {
    position: 'absolute',
    bottom: 24,
    left: '50%',
    transform: 'translateX(-50%)',
    width: 1,
    height: 40,
    background: 'var(--green-threat)',
    opacity: 0.5,
  },
  chLeft: {
    position: 'absolute',
    left: 24,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 40,
    height: 1,
    background: 'var(--green-threat)',
    opacity: 0.5,
  },
  chRight: {
    position: 'absolute',
    right: 24,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 40,
    height: 1,
    background: 'var(--green-threat)',
    opacity: 0.5,
  },
  chLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: 10,
    letterSpacing: '0.2em',
    color: 'var(--green-threat)',
    opacity: 0.7,
    animation: 'blink 2s infinite',
  },
  features: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 1,
    background: 'var(--bg-border)',
    flexShrink: 0,
  },
  card: {
    background: 'var(--bg-panel)',
    padding: '28px 24px',
  },
};