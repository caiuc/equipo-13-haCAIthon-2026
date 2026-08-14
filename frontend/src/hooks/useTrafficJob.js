import { useCallback, useRef, useState } from 'react';
import { getJob, getJobResult } from '../services/trafficControlService';

const TERMINAL_STATES = new Set(['completed', 'failed', 'cancelled']);

export function useTrafficJob() {
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const pollToken = useRef(0);

  const run = useCallback(async (starter) => {
    const token = ++pollToken.current;
    setError('');
    setResult(null);
    try {
      const created = await starter();
      setJob(created);
      let current = created;
      while (!TERMINAL_STATES.has(current.status)) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        if (token !== pollToken.current) return null;
        current = await getJob(created.id);
        setJob(current);
      }
      if (current.status === 'failed') {
        throw new Error(current.error?.message || 'El trabajo falló');
      }
      const completed = await getJobResult(created.id);
      const pythonResponse = completed.result;
      setResult(pythonResponse?.data || null);
      return pythonResponse?.data || null;
    } catch (caught) {
      if (token === pollToken.current) setError(caught.message);
      throw caught;
    }
  }, []);

  const reset = useCallback(() => {
    pollToken.current += 1;
    setJob(null);
    setResult(null);
    setError('');
  }, []);

  return { job, result, error, run, reset };
}
