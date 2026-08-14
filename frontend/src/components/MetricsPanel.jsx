const METRICS = [
  { key: 'bunching_events', section: 'public_transport', label: 'Eventos de bunching', suffix: '', lowerIsBetter: true, help: 'Veces que buses del mismo recorrido quedaron peligrosamente juntos.' },
  { key: 'critical_headway_pct', section: 'public_transport', label: 'Headways críticos', suffix: '%', lowerIsBetter: true, help: 'Porcentaje de separaciones bajo el umbral crítico.' },
  { key: 'headway_std_s', section: 'public_transport', label: 'Desv. de headway', suffix: ' s', lowerIsBetter: true, help: 'Qué tan irregular es la separación entre buses.' },
  { key: 'mean_headway_s', section: 'public_transport', label: 'Headway promedio', suffix: ' s', help: 'Separación temporal promedio entre buses.' },
  { key: 'mean_travel_time_s', section: 'public_transport', label: 'Viaje medio buses', suffix: ' s', lowerIsBetter: true, help: 'Tiempo promedio de viaje de los buses completados.' },
  { key: 'mean_waiting_time_s', section: 'public_transport', label: 'Espera media buses', suffix: ' s', lowerIsBetter: true, help: 'Tiempo promedio que los buses permanecieron detenidos.' },
  { key: 'network_flow_veh_per_hour', section: 'general_traffic', label: 'Flujo de red', suffix: ' veh/h', lowerIsBetter: false, help: 'Vehículos que la red logra procesar por hora.' },
  { key: 'active_queue_length', section: 'general_traffic', label: 'Cola activa', suffix: '', lowerIsBetter: true, help: 'Vehículos prácticamente detenidos al finalizar.' },
];

function readMetric(metrics, definition) { return metrics?.[definition.section]?.[definition.key]; }
// null/undefined significa "sin observaciones válidas" (p.ej. ningún bus completó la
// ruta), no un valor real de cero; se muestra explícitamente como N/D.
function printable(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'N/D';
  const number = Number(value);
  return Number.isInteger(number) ? String(number) : number.toFixed(2);
}
function comparison(current, baseline, lowerIsBetter) {
  if (current === null || current === undefined || baseline === null || baseline === undefined) return null;
  if (!Number.isFinite(Number(current)) || !Number.isFinite(Number(baseline))) return null;
  const c = Number(current); const b = Number(baseline);
  if (Math.abs(b) < 1e-9) return { improvement: null };
  const raw = ((c - b) / Math.abs(b)) * 100;
  return { improvement: lowerIsBetter === undefined ? null : (lowerIsBetter ? -raw : raw) };
}

function MetricCard({ definition, value, baselineValue, showComparison }) {
  const diff = showComparison ? comparison(value, baselineValue, definition.lowerIsBetter) : null;
  const improvement = diff?.improvement;
  const good = Number.isFinite(improvement) && improvement > 0.05;
  const bad = Number.isFinite(improvement) && improvement < -0.05;
  return (
    <article className="metric-card interactive-card" title={definition.help}>
      <div className="metric-topline">
        <span>{definition.label}</span>
        {showComparison && Number.isFinite(improvement) && (
          <span className={`metric-delta ${good ? 'good' : bad ? 'bad' : 'neutral'}`}>
            {good ? '▲' : bad ? '▼' : '•'} {Math.abs(improvement).toFixed(1)}%
          </span>
        )}
      </div>
      <strong>{printable(value)}{printable(value) !== '—' ? definition.suffix : ''}</strong>
      <p>{definition.help}</p>
      {showComparison && Number.isFinite(Number(baselineValue)) && (
        <div className="baseline-note">Baseline: {printable(baselineValue)}{definition.suffix}</div>
      )}
    </article>
  );
}

function ComparisonBars({ baselineMetrics, currentMetrics }) {
  const rows = METRICS.filter((metric) => metric.lowerIsBetter !== undefined).slice(0, 7);
  return (
    <div className="comparison-block">
      <div className="comparison-heading">
        <div><h3>Baseline vs DQN</h3><p>Compara la referencia con el modelo evaluado. Verde favorece al DQN.</p></div>
        <div className="comparison-legend"><span><i className="legend-swatch baseline" />Baseline</span><span><i className="legend-swatch dqn" />DQN</span></div>
      </div>
      <div className="comparison-rows">
        {rows.map((metric) => {
          const baselineRaw = readMetric(baselineMetrics, metric);
          const currentRaw = readMetric(currentMetrics, metric);
          const baseline = Number.isFinite(Number(baselineRaw)) ? Number(baselineRaw) : 0;
          const current = Number.isFinite(Number(currentRaw)) ? Number(currentRaw) : 0;
          const max = Math.max(Math.abs(baseline), Math.abs(current), 1);
          const improvement = comparison(currentRaw, baselineRaw, metric.lowerIsBetter)?.improvement;
          return (
            <div className="comparison-row" key={`${metric.section}-${metric.key}`}>
              <div className="comparison-label">
                <span>{metric.label}</span>
                {Number.isFinite(improvement) && <strong className={improvement > 0 ? 'good-text' : improvement < 0 ? 'bad-text' : ''}>{Math.abs(improvement).toFixed(1)}% {improvement >= 0 ? 'mejor' : 'peor'}</strong>}
              </div>
              <div className="bar-pair">
                <div className="comparison-track"><span className="baseline-bar" style={{ width: `${Math.max(2, Math.abs(baseline) / max * 100)}%` }} /></div>
                <div className="comparison-track"><span className="dqn-bar" style={{ width: `${Math.max(2, Math.abs(current) / max * 100)}%` }} /></div>
              </div>
              <div className="comparison-values"><span>{printable(baselineRaw)}{metric.suffix}</span><span>{printable(currentRaw)}{metric.suffix}</span></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function MetricsPanel({ metrics, baselineMetrics, mode }) {
  if (!metrics) {
    return <section className="panel empty-result-panel"><span className="eyebrow">3 · Resultados</span><h2>Aún no hay métricas</h2><p>Ejecuta un baseline, entrenamiento o evaluación y aquí aparecerán los indicadores principales.</p></section>;
  }
  const showComparison = mode === 'evaluation' && baselineMetrics;
  const simulation = metrics.simulation || {};
  return (
    <section className="panel metrics-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">3 · Resultados</span><h2>{showComparison ? '¿El DQN mejoró el baseline?' : 'Métricas prioritarias'}</h2><p className="section-description">La prioridad es reducir bunching y mejorar regularidad sin colapsar el tráfico general.</p></div>
        <div className="simulation-summary"><span>Tiempo simulado <strong>{printable(simulation.time_s)} s</strong></span><span>Generados <strong>{simulation.spawned ?? '—'}</strong></span><span>Completados <strong>{simulation.completed ?? '—'}</strong></span></div>
      </div>
      <div className="metrics-grid">
        {METRICS.map((definition) => <MetricCard key={`${definition.section}-${definition.key}`} definition={definition} value={readMetric(metrics, definition)} baselineValue={readMetric(baselineMetrics, definition)} showComparison={showComparison} />)}
      </div>
      {showComparison && <ComparisonBars baselineMetrics={baselineMetrics} currentMetrics={metrics} />}
    </section>
  );
}
