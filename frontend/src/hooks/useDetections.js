import { useState, useEffect, useCallback } from 'react';
import { fetchDetections, deleteDetection } from '../api/detections';

export function useDetections({ pollInterval = 5000 } = {}) {
  const [detections, setDetections] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const LIMIT = 20;

  const load = useCallback(async (pageNum = 0, { silent = false } = {}) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const data = await fetchDetections({ limit: LIMIT, offset: pageNum * LIMIT });
      setDetections(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e.message);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial load (and any load triggered by changing page) shows the
    // loading state — that's a real, user-visible transition. Background
    // polling ticks on an interval refresh the same data silently instead,
    // so the table doesn't flash "LOADING..." every few seconds when
    // nothing has actually changed.
    load(page);
    const timer = setInterval(() => load(page, { silent: true }), pollInterval);
    return () => clearInterval(timer);
  }, [load, page, pollInterval]);

  // Optimistically removes the row so the UI feels instant; if the
  // DELETE request fails, re-fetch the current page to resync state
  // rather than leaving a row missing that's still on the server.
  const remove = useCallback(async (id) => {
    setDetections((prev) => prev.filter((d) => d.id !== id));
    setTotal((prev) => Math.max(0, prev - 1));
    try {
      await deleteDetection(id);
    } catch (e) {
      setError(e.message);
      load(page);
      throw e;
    }
  }, [load, page]);

  // Deletes every record on the server matching eventType (or literally
  // everything if eventType is omitted), then resets to page 0 and
  // re-fetches — a full re-fetch is safer than optimistic clearing here
  // since a bulk op can be partially rejected server-side.
  const removeAll = useCallback(async (eventType) => {
    const result = await deleteAllDetections(eventType ? { eventType } : {});
    setPage(0);
    await load(0);
    return result; // { deleted: <count> }
  }, [load]);

  return {
    detections, total, loading, error,
    page, setPage,
    limit: LIMIT,
    refresh: () => load(page),
    remove,
    removeAll,
  };
}