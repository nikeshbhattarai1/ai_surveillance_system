import { useEffect, useRef, useCallback, useState } from 'react';
import { WS_URL } from '../api/client';

export function useWebSocket() {
    const wsRef = useRef(null);
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const intervalRef = useRef(null);

    const [status, setStatus] = useState('disconnected');
    const [lastEvent, setLastEvent] = useState(null);
    const [frameCount, setFrameCount] = useState(0);
    const [isCamActive, setIsCamActive] = useState(false);
    const [mode, setMode] = useState(null);        // 'webcam' | 'rtsp' | null
    const [remoteFrame, setRemoteFrame] = useState(null);        // base64 jpeg from backend (rtsp mode)

    const STREAM_FPS = 5;

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;
        setStatus('connecting');
        const ws = new WebSocket(`${WS_URL}/ws/stream`);
        wsRef.current = ws;
        ws.onopen = () => { setStatus('connected'); };
        ws.onclose = () => { setStatus('disconnected'); };
        ws.onerror = () => { setStatus('error'); };
        ws.onmessage = (msg) => {
            try {
                const data = JSON.parse(msg.data);
                setLastEvent(data);
                if (data.event !== 'heartbeat' && data.event !== 'buffering') {
                    setFrameCount(data.frame_id || 0);
                }
                // Backend pushes the decoded RTSP frame back as base64 jpeg
                if (data.frame) {
                    setRemoteFrame(data.frame);
                }
            } catch { /* ignore */ }
        };
    }, []);

    const disconnect = useCallback(() => {
        wsRef.current?.close();
        stopCamera();
        setMode(null);
        setRemoteFrame(null);
    }, []);

    const startCamera = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play();
                setIsCamActive(true);
            }
        } catch (e) {
            console.error('[Camera] Access denied:', e);
        }
    }, []);

    const stopCamera = useCallback(() => {
        if (videoRef.current?.srcObject) {
            videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
            videoRef.current.srcObject = null;
        }
        clearInterval(intervalRef.current);
        setIsCamActive(false);
    }, []);

    // source: '0' for webcam, or an rtsp:// URL string
    const startSource = useCallback(async (source) => {
        connect();
        const trimmed = source.trim();
        if (trimmed === '0') {
            setMode('webcam');
            await startCamera();
        } else {
            setMode('rtsp');
            // Tell the backend which RTSP stream to open and start pushing frames from.
            // Sent once the socket is open; if not yet open, queue until onopen fires.
            const send = () => wsRef.current.send(JSON.stringify({ source: trimmed }));
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                send();
            } else {
                wsRef.current.addEventListener('open', send, { once: true });
            }
            setIsCamActive(true);
        }
    }, [connect, startCamera]);

    const stopSource = useCallback(() => {
        if (mode === 'webcam') stopCamera();
        setIsCamActive(false);
        setRemoteFrame(null);
        disconnect();
    }, [mode, stopCamera, disconnect]);

    // Only stream local webcam frames to the backend in webcam mode
    useEffect(() => {
        if (mode !== 'webcam' || !isCamActive || status !== 'connected') return;
        intervalRef.current = setInterval(() => {
            const video = videoRef.current;
            const canvas = canvasRef.current;
            if (!video || !canvas || video.readyState < 2) return;
            const ctx = canvas.getContext('2d');
            canvas.width = 320;
            canvas.height = 240;
            ctx.drawImage(video, 0, 0, 320, 240);
            const base64 = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ frame: base64 }));
            }
        }, 1000 / STREAM_FPS);
        return () => clearInterval(intervalRef.current);
    }, [mode, isCamActive, status]);

    return {
        videoRef, canvasRef,
        status, lastEvent, frameCount, isCamActive, mode, remoteFrame,
        connect, disconnect, startCamera, stopCamera,
        startSource, stopSource,
    };
}