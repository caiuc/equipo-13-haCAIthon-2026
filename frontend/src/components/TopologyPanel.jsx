import { useEffect, useMemo, useState } from 'react';

export default function TopologyPanel({ topology }) {
  const intersectionIds = useMemo(() => Object.keys(topology?.intersections || {}), [topology]);
  const [selectedIntersection, setSelectedIntersection] = useState(null);
  const [selectedPhase, setSelectedPhase] = useState(0);

  useEffect(() => {
    setSelectedIntersection(intersectionIds[0] || null);
    setSelectedPhase(0);
  }, [topology, intersectionIds]);

  if (!topology?.intersections) {
    return <section className="panel empty-result-panel"><span className="eyebrow">Clingo</span><h2>Topología todavía no resuelta</h2><p>Presiona “Topología Clingo” para ver movimientos, conflictos y fases legales de cada intersección.</p></section>;
  }

  const current = topology.intersections[selectedIntersection] || topology.intersections[intersectionIds[0]];
  const phase = current?.phases?.[selectedPhase] || current?.phases?.[0];

  return (
    <section className="panel topology-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">Seguridad formal · Clingo</span><h2>Qué puede hacer legalmente cada semáforo</h2><p className="section-description">El DQN nunca inventa luces. Solo puede elegir entre estas fases derivadas por Clingo.</p></div>
        <span className="status-pill success">✓ {intersectionIds.length} intersecciones resueltas</span>
      </div>

      <div className="topology-layout">
        <div className="intersection-selector">
          {intersectionIds.map((intersectionId) => {
            const data = topology.intersections[intersectionId];
            const active = intersectionId === selectedIntersection;
            return (
              <button type="button" className={`intersection-select-card ${active ? 'active' : ''}`} key={intersectionId} onClick={() => { setSelectedIntersection(intersectionId); setSelectedPhase(0); }}>
                <span className="intersection-name">{intersectionId}</span>
                <span>{data.movements.length} mov.</span><span>{data.conflicts.length} conflictos</span><span>{data.phases.length} fases</span>
              </button>
            );
          })}
        </div>

        {current && (
          <div className="phase-explorer">
            <div className="phase-explorer-head">
              <div><span className="eyebrow">Intersección seleccionada</span><h3>{selectedIntersection}</h3></div>
              <div className="mini-stats"><span><strong>{current.movements.length}</strong> movimientos</span><span><strong>{current.conflicts.length}</strong> conflictos</span><span><strong>{current.phases.length}</strong> fases legales</span></div>
            </div>

            <div className="phase-tabs" role="tablist" aria-label="Fases legales">
              {current.phases.map((item, index) => <button type="button" role="tab" aria-selected={selectedPhase === index} className={selectedPhase === index ? 'active' : ''} key={item.index} onClick={() => setSelectedPhase(index)}>Fase {item.index}</button>)}
            </div>

            <div className="phase-detail">
              <div><span className="detail-label">Movimientos activos simultáneos</span><div className="movement-chips">{(phase?.movements || []).map((movement) => <span key={movement}>{movement}</span>)}{!phase?.movements?.length && <em>Sin movimientos activos.</em>}</div></div>
              <div><span className="detail-label">Interpretación</span><p>Todos estos movimientos pueden recibir verde al mismo tiempo porque Clingo determinó que no existe un conflicto incompatible entre ellos.</p></div>
            </div>

            <details className="conflicts-details">
              <summary>Ver conflictos derivados ({current.conflicts.length})</summary>
              <div className="conflict-list">{current.conflicts.map((conflict, index) => <span key={`${conflict.join?.('-') || String(conflict)}-${index}`}>{Array.isArray(conflict) ? conflict.join(' ↔ ') : String(conflict)}</span>)}</div>
            </details>
          </div>
        )}
      </div>
    </section>
  );
}
