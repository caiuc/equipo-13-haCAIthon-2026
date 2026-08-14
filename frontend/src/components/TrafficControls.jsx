function humanDuration(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return '—';
  if (value < 60) return `${value} s`;
  if (value < 3600) return `${(value / 60).toFixed(value % 60 ? 1 : 0)} min`;
  return `${(value / 3600).toFixed(1)} h`;
}

function StepBadge({ number, done, active }) {
  return <span className={`step-badge ${done ? 'done' : ''} ${active ? 'active' : ''}`}>{done ? '✓' : number}</span>;
}

function connectionLabel(status) {
  return ({
    live: 'SSE conectado',
    connecting: 'Conectando stream…',
    reconnecting: 'Reconectando stream…',
    fallback: 'Actualización de respaldo · 250 ms',
    closed: 'Stream cerrado',
  })[status] || status;
}

export default function TrafficControls({
  values,
  clingoFile,
  onFile,
  onClearFile,
  onChange,
  onPreset,
  onValidate,
  onTrain,
  onStartLive,
  onStopLive,
  topologyReady,
  trainedRunId,
  job,
  topologyBusy,
  liveSession,
  connectionStatus,
}) {
  const training = job?.operation === 'train' && ['pending', 'running'].includes(job.status);
  const liveRunning = ['starting', 'running', 'stopping'].includes(liveSession?.status);
  const blocked = training || topologyBusy;

  return (
    <section className="experiment-flow">
      <article className={`flow-step ${topologyReady ? 'completed' : ''}`}>
        <header className="flow-step-head">
          <StepBadge number="1" done={topologyReady} active={topologyBusy} />
          <div><span className="eyebrow">Clingo</span><h2>Carga y valida las reglas</h2><p>Clingo define qué movimientos y fases son legalmente posibles.</p></div>
        </header>

        <label className={`clingo-dropzone ${clingoFile ? 'has-file' : ''}`}>
          <input type="file" accept=".lp,text/plain" onClick={(event) => { event.currentTarget.value = ''; }} onChange={(event) => onFile(event.target.files?.[0] || null)} disabled={blocked || liveRunning} />
          <span className="file-icon">ASP</span>
          <span className="file-copy">
            <strong>{clingoFile?.name || 'Seleccionar archivo .lp'}</strong>
            <small>{clingoFile ? `${(clingoFile.size / 1024).toFixed(1)} KB · se agrega al núcleo seguro rules.lp` : 'Si no cargas uno, se usa únicamente el rules.lp incluido en el proyecto.'}</small>
          </span>
          <span className="file-action">Elegir archivo</span>
        </label>
        {clingoFile && <button type="button" className="text-button" onClick={onClearFile} disabled={blocked || liveRunning}>Quitar archivo y usar reglas base</button>}

        <div className="network-fact-row">
          <span><strong>2</strong> cruces de 4 vías</span><span><strong>2</strong> pistas por sentido</span><span><strong>8</strong> semáforos visibles</span><span><strong>2</strong> recorridos de bus</span>
        </div>
        <button type="button" className="primary-big" onClick={onValidate} disabled={blocked || liveRunning}>
          {topologyBusy ? <><span className="spinner" /> Validando con Clingo…</> : topologyReady ? '✓ Revalidar topología' : 'Validar topología Clingo'}
        </button>
      </article>

      <article className={`flow-step ${trainedRunId ? 'completed' : ''}`}>
        <header className="flow-step-head">
          <StepBadge number="2" done={Boolean(trainedRunId)} active={training} />
          <div><span className="eyebrow">DQN</span><h2>Elige cuánto quieres entrenar</h2><p>Cada cruce posee su agente y solo puede escoger fases autorizadas por Clingo.</p></div>
        </header>

        <div className="preset-row train-presets">
          <button type="button" onClick={() => onPreset(3, 120)} disabled={blocked || liveRunning}>Prueba <small>3 ep · 2 min</small></button>
          <button type="button" onClick={() => onPreset(10, 300)} disabled={blocked || liveRunning}>Demo <small>10 ep · 5 min</small></button>
          <button type="button" onClick={() => onPreset(50, 900)} disabled={blocked || liveRunning}>Entrenamiento <small>50 ep · 15 min</small></button>
        </div>

        <div className="compact-fields">
          <label><span>Episodios</span><input name="episodes" type="number" min="1" max="10000" value={values.episodes} onChange={onChange} disabled={blocked || liveRunning} /><small>Veces que el agente practica.</small></label>
          <label><span>Duración por episodio</span><input name="trainSeconds" type="number" min="5" max="86400" value={values.trainSeconds} onChange={onChange} disabled={blocked || liveRunning} /><small>{humanDuration(values.trainSeconds)} de tráfico simulado.</small></label>
        </div>

        <div className="training-total"><span>Entrenamiento configurado</span><strong>{values.episodes} × {humanDuration(values.trainSeconds)}</strong></div>
        <button type="button" className="primary-big" onClick={onTrain} disabled={!topologyReady || blocked || liveRunning}>
          {training ? <><span className="spinner" /> Entrenando agentes…</> : trainedRunId ? 'Entrenar un nuevo modelo' : 'Entrenar DQN'}
        </button>
        {!topologyReady && <p className="flow-hint">Primero valida Clingo para habilitar el entrenamiento.</p>}
        {trainedRunId && <div className="run-id-card"><span>Modelo listo</span><code>{trainedRunId}</code></div>}
      </article>

      <article className={`flow-step live-step ${liveRunning ? 'is-live' : ''}`}>
        <header className="flow-step-head">
          <StepBadge number="3" done={false} active={liveRunning} />
          <div><span className="eyebrow">Simulación DQN</span><h2>Tráfico en tiempo real</h2><p>El motor avanza cada 0,2 s y transmite cada micro‑frame al navegador; el DQN vuelve a decidir cada 5 s.</p></div>
        </header>

        <div className="compact-fields">
          <label><span>Ciclo de tráfico</span><input name="cycleSeconds" type="number" min="60" max="86400" value={values.cycleSeconds} onChange={onChange} disabled={liveRunning || training} /><small>{humanDuration(values.cycleSeconds)} antes de generar un nuevo ciclo.</small></label>
          <label><span>Ritmo temporal</span><select name="realTimeFactor" value={values.realTimeFactor} onChange={onChange} disabled={liveRunning || training}><option value="0.5">0,5× · cámara lenta</option><option value="1">1× · tiempo real</option><option value="2">2× · acelerado</option><option value="4">4× · muy rápido</option></select><small>A 1×, 1 segundo simulado ≈ 1 segundo real.</small></label>
        </div>

        <div className="realtime-contract">
          <span><strong>0,2 s</strong> paso microscópico</span>
          <span><strong>≈5 FPS</strong> a 1×</span>
          <span><strong>5 s</strong> entre decisiones DQN</span>
          <span><strong>SSE</strong> + respaldo automático</span>
        </div>

        {!liveRunning ? (
          <button type="button" className="live-button start" onClick={onStartLive} disabled={!trainedRunId || training || topologyBusy}>
            <span className="live-dot" /> Iniciar simulación en tiempo real
          </button>
        ) : (
          <button type="button" className="live-button stop" onClick={onStopLive} disabled={liveSession?.status === 'stopping'}>
            <span className="stop-square" /> {liveSession?.status === 'stopping' ? 'Deteniendo…' : 'Detener simulación'}
          </button>
        )}
        {!trainedRunId && <p className="flow-hint">Después de entrenar, el modelo se selecciona automáticamente.</p>}
        {liveSession && <div className="live-session-meta"><span className={`session-state ${liveSession.status}`}>{liveSession.status}</span><span>{connectionLabel(connectionStatus)}</span><span>Ciclo {liveSession.cycle || 0}</span><span>Frame #{liveSession.frameSequence || 0}</span><span>Decisión DQN #{liveSession.decisionSequence || liveSession.sequence || 0}</span></div>}
      </article>
    </section>
  );
}
