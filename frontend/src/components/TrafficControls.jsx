function durationLabel(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value)) return '—';
  if (value < 60) return `${value} s`;
  return `${(value / 60).toFixed(value % 60 ? 1 : 0)} min`;
}

export default function TrafficControls({
  values, clingoFile, onFile, onClearFile, onChange, onPreset,
  onValidate, onTrain, onStartLive, onStopLive,
  topologyReady, trainedRunId, job, topologyBusy, liveSession, connectionStatus,
}) {
  const training = job?.operation === 'train' && ['pending', 'running'].includes(job.status);
  const live = ['starting', 'running', 'stopping'].includes(liveSession?.status);

  return (
    <section className="control-grid">
      <article className={`step-card ${topologyReady ? 'ready' : ''}`}>
        <div className="step-title"><span>1</span><div><small>CLINGO</small><h2>Cargar reglas</h2></div></div>
        <p>Define qué movimientos pueden compartir verde. El DQN nunca puede saltarse estas reglas.</p>
        <label className="file-picker">
          <input type="file" accept=".lp,text/plain" onChange={(event) => onFile(event.target.files?.[0] || null)} />
          <strong>{clingoFile?.name || 'Elegir archivo .lp'}</strong>
          <span>{clingoFile ? `${(clingoFile.size / 1024).toFixed(1)} KB` : 'Opcional · usa rules.lp si no eliges uno'}</span>
        </label>
        {clingoFile && <button className="link-button" type="button" onClick={onClearFile}>Quitar archivo</button>}
        <button className="action-button" type="button" onClick={onValidate} disabled={topologyBusy || training || live}>
          {topologyBusy ? 'Validando…' : topologyReady ? '✓ Topología válida · volver a validar' : 'Validar con Clingo'}
        </button>
      </article>

      <article className={`step-card ${trainedRunId ? 'ready' : ''}`}>
        <div className="step-title"><span>2</span><div><small>DQN</small><h2>Entrenar los dos agentes</h2></div></div>
        <p>Ambos cruces practican sobre el mismo simulador microscópico que luego verás en pantalla.</p>
        <div className="preset-buttons">
          <button type="button" onClick={() => onPreset(3, 120)}>Prueba<br/><small>3 × 2 min</small></button>
          <button type="button" onClick={() => onPreset(10, 300)}>Demo<br/><small>10 × 5 min</small></button>
          <button type="button" onClick={() => onPreset(50, 600)}>Largo<br/><small>50 × 10 min</small></button>
        </div>
        <div className="field-row">
          <label><span>Episodios</span><input name="episodes" type="number" min="1" max="10000" value={values.episodes} onChange={onChange}/></label>
          <label><span>Segundos / episodio</span><input name="trainSeconds" type="number" min="30" max="86400" value={values.trainSeconds} onChange={onChange}/></label>
        </div>
        <div className="mini-summary">Total: <strong>{values.episodes} episodios</strong> · {durationLabel(values.trainSeconds)} simulados cada uno</div>
        <button className="action-button" type="button" onClick={onTrain} disabled={!topologyReady || training || live}>
          {training ? 'Entrenando DQN…' : 'Entrenar y guardar modelo'}
        </button>
        {trainedRunId && <div className="run-chip"><span>Checkpoint</span><code>{trainedRunId}</code></div>}
      </article>

      <article className={`step-card live-card ${live ? 'running' : ''}`}>
        <div className="step-title"><span>3</span><div><small>REPRODUCCIÓN</small><h2>Simular el modelo</h2></div></div>
        <p>El checkpoint decide cada 5 s. Entre decisiones, la física avanza y se dibuja cada 0,2 s.</p>
        <div className="field-row">
          <label><span>Duración de cada ciclo</span><input name="cycleSeconds" type="number" min="60" max="86400" value={values.cycleSeconds} onChange={onChange}/></label>
          <label><span>Velocidad</span><select name="realTimeFactor" value={values.realTimeFactor} onChange={onChange}><option value="0.5">0,5×</option><option value="1">1× tiempo real</option><option value="2">2×</option><option value="4">4×</option></select></label>
        </div>
        {!live ? (
          <button className="live-button" type="button" onClick={onStartLive} disabled={!trainedRunId || training || !topologyReady}>
            <i/> Iniciar simulación
          </button>
        ) : (
          <button className="stop-button" type="button" onClick={onStopLive} disabled={liveSession?.status === 'stopping'}>■ Detener simulación</button>
        )}
        <div className="stream-line">
          <span className={`stream-dot ${connectionStatus}`}/>
          <span>{connectionStatus === 'live' ? 'Frames SSE en vivo' : connectionStatus === 'fallback' ? 'Modo respaldo' : connectionStatus === 'connecting' ? 'Conectando…' : 'Sin transmisión'}</span>
          {liveSession && <><b>Frame {liveSession.frameSequence || 0}</b><b>Decisión {liveSession.decisionSequence || 0}</b></>}
        </div>
      </article>
    </section>
  );
}
