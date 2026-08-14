function Metric({ label, value, suffix = '' }) {
  const printable = typeof value === 'number'
    ? (Number.isInteger(value) ? value : value.toFixed(2))
    : value ?? '—';
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{printable}{printable !== '—' ? suffix : ''}</strong>
    </div>
  );
}

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;
  const transit = metrics.public_transport || {};
  const traffic = metrics.general_traffic || {};
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Resultado</span>
          <h2>Métricas prioritarias</h2>
        </div>
      </div>
      <div className="metrics-grid">
        <Metric label="Eventos de bunching" value={transit.bunching_events} />
        <Metric label="Headway promedio" value={transit.mean_headway_s} suffix=" s" />
        <Metric label="Desv. headway" value={transit.headway_std_s} suffix=" s" />
        <Metric label="Headways críticos" value={transit.headways_below_critical_pct} suffix="%" />
        <Metric label="Viaje medio buses" value={transit.mean_travel_time_s} suffix=" s" />
        <Metric label="Espera media buses" value={transit.mean_waiting_time_s} suffix=" s" />
        <Metric label="Flujo red" value={traffic.network_flow_veh_per_hour} suffix=" veh/h" />
        <Metric label="Cola activa" value={traffic.active_queue_length} />
      </div>
    </section>
  );
}
