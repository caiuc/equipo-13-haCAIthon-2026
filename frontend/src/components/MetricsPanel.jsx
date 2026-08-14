function number(value, digits = 1) {
  return Number.isFinite(Number(value))
    ? Number(value).toFixed(digits)
    : '—';
}

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;

  const simulation = metrics.simulation || {};
  const publicTransport = metrics.public_transport || {};
  const traffic = metrics.general_traffic || {};
  const signals = metrics.signal_control || {};

  const phaseChanges = Object.values(
    signals.phase_changes || {},
  ).reduce(
    (total, value) => total + Number(value || 0),
    0,
  );

  const cards = [
    [
      'En circulación',
      simulation.active_vehicles,
      'Vehículos activos',
    ],
    [
      'Autos completados',
      simulation.completed_cars,
      'Llegaron a destino',
    ],
    [
      'Micros completadas',
      simulation.completed_buses,
      'Fin de recorrido',
    ],
    [
      'Bunching',
      publicTransport.bunching_events,
      'Eventos detectados',
    ],
    [
      'Headway medio',
      `${number(publicTransport.mean_headway_s)} s`,
      'Entre micros',
    ],
    [
      'Headway crítico',
      `${number(
        publicTransport.headways_below_critical_pct,
      )} %`,
      'Separaciones críticas',
    ],
    [
      'En cola',
      traffic.queue_vehicles,
      'Casi detenidos',
    ],
    [
      'Velocidad media',
      `${number(traffic.mean_speed_mps)} m/s`,
      'Tráfico activo',
    ],
  ];

  return (
    <section className="panel metrics-panel">
      <div className="section-heading">
        <div>
          <small>TELEMETRÍA</small>
          <h2>Estado actual</h2>
        </div>

        <p>
          {number(simulation.time_s)} s · {phaseChanges}{' '}
          cambios de fase
        </p>
      </div>

      <div className="metric-grid">
        {cards.map(([label, value, help]) => (
          <article key={label}>
            <span>{label}</span>
            <strong>{value ?? '—'}</strong>
            <small>{help}</small>
          </article>
        ))}
      </div>
    </section>
  );
}