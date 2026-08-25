import { useState, useEffect, useRef } from 'react';
import UploadPanel from '../components/UploadPanel';
import DetectionResults from '../components/DetectionResults';
import { fetchDetections, fetchJobStatus } from '../api/detections';

const POLL_INTERVAL_MS = 4000;
const POLL_TIMEOUT_MS = 10 * 60 * 1000; // safety net in case a job never leaves queued/processing

// event_types that count as an actual threat for display purposes.
// Keep in sync with db/models.py EventType — anything not in this set
// (e.g. 'normal', or an unmapped 'unknown') renders as clear, not threat.
const THREAT_EVENT_TYPES = new Set(['violence', 'anomaly', 'intrusion', 'fire']);

export default function VideoUpload() {
  const [uploadState, setUploadState] = useState({ loading: false, result: null });
  // detection: undefined = not resolved yet, null = job completed with no threat found, object = threat found
  const [detection, setDetection] = useState(undefined);
  const [polling, setPolling] = useState(false);
  const [jobFailed, setJobFailed] = useState(null);
  const pollTimerRef = useRef(null);

  useEffect(() => {
    // Reset and (re)start polling whenever a new job is queued
    clearInterval(pollTimerRef.current);
    setDetection(undefined);
    setJobFailed(null);

    const jobId = uploadState.result?.job_id;
    if (!jobId) return;

    setPolling(true);
    const startedAt = Date.now();

    const poll = async () => {
      try {
        const job = await fetchJobStatus(jobId);

        if (job.status === 'failed') {
          setJobFailed(job.error_message || 'Processing failed');
          setPolling(false);
          clearInterval(pollTimerRef.current);
          return;
        }

        if (job.status === 'completed') {
          const data = await fetchDetections({ jobId, limit: 1 });
          // Job is done: either a threat row exists, or it's confirmed clear —
          // no more ambiguity, no more timeout guessing.
          setDetection(data.items?.[0] ?? null);
          setPolling(false);
          clearInterval(pollTimerRef.current);
          return;
        }
        // else: status is 'queued' or 'processing' — keep polling
      } catch {
        // transient fetch errors are ignored; next tick retries
      }

      if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
        setPolling(false);
        clearInterval(pollTimerRef.current);
      }
    };

    poll();
    pollTimerRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(pollTimerRef.current);
  }, [uploadState.result?.job_id]);

  const hasResult = detection !== undefined && detection !== null;

  // A detection record now exists for both threat AND clear outcomes
  // (see the backend fix that always persists a verdict). "A record
  // exists" is no longer the same thing as "it was a threat" — that
  // has to come from event_type itself.
  const isThreat = hasResult
    ? THREAT_EVENT_TYPES.has(detection.event_type)
    : (detection === null ? false : null);

  const monitoringStatus = uploadState.loading
    ? 'Uploading'
    : jobFailed
      ? `Failed: ${jobFailed}`
      : polling
        ? 'Processing'
        : hasResult
          ? 'Analysis Complete'
          : detection === null
            ? 'Analysis Complete'
            : uploadState.result
              ? 'Queued'
              : 'Idle';

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <span style={styles.title}>VIDEO UPLOAD</span>
        <span style={styles.sub}>Submit a recorded video file for offline threat analysis</span>
      </div>

      <div style={styles.body}>
        <div style={styles.uploadCol}>
          <UploadPanel onStateChange={setUploadState} />
        </div>

        <div style={styles.resultsCol}>
          <DetectionResults
            isThreat={isThreat}
            label={detection?.event_type}
            streamSource="Uploaded Video"
            monitoringStatus={monitoringStatus}
          />
        </div>

        <div style={styles.infoCol}>
          {INFO.map((item) => (
            <InfoRow key={item.label} {...item} />
          ))}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ icon, label, desc }) {
  return (
    <div style={styles.infoRow}>
      <span style={styles.infoIcon}>{icon}</span>
      <div>
        <div style={styles.infoLabel}>{label}</div>
        <div style={styles.infoDesc}>{desc}</div>
      </div>
    </div>
  );
}

const INFO = [
  {
    icon: '📁',
    label: 'ACCEPTED FORMATS',
    desc: 'MP4, AVI, MOV, MKV — any format supported by your browser\'s File API.',
  },
  {
    icon: '⚙️',
    label: 'PROCESSING',
    desc: 'Video is queued as a background Celery job. A job ID is returned immediately.',
  },
  {
    icon: '📋',
    label: 'RESULTS',
    desc: 'Detection results appear here once the job completes, and in Detection History.',
  },
  {
    icon: '⚠️',
    label: 'SIZE LIMIT',
    desc: 'Keep files under 500 MB for reliable upload performance.',
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
  header: {
    padding: '32px 48px 24px',
    borderBottom: '1px solid var(--bg-border)',
    flexShrink: 0,
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontSize: 28,
    fontWeight: 700,
    letterSpacing: '0.15em',
    color: 'var(--text-primary)',
    display: 'block',
    marginBottom: 6,
  },
  sub: {
    fontFamily: 'var(--font-mono)',
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  body: {
    display: 'flex',
    gap: 32,
    padding: '32px 48px',
    flexWrap: 'wrap',
    alignItems: 'flex-start',
  },
  uploadCol: {
    width: 400,
    flexShrink: 0,
  },
  resultsCol: {
    width: 320,
    flexShrink: 0,
  },
  infoCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
    flex: 1,
    minWidth: 260,
  },
  infoRow: {
    display: 'flex',
    gap: 14,
    alignItems: 'flex-start',
    padding: '16px',
    background: 'var(--bg-panel)',
    border: '1px solid var(--bg-border)',
  },
  infoIcon: {
    fontSize: 20,
    flexShrink: 0,
    marginTop: 2,
  },
  infoLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.1em',
    color: 'var(--amber-warn)',
    marginBottom: 4,
  },
  infoDesc: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'var(--text-secondary)',
    lineHeight: 1.7,
  },
};