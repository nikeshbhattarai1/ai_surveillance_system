import { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import ConfidenceBar from './ConfidenceBar';

const STATUS_COLOR = {
  connected: 'var(--green-threat)',
  connecting: 'var(--amber-warn)',
  disconnected: 'var(--text-dim)',
  error: 'var(--red-critical)',
};

export default function CameraFeed({ onDetection }) {
  const {
    videoRef, canvasRef,
    status, lastEvent, frameCount, isCamActive, mode, remoteFrame,
    startSource, stopSource,
  } = useWebSocket();

  const [sourceInput, setSourceInput] = useState('');

  useEffect(() => {
    if (lastEvent?.event === 'threat_detected') {
      onDetection?.(lastEvent);
    }
  }, [lastEvent]);

  const handleToggle = async () => {
    if (isCamActive) {
      stopSource();
    } else {
      if (!sourceInput.trim()) return;
      await startSource(sourceInput);
    }
  };

  const isThreat = lastEvent?.is_threat;
  const confidence = lastEvent?.confidence ?? 0;
  const label = lastEvent?.event_type ?? 'normal';

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>LIVE FEED</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: STATUS_COLOR[status], display: 'inline-block',
            animation: status === 'connected' ? 'pulse-green 2s infinite' : 'none',
          }} />
          <span style={{ color: STATUS_COLOR[status], fontSize: 11 }}>{status.toUpperCase()}</span>
        </div>
      </div>

      <input
        type="text"
        value={sourceInput}
        onChange={(e) => setSourceInput(e.target.value)}
        disabled={isCamActive}
        placeholder="Enter 0 for webcam, or rtsp://... for CCTV"
        style={{
          ...styles.sourceInput,
          opacity: isCamActive ? 0.5 : 1,
        }}
      />

      <div style={{
        ...styles.viewport,
        outline: isThreat ? '1px solid var(--red-critical)' : '1px solid var(--bg-border)',
        boxShadow: isThreat ? '0 0 20px var(--red-glow)' : 'none',
        transition: 'box-shadow 0.3s, outline 0.3s',
      }}>
        {mode === 'rtsp' ? (
          remoteFrame ? (
            <img
              src={`data:image/jpeg;base64,${remoteFrame}`}
              alt="CCTV feed"
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
          ) : (
            <div style={styles.noSignal}>
              <span style={{ color: 'var(--text-dim)', fontSize: 11, letterSpacing: '0.2em' }}>
                CONNECTING TO CCTV...
              </span>
            </div>
          )
        ) : (
          <video ref={videoRef} muted style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
        )}

        {!isCamActive && (
          <div style={styles.noSignal}>
            <span style={{ color: 'var(--text-dim)', fontSize: 11, letterSpacing: '0.2em' }}>NO SIGNAL</span>
          </div>
        )}
        {isThreat && (
          <div style={styles.threatOverlay}>
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
              color: 'var(--red-critical)', letterSpacing: '0.2em',
              animation: 'pulse-red 0.8s infinite',
            }}>⚠ THREAT DETECTED</span>
          </div>
        )}
        {isCamActive && (
          <div style={styles.frameCounter}>FRM {String(frameCount).padStart(6, '0')}</div>
        )}
      </div>

      <div style={{ padding: '10px 0 6px' }}>
        <ConfidenceBar confidence={confidence} label={label} />
      </div>

      <button onClick={handleToggle} disabled={!isCamActive && !sourceInput.trim()} style={{
        ...styles.btn,
        background: isCamActive ? 'var(--red-glow)' : 'var(--green-glow)',
        borderColor: isCamActive ? 'var(--red-critical)' : 'var(--green-threat)',
        color: isCamActive ? 'var(--red-critical)' : 'var(--green-threat)',
        opacity: (!isCamActive && !sourceInput.trim()) ? 0.4 : 1,
        cursor: (!isCamActive && !sourceInput.trim()) ? 'not-allowed' : 'pointer',
      }}>
        {isCamActive ? '■ STOP STREAM' : '▶ START STREAM'}
      </button>

      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
}

const styles = {
  panel: {
    background: 'var(--bg-panel)', border: '1px solid var(--bg-border)',
    padding: 16, display: 'flex', flexDirection: 'column', gap: 8,
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    paddingBottom: 8, borderBottom: '1px solid var(--bg-border)',
  },
  title: {
    fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700,
    letterSpacing: '0.15em', color: 'var(--text-primary)',
  },
  sourceInput: {
    fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.05em',
    padding: '8px 10px', background: 'var(--bg-raised)',
    border: '1px solid var(--bg-border)', color: 'var(--text-primary)',
    outline: 'none', width: '100%',
  },
  viewport: {
    position: 'relative', aspectRatio: '16/9', background: '#000', overflow: 'hidden',
  },
  noSignal: {
    position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'repeating-linear-gradient(45deg,#0a0a0a 0px,#0a0a0a 2px,transparent 2px,transparent 8px)',
  },
  threatOverlay: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    padding: '8px 12px', background: 'rgba(255,45,85,0.15)', backdropFilter: 'blur(2px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  frameCounter: {
    position: 'absolute', top: 8, right: 8, fontFamily: 'var(--font-mono)',
    fontSize: 10, color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.6)',
    padding: '2px 6px', letterSpacing: '0.1em',
  },
  btn: {
    fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, letterSpacing: '0.15em',
    padding: '8px 16px', border: '1px solid', background: 'transparent',
    cursor: 'pointer', transition: 'all 0.2s', width: '100%', textAlign: 'center',
  },
};