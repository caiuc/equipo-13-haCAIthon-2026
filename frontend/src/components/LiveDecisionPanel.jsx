const BRANCHES = [['north', 'N'], ['east', 'E'], ['south', 'S'], ['west', 'O']];

function rewardTotal(components) {
  return Object.values(components || {}).reduce((sum, value) => sum + (Number(value) || 0), 0);
}

function modeText(mode) {
  return mode === 'YELLOW' ? 'Transición amarilla' : 'Fase verde activa';
}

export default function LiveDecisionPanel({ snapshot, decisions = [], sessionStatus }) {
  const intersections = snapshot?.intersections || {};
  const configs = snapshot?.intersectionsConfig || {};
  const ids = Object.keys(intersections);
  if (!ids.length) return null;

  return (
    <section className="decision-section panel">
      <div className="panel-heading">
        <div><span className="eyebrow">Decisiones del modelo</span><h2>Qué está haciendo cada agente ahora</h2><p className="section-description">La acción DQN selecciona una fase legal; el controlador impone mínimo de verde y transición amarilla.</p></div>
        <span className={`live-status-badge ${sessionStatus || 'idle'}`}><i />{sessionStatus === 'running' ? 'DQN en vivo' : 'Estado actual'}</span>
      </div>
      <div className="decision-grid">
        {ids.map((id) => {
          const state = intersections[id];
          const label = configs[id]?.label || id;
          return (
            <article className={`decision-card ${state.mode?.toLowerCase()}`} key={id}>
              <div className="decision-card-head"><div><span>{label}</span><strong>{id}</strong></div><span className="phase-number">F{state.phaseIndex}</span></div>
              <div className="decision-message"><strong>DQN pidió fase {state.selectedPhase}</strong><span>{modeText(state.mode)} · {Number(state.elapsedS || 0).toFixed(1)} s</span></div>
              <div className="branch-mini-signals">
                {BRANCHES.map(([branch, short]) => <div key={branch}><span>{short}</span><i className={`mini-signal ${String(state.branchSignals?.[branch] || 'RED').toLowerCase()}`} /></div>)}
              </div>
              <div className="decision-stats"><span>Movimientos activos <strong>{state.activeMovements?.length || 0}</strong></span><span>Recompensa <strong>{rewardTotal(state.rewardComponents).toFixed(2)}</strong></span></div>
              <div className="active-movement-list">{(state.activeMovements || []).slice(0, 6).map((movement) => <code key={movement}>{movement}</code>)}</div>
            </article>
          );
        })}
      </div>
      {decisions.length > 0 && <div className="decision-log"><div className="decision-log-title"><strong>Últimas decisiones</strong><span>más reciente a la derecha</span></div><div className="decision-log-track">{decisions.slice(-16).map((item) => <div className="decision-tick" key={`${item.sequence}-${item.timeS}`} title={`t=${item.timeS}s`}><span>#{item.sequence}</span><strong>{Object.entries(item.actions || {}).map(([id, phase]) => `${id}:F${phase}`).join(' · ')}</strong></div>)}</div></div>}
    </section>
  );
}
