function number(value, digits=1) { return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—'; }

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;
  const sim=metrics.simulation || {}, pt=metrics.public_transport || {}, traffic=metrics.general_traffic || {}, signals=metrics.signal_control || {};
  const cards=[
    ['Vehículos activos', sim.active_vehicles, 'Ahora mismo en la red'],
    ['Autos completados', sim.completed_cars, 'Llegaron a destino'],
    ['Buses completados', sim.completed_buses, 'Recorridos terminados'],
    ['Bunching', pt.bunching_events, 'Eventos críticos detectados'],
    ['Headway medio', `${number(pt.mean_headway_s)} s`, 'Separación estimada entre buses'],
    ['Headway crítico', `${number(pt.headways_below_critical_pct)} %`, 'Menor es mejor'],
    ['Cola actual', traffic.queue_vehicles, 'Vehículos casi detenidos'],
    ['Velocidad media', `${number(traffic.mean_speed_mps)} m/s`, 'Tráfico activo'],
  ];
  return <section className="panel metrics-panel">
    <div className="section-heading"><div><small>TELEMETRÍA</small><h2>Estado de la red</h2></div><p>t = {number(sim.time_s)} s · cambios de fase: {Object.values(signals.phase_changes || {}).reduce((a,b)=>a+Number(b||0),0)}</p></div>
    <div className="metric-grid">{cards.map(([label,value,help])=><article key={label}><span>{label}</span><strong>{value ?? '—'}</strong><small>{help}</small></article>)}</div>
  </section>;
}
