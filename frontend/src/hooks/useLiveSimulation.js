import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getLiveSimulation,
  liveSimulationStreamUrl,
  startLiveSimulation,
  stopLiveSimulation,
} from '../services/trafficControlService';

function appendDecision(current = [], decision) {
  if (!decision) return current;
  const next = [...current.filter((item) => item.sequence !== decision.sequence), decision];
  return next.slice(-30);
}

function mergeEvent(current, event) {
  const base = current || {};
  if (event.type === 'session') return { ...base, ...event };
  return {
    ...base,
    id: event.id ?? base.id,
    status: event.status ?? base.status,
    cycle: event.cycle ?? base.cycle,
    sequence: event.sequence ?? event.decisionSequence ?? base.sequence,
    decisionSequence: event.decisionSequence ?? base.decisionSequence,
    frameSequence: event.frameSequence ?? base.frameSequence,
    snapshot: event.snapshot ?? base.snapshot,
    metrics: event.metrics ?? base.metrics,
    streamInfo: event.streamInfo ?? base.streamInfo,
    decisions: event.decision
      ? appendDecision(base.decisions, event.decision)
      : (event.decisions ?? base.decisions ?? []),
    error: event.error ?? base.error,
    stoppedAt: event.stoppedAt ?? base.stoppedAt,
  };
}

/**
 * Mantiene una simulación realmente viva en React.
 *
 * SSE es el canal principal. En desarrollo React.StrictMode monta/desmonta los
 * efectos dos veces; por eso `mounted.current` se reactiva explícitamente en
 * cada setup. Si SSE se queda sin frames > 900 ms, se activa un polling corto
 * como respaldo. El polling no crea estados: solo recupera el último snapshot
 * real que Python ya produjo y NestJS mantiene en memoria.
 */
export function useLiveSimulation() {
  const [session, setSession] = useState(null);
  const [error, setError] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('closed');
  const sourceRef = useRef(null);
  const fallbackTimerRef = useRef(null);
  const lastEventAtRef = useRef(0);
  const pollBusyRef = useRef(false);
  const mounted = useRef(false);

  const stopFallback = useCallback(() => {
    if (fallbackTimerRef.current) {
      clearInterval(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  }, []);

  const closeStream = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    stopFallback();
    if (mounted.current) setConnectionStatus('closed');
  }, [stopFallback]);

  useEffect(() => {
    // IMPORTANTE: StrictMode ejecuta setup -> cleanup -> setup en desarrollo.
    // Sin esta línea el hook quedaba permanentemente marcado como desmontado y
    // descartaba todos los frames SSE, aunque Python/NestJS sí los enviaran.
    mounted.current = true;
    return () => {
      mounted.current = false;
      sourceRef.current?.close();
      sourceRef.current = null;
      stopFallback();
    };
  }, [stopFallback]);

  const startFallback = useCallback((sessionId) => {
    stopFallback();
    fallbackTimerRef.current = setInterval(async () => {
      if (!mounted.current || pollBusyRef.current) return;

      const staleForMs = Date.now() - lastEventAtRef.current;
      if (staleForMs < 900) return;

      pollBusyRef.current = true;
      try {
        const fresh = await getLiveSimulation(sessionId);
        if (!mounted.current) return;
        setSession((current) => mergeEvent(current, { type: 'session', ...fresh }));
        if (fresh.status === 'running') setConnectionStatus('fallback');
        if (fresh.error?.message) setError(fresh.error.message);
      } catch (caught) {
        if (mounted.current) setError(`No se pudo recuperar el frame en vivo: ${caught.message}`);
      } finally {
        pollBusyRef.current = false;
      }
    }, 250);
  }, [stopFallback]);

  const connect = useCallback((sessionId) => {
    sourceRef.current?.close();
    setConnectionStatus('connecting');
    lastEventAtRef.current = Date.now();

    const source = new EventSource(liveSimulationStreamUrl(sessionId));
    sourceRef.current = source;
    startFallback(sessionId);

    source.onopen = () => {
      if (!mounted.current) return;
      lastEventAtRef.current = Date.now();
      setConnectionStatus('live');
      setError('');
    };

    source.onmessage = (message) => {
      if (!mounted.current) return;
      try {
        const event = JSON.parse(message.data);
        lastEventAtRef.current = Date.now();
        setConnectionStatus('live');
        setSession((current) => mergeEvent(current, event));
        if (event.error?.message) setError(event.error.message);
        if (['stopped', 'failed'].includes(event.status) || ['stopped', 'failed'].includes(event.type)) {
          source.close();
          sourceRef.current = null;
          stopFallback();
          setConnectionStatus('closed');
        }
      } catch (caught) {
        setError(`Frame SSE inválido: ${caught.message}`);
      }
    };

    source.onerror = () => {
      if (!mounted.current) return;
      // EventSource intenta reconectar automáticamente. Mientras tanto el
      // fallback GET mantiene la pantalla actualizada con snapshots reales.
      if (source.readyState === EventSource.CLOSED) {
        setConnectionStatus('fallback');
      } else {
        setConnectionStatus('reconnecting');
      }
    };
  }, [startFallback, stopFallback]);

  const start = useCallback(async (parameters) => {
    setError('');
    closeStream();
    const created = await startLiveSimulation(parameters);
    if (mounted.current) {
      setSession(created);
      connect(created.id);
    }
    return created;
  }, [closeStream, connect]);

  const stop = useCallback(async () => {
    if (!session?.id) return null;
    const stopped = await stopLiveSimulation(session.id);
    if (mounted.current) setSession((current) => ({ ...current, ...stopped }));
    return stopped;
  }, [session?.id]);

  const reset = useCallback(() => {
    closeStream();
    setSession(null);
    setError('');
  }, [closeStream]);

  return { session, error, connectionStatus, start, stop, reset };
}
