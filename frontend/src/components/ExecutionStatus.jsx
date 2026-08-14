import { useEffect, useMemo, useState } from 'react';

const OPERATION_COPY = {
  simulate: {
    title: 'Simulando baseline',
    detail: 'Ejecutando el controlador heurístico seguro para obtener el punto de comparación.',
  },
  train: {
    title: 'Entrenando agentes DQN',
    detail: 'Los agentes prueban fases legales, reciben recompensas y actualizan sus redes neuronales.',
  },
  evaluate: {
    title: 'Evaluando DQN',
    detail: 'El modelo guardado controla la red sin aprender para medir su rendimiento real.',
  },
};

function elapsedLabel(startedAt, now) {
  if (!startedAt) return 'Preparando…';
  const seconds = Math.max(0, Math.floor((now - new Date(startedAt).getTime()) / 1000));
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} min ${seconds % 60} s`;
}

export default function ExecutionStatus({
  job,
  topologyBusy,
  topologyReady,
  baselineReady,
  trainingReady,
  evaluationReady,
}) {
  const [now, setNow] = useState(Date.now());
  const running = topologyBusy || ['pending', 'running'].includes(job?.status);

  useEffect(() => {
    if (!running) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(timer);
  }, [running]);

  const activeCopy = useMemo(() => {
    if (topologyBusy) {
      return {
        title: 'Resolviendo topología con Clingo',
        detail: 'Derivando movimientos posibles, conflictos y fases semafóricas legalmente válidas.',
      };
    }
    return OPERATION_COPY[job?.operation] || null;
  }, [job?.operation, topologyBusy]);

  const steps = [
    { label: 'Topología', done: topologyReady },
    { label: 'Baseline', done: baselineReady },
    { label: 'Entrenamiento', done: trainingReady },
    { label: 'Evaluación', done: evaluationReady },
  ];

  return (
    <section className={`execution-strip ${running ? 'is-running' : ''}`} aria-live="polite">
      <div className="execution-main">
        <div className={`execution-indicator ${running ? 'pulse' : ''}`}>
          {running ? <span className="spinner" /> : <span className="execution-dot" />}
        </div>
        <div>
          <span className="eyebrow">Estado del experimento</span>
          <strong>{activeCopy?.title || 'Listo para ejecutar'}</strong>
          <p>
            {activeCopy?.detail || 'Elige una acción. Recomendado: Topología → Baseline → Entrenar → Evaluar.'}
          </p>
        </div>
      </div>

      <div className="execution-side">
        {running && (
          <span className="elapsed-time">
            {topologyBusy ? 'Procesando…' : elapsedLabel(job?.startedAt || job?.createdAt, now)}
          </span>
        )}
        <div className="pipeline-steps" aria-label="Progreso del flujo de trabajo">
          {steps.map((step, index) => (
            <div className={`pipeline-step ${step.done ? 'done' : ''}`} key={step.label}>
              <span>{step.done ? '✓' : index + 1}</span>
              <small>{step.label}</small>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
