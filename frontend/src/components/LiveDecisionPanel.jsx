const BRANCHES = [['north', 'N'], ['east', 'E'], ['south', 'S'], ['west', 'O']];

export default function LiveDecisionPanel({ snapshot, decisions = [] }) {
  const intersections = snapshot?.intersections || {};
  const ids = Object.keys(intersections);
  if (!ids.length) return null;
  return (
    <section className="panel decisions-panel">
      <div className="section-heading"><div><small>CONTROL</small><h2>Decisiones que está ejecutando el DQN</h2></div><p>“Pidió” es la fase elegida por la red; “actual” es lo que el controlador puede ejecutar respetando verde mínimo y amarillo.</p></div>
      <div className="decision-cards">
        {ids.map((id) => {
          const state = intersections[id];
          return <article key={id} className={`decision-card ${String(state.mode).toLowerCase()}`}>
            <header><div><small>{id}</small><h3>{state.label}</h3></div><strong>F{state.phaseIndex}</strong></header>
            <div className="phase-explanation"><span>DQN pidió <b>F{state.requestedPhase}</b></span><span>Controlador <b>{state.mode === 'YELLOW' ? 'AMARILLO' : `F${state.phaseIndex} VERDE`}</b></span></div>
            <div className="signal-mini-row">
              {BRANCHES.map(([branch, short]) => <div key={branch}><b>{short}</b><i className={String(state.signals?.[branch] || 'RED').toLowerCase()}/></div>)}
            </div>
            <footer><span>{state.activeMovements?.length || 0} movimientos activos</span><span>reward {Number(state.reward || 0).toFixed(2)}</span></footer>
          </article>;
        })}
      </div>
      {decisions.length > 0 && <div className="decision-history"><strong>Últimas acciones:</strong>{decisions.slice(-10).map((decision) => <code key={decision.sequence}>#{decision.sequence} {Object.entries(decision.actions || {}).map(([id, phase]) => `${id}=F${phase}`).join(' · ')}</code>)}</div>}
    </section>
  );
}
