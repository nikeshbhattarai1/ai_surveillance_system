import { useState, useRef } from 'react';
import { useDetections } from '../hooks/useDetections';
import { useAuth } from '../context/AuthContext';
import ConfidenceBar from '../components/ConfidenceBar';

const STATUS_COLOR = {
    violence: 'var(--red-critical)',
    anomaly: 'var(--amber-warn)',
    intrusion: 'var(--amber-warn)',
    fire: 'var(--red-critical)',
    normal: 'var(--blue-clear)',
    unknown: 'var(--text-secondary)',
};

const MOCK_DETECTIONS = [
    { id: 1, timestamp: new Date(Date.now() - 60000).toISOString(), event_type: 'violence', confidence: 0.91, source: 'stream', notified: true, notification_channel: 'email', job_id: null },
    { id: 2, timestamp: new Date(Date.now() - 120000).toISOString(), event_type: 'normal', confidence: 0.98, source: 'stream', notified: false, notification_channel: null, job_id: null },
    { id: 3, timestamp: new Date(Date.now() - 180000).toISOString(), event_type: 'normal', confidence: 0.95, source: 'upload', notified: false, notification_channel: null, job_id: 'a1b2c3d4-e5f6-47a8-9b0c-1d2e3f4a5b6c' },
    { id: 4, timestamp: new Date(Date.now() - 240000).toISOString(), event_type: 'violence', confidence: 0.81, source: 'stream', notified: true, notification_channel: 'slack', job_id: null },
    { id: 5, timestamp: new Date(Date.now() - 300000).toISOString(), event_type: 'normal', confidence: 0.97, source: 'upload', notified: false, notification_channel: null, job_id: 'e5f6g7h8-a1b2-4c3d-8e9f-0a1b2c3d4e5f' },
];

const EVENT_TYPES = ['ALL', 'VIOLENCE', 'NORMAL'];

// Roles allowed to delete detection records — must mirror the
// require_role(...) check on DELETE /api/v1/detections/{id} in the backend.
const CAN_DELETE_ROLES = ['ADMIN', 'OPERATOR'];

export default function DetectionHistory() {
    const [filter, setFilter] = useState('ALL');
    const [confirmingId, setConfirmingId] = useState(null);
    const [copiedId, setCopiedId] = useState(null);
    const [deletingId, setDeletingId] = useState(null);
    const confirmTimer = useRef(null);

    const { user } = useAuth();
    const canDelete = CAN_DELETE_ROLES.includes(user?.role?.toUpperCase());

    const {
        detections: apiData,
        total,
        loading,
        error,
        page,
        setPage,
        limit,
        remove,
    } = useDetections();

    // Only fall back to demo rows when the request actually failed.
    // A legitimately empty result set (e.g. no detections yet, or the
    // last one was just deleted) should show "no records", not fake data.
    const detections = error ? MOCK_DETECTIONS : apiData;
    const displayTotal = error ? MOCK_DETECTIONS.length : total;
    const totalPages = Math.max(1, Math.ceil(displayTotal / limit));

    const filtered = filter === 'ALL'
        ? detections
        : detections.filter((d) => d.event_type?.toUpperCase() === filter);

    const handleCopyId = async (jobId) => {
        if (!jobId) return;
        try {
            await navigator.clipboard.writeText(jobId);
            setCopiedId(jobId);
            setTimeout(() => setCopiedId(null), 1200);
        } catch {
            // Clipboard API unavailable (e.g. non-HTTPS context) — ignore silently.
        }
    };

    const handleDeleteClick = async (id) => {
        if (confirmingId !== id) {
            // First click arms a confirmation state instead of deleting
            // immediately, and auto-disarms after 3s so a stray click
            // later can't trigger an old confirmation.
            setConfirmingId(id);
            clearTimeout(confirmTimer.current);
            confirmTimer.current = setTimeout(() => setConfirmingId(null), 3000);
            return;
        }

        clearTimeout(confirmTimer.current);
        setConfirmingId(null);
        setDeletingId(id);
        try {
            await remove(id);
        } catch {
            // remove() already restores state and surfaces the error via `error`
        } finally {
            setDeletingId(null);
        }
    };

    // Job ID column is sized to fit a full UUID (36 chars) on one line at
    // the mono font-size used below, plus breathing room for the "COPIED ✓"
    // state. Other fixed columns were trimmed slightly to make space.
    const gridTemplateColumns = canDelete
        ? '180px 100px 150px 80px 120px minmax(280px, 1fr) 90px'
        : '180px 100px 150px 80px 120px minmax(280px, 1fr)';

    return (
        <div style={styles.root}>

            {/* ── Page header ── */}
            <div style={styles.header}>
                <div>
                    <span style={styles.title}>DETECTION HISTORY</span>
                    <span style={styles.sub}>
                        {displayTotal} TOTAL RECORDS{error ? ' · DEMO DATA' : ''}
                    </span>
                </div>

                {/* ── Filter chips ── */}
                <div style={styles.filters}>
                    {EVENT_TYPES.map((type) => (
                        <button
                            key={type}
                            onClick={() => setFilter(type)}
                            style={{
                                ...styles.chip,
                                borderColor: filter === type
                                    ? STATUS_COLOR[type.toLowerCase()] ?? 'var(--green-threat)'
                                    : 'var(--bg-border)',
                                color: filter === type
                                    ? STATUS_COLOR[type.toLowerCase()] ?? 'var(--green-threat)'
                                    : 'var(--text-secondary)',
                                background: filter === type ? 'var(--bg-raised)' : 'transparent',
                            }}
                        >
                            {type}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Table ── */}
            <div style={styles.tableWrap}>

                {/* Column headers */}
                <div style={{ ...styles.colHeaders, gridTemplateColumns }}>
                    {['TIMESTAMP', 'TYPE', 'CONFIDENCE', 'SOURCE', 'NOTIFIED', 'JOB ID'].map((h) => (
                        <span key={h} style={styles.colHeader}>{h}</span>
                    ))}
                    {canDelete && <span style={styles.colHeader}>ACTIONS</span>}
                </div>

                {/* Rows */}
                <div style={styles.tbody}>
                    {loading && (
                        <div style={styles.status}>LOADING...</div>
                    )}

                    {!loading && filtered.length === 0 && (
                        <div style={styles.status}>NO RECORDS MATCH FILTER</div>
                    )}

                    {filtered.map((d) => (
                        <div key={d.id} style={{ ...styles.row, gridTemplateColumns }}>

                            <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                                {new Date(d.timestamp).toLocaleString('en-US', { hour12: false })}
                            </span>

                            <span style={{
                                fontFamily: 'var(--font-display)',
                                fontWeight: 700,
                                fontSize: 13,
                                letterSpacing: '0.05em',
                                color: STATUS_COLOR[d.event_type] ?? 'var(--text-secondary)',
                            }}>
                                {d.event_type?.toUpperCase()}
                            </span>

                            <div style={{ minWidth: 120 }}>
                                <ConfidenceBar confidence={d.confidence} label={d.event_type} />
                            </div>

                            <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                                {d.source?.toUpperCase()}
                            </span>

                            <span style={{
                                color: d.notified ? 'var(--green-threat)' : 'var(--text-dim)',
                                fontSize: 11,
                            }}>
                                {d.notified ? `✓ ${d.notification_channel?.toUpperCase()}` : '—'}
                            </span>

                            {/* Full UUID is rendered directly (no truncation) and
                                copies to clipboard on click; title attr still
                                gives a native tooltip as a fallback. */}
                            <span
                                title={d.job_id || undefined}
                                onClick={() => handleCopyId(d.job_id)}
                                style={{
                                    color: copiedId === d.job_id ? 'var(--green-threat)' : 'var(--text-dim)',
                                    fontSize: 10,
                                    fontFamily: 'var(--font-mono)',
                                    cursor: d.job_id ? 'pointer' : 'default',
                                    userSelect: 'none',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                }}
                            >
                                {d.job_id
                                    ? (copiedId === d.job_id ? 'COPIED ✓' : d.job_id)
                                    : 'STREAM'}
                            </span>

                            {canDelete && (
                                <button
                                    onClick={() => handleDeleteClick(d.id)}
                                    disabled={deletingId === d.id}
                                    style={{
                                        ...styles.deleteBtn,
                                        ...(confirmingId === d.id ? styles.deleteBtnConfirm : {}),
                                    }}
                                >
                                    {deletingId === d.id
                                        ? '...'
                                        : confirmingId === d.id
                                            ? 'CONFIRM?'
                                            : 'DELETE'}
                                </button>
                            )}

                        </div>
                    ))}
                </div>
            </div>

            {/* ── Pagination ── */}
            <div style={styles.pagination}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                    SHOWING {filtered.length} OF {displayTotal} RECORDS
                </span>

                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <button
                        style={styles.pageBtn}
                        onClick={() => setPage(Math.max(0, page - 1))}
                        disabled={page === 0}
                    >
                        ← PREV
                    </button>

                    <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                        PAGE {page + 1} / {totalPages}
                    </span>

                    <button
                        style={styles.pageBtn}
                        onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                        disabled={page >= totalPages - 1}
                    >
                        NEXT →
                    </button>
                </div>
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
        background: 'var(--bg-void)',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        flexWrap: 'wrap',
        gap: 16,
        padding: '24px 24px 16px',
        borderBottom: '1px solid var(--bg-border)',
        background: 'var(--bg-panel)',
        flexShrink: 0,
    },
    title: {
        fontFamily: 'var(--font-display)',
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: '0.15em',
        color: 'var(--text-primary)',
        display: 'block',
        marginBottom: 4,
    },
    sub: {
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        color: 'var(--text-dim)',
        letterSpacing: '0.1em',
    },
    filters: {
        display: 'flex',
        gap: 8,
        flexWrap: 'wrap',
    },
    chip: {
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        letterSpacing: '0.12em',
        padding: '4px 12px',
        border: '1px solid',
        background: 'transparent',
        cursor: 'pointer',
        transition: 'all 0.15s',
    },
    tableWrap: {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'hidden',
        overflowX: 'auto',
    },
    colHeaders: {
        display: 'grid',
        gap: 16,
        padding: '8px 24px',
        background: 'var(--bg-raised)',
        borderBottom: '1px solid var(--bg-border)',
        flexShrink: 0,
    },
    colHeader: {
        fontSize: 10,
        color: 'var(--text-dim)',
        letterSpacing: '0.12em',
        fontWeight: 700,
        fontFamily: 'var(--font-mono)',
    },
    tbody: {
        flex: 1,
        overflowY: 'auto',
    },
    row: {
        display: 'grid',
        gap: 16,
        padding: '11px 24px',
        borderBottom: '1px solid var(--bg-border)',
        alignItems: 'center',
        fontSize: 12,
        transition: 'background 0.15s',
        cursor: 'default',
    },
    status: {
        padding: 32,
        textAlign: 'center',
        color: 'var(--text-secondary)',
        letterSpacing: '0.1em',
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
    },
    pagination: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '10px 24px',
        borderTop: '1px solid var(--bg-border)',
        background: 'var(--bg-panel)',
        flexShrink: 0,
    },
    pageBtn: {
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        letterSpacing: '0.1em',
        padding: '5px 14px',
        border: '1px solid var(--bg-border)',
        background: 'transparent',
        color: 'var(--text-secondary)',
        cursor: 'pointer',
        transition: 'all 0.15s',
    },
    deleteBtn: {
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        letterSpacing: '0.08em',
        padding: '4px 8px',
        border: '1px solid var(--bg-border)',
        background: 'transparent',
        color: 'var(--text-dim)',
        cursor: 'pointer',
        transition: 'all 0.15s',
        justifySelf: 'start',
    },
    deleteBtnConfirm: {
        borderColor: 'var(--red-critical)',
        color: 'var(--red-critical)',
    },
};