export default function TopologyPanel({ topology }) {
  if (!topology?.intersections) return null;
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Clingo</span>
          <h2>Fases legales derivadas</h2>
        </div>
      </div>
      <div className="intersection-grid">
        {Object.entries(topology.intersections).map(([intersectionId, data]) => (
          <article className="intersection-card" key={intersectionId}>
            <h3>{intersectionId}</h3>
            <p>{data.movements.length} movimientos · {data.conflicts.length} conflictos · {data.phases.length} fases</p>
            <ol>
              {data.phases.map((phase) => (
                <li key={phase.index}>
                  <strong>Fase {phase.index}</strong>
                  <span>{phase.movements.join(', ') || 'sin movimientos'}</span>
                </li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}
