import { useState, useRef, useEffect } from 'react';
import { uploadVideo } from '../api/detections';

export default function UploadPanel({ onStateChange }) {
  const [file, setFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef();

  useEffect(() => {
    onStateChange?.({ loading, result });
  }, [loading, result]);

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true); setError(null); setResult(null); setProgress(0);
    try {
      const data = await uploadVideo(file, setProgress);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const hasState = !!(file || result || error);

  const handleClear = () => {
    setFile(null);
    setProgress(0);
    setResult(null);
    setError(null);
    // Reset the native input value too — otherwise re-selecting the same
    // file won't fire onChange since the browser sees no value change.
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>VIDEO UPLOAD</span>
      </div>
      <div
        style={{
          ...styles.dropzone,
          borderColor: file ? 'var(--amber-warn)' : 'var(--bg-border)',
          background: file ? 'var(--amber-glow)' : 'transparent',
        }}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept="video/*" style={{ display: 'none' }}
          onChange={(e) => setFile(e.target.files[0])} />
        <span style={{ color: 'var(--text-secondary)', fontSize: 11, letterSpacing: '0.1em' }}>
          {file ? `▶ ${file.name}` : '+ DROP VIDEO FILE OR CLICK'}
        </span>
        {file && (
          <span style={{ color: 'var(--text-dim)', fontSize: 10, marginTop: 4 }}>
            {(file.size / 1024 / 1024).toFixed(1)} MB
          </span>
        )}
      </div>
      {loading && (
        <div style={{ marginTop: 8 }}>
          <div style={styles.progressTrack}>
            <div style={{ ...styles.progressFill, width: `${progress}%` }} />
          </div>
          <span style={{ color: 'var(--text-secondary)', fontSize: 10, marginTop: 4, display: 'block' }}>
            UPLOADING {progress}%
          </span>
        </div>
      )}
      {result && (
        <div style={styles.result}>
          <span style={{ color: 'var(--green-threat)' }}>✓ QUEUED</span>
          <span style={{ color: 'var(--text-secondary)', fontSize: 10, marginTop: 4, display: 'block' }}>
            JOB: {result.job_id}
          </span>
        </div>
      )}
      {error && (
        <div style={{ ...styles.result, borderColor: 'var(--red-critical)', color: 'var(--red-critical)' }}>
          ✗ {error}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={handleSubmit} disabled={!file || loading} style={{
          ...styles.btn,
          flex: 1,
          opacity: (!file || loading) ? 0.4 : 1,
          cursor: (!file || loading) ? 'not-allowed' : 'pointer',
        }}>
          {loading ? 'UPLOADING...' : '▲ SUBMIT FOR ANALYSIS'}
        </button>
        <button onClick={handleClear} disabled={!hasState || loading} style={{
          ...styles.clearBtn,
          opacity: (!hasState || loading) ? 0.4 : 1,
          cursor: (!hasState || loading) ? 'not-allowed' : 'pointer',
        }}>
          ✕ CLEAR
        </button>
      </div>
    </div>
  );
}

const styles = {
  panel: {
    background: 'var(--bg-panel)', border: '1px solid var(--bg-border)',
    padding: 16, display: 'flex', flexDirection: 'column', gap: 10,
  },
  header: { paddingBottom: 8, borderBottom: '1px solid var(--bg-border)' },
  title: { fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700, letterSpacing: '0.15em' },
  dropzone: {
    border: '1px dashed', padding: '24px 16px',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', transition: 'all 0.2s', minHeight: 80,
  },
  progressTrack: { height: 2, background: 'var(--bg-border)', position: 'relative', overflow: 'hidden' },
  progressFill: {
    position: 'absolute', left: 0, top: 0, bottom: 0,
    background: 'var(--amber-warn)', boxShadow: '0 0 8px var(--amber-warn)', transition: 'width 0.2s',
  },
  result: { border: '1px solid var(--green-dim)', padding: '8px 12px', fontSize: 11, letterSpacing: '0.05em' },
  btn: {
    fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, letterSpacing: '0.15em',
    padding: '9px 16px', border: '1px solid var(--amber-warn)', background: 'var(--amber-glow)',
    color: 'var(--amber-warn)', width: '100%', textAlign: 'center', transition: 'all 0.2s',
  },
  clearBtn: {
    fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, letterSpacing: '0.15em',
    padding: '9px 14px', border: '1px solid var(--bg-border)', background: 'transparent',
    color: 'var(--text-secondary)', textAlign: 'center', transition: 'all 0.2s', flexShrink: 0,
  },
};