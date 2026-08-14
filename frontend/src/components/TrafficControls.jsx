export default function TrafficControls({
  scenarios,
  values,
  onChange,
  onTopology,
  onSimulate,
  onTrain,
  onEvaluate,
  busy,
}) {
  return (
    <section className="panel controls-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Escenario</span>
          <h2>Control de ejecución</h2>
        </div>
        {busy && <span className="status-pill running">Ejecutando</span>}
      </div>

      <div className="form-grid">
        <label>
          Escenario
          <select name="scenario" value={values.scenario} onChange={onChange} disabled={busy}>
            {scenarios.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          Segundos por episodio
          <input name="seconds" type="number" min="5" value={values.seconds} onChange={onChange} disabled={busy} />
        </label>
        <label>
          Episodios DQN
          <input name="episodes" type="number" min="1" value={values.episodes} onChange={onChange} disabled={busy} />
        </label>
        <label>
          Run ID para evaluar
          <input
            name="checkpointRunId"
            placeholder="UUID del entrenamiento"
            value={values.checkpointRunId}
            onChange={onChange}
            disabled={busy}
          />
        </label>
      </div>

      <div className="button-row">
        <button className="button secondary" type="button" onClick={onTopology} disabled={busy}>Topología Clingo</button>
        <button className="button" type="button" onClick={onSimulate} disabled={busy}>Simular baseline</button>
        <button className="button" type="button" onClick={onTrain} disabled={busy}>Entrenar DQN</button>
        <button className="button secondary" type="button" onClick={onEvaluate} disabled={busy || !values.checkpointRunId}>Evaluar DQN</button>
      </div>
    </section>
  );
}
