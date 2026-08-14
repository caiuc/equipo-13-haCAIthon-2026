import { useMemo, useState } from 'react';

const BRANCH_VECTOR = {
  north: { x: 0, y: -1, label: 'N' },
  east: { x: 1, y: 0, label: 'E' },
  south: { x: 0, y: 1, label: 'S' },
  west: { x: -1, y: 0, label: 'O' },
};

function bounds(nodes = {}) {
  const list = Object.values(nodes);
  if (!list.length) return { x: -700, y: -480, width: 1400, height: 960 };
  const xs = list.map((node) => Number(node.x));
  const ys = list.map((node) => Number(node.y));
  const minX = Math.min(...xs) - 105;
  const maxX = Math.max(...xs) + 105;
  const minY = Math.min(...ys) - 105;
  const maxY = Math.max(...ys) + 105;
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

function segmentKey(a, b) {
  const first = `${Number(a.x).toFixed(2)},${Number(a.y).toFixed(2)}`;
  const second = `${Number(b.x).toFixed(2)},${Number(b.y).toFixed(2)}`;
  return [first, second].sort().join('|');
}

function uniqueRoads(network) {
  const found = new Map();
  Object.entries(network.links || {}).forEach(([id, link]) => {
    const from = network.nodes?.[link.from];
    const to = network.nodes?.[link.to];
    if (!from || !to) return;
    const key = segmentKey(from, to);
    if (!found.has(key)) found.set(key, { id, from, to });
  });
  return [...found.values()];
}

function shiftedLine(from, to, offset) {
  const dx = Number(to.x) - Number(from.x);
  const dy = Number(to.y) - Number(from.y);
  const length = Math.hypot(dx, dy) || 1;
  const px = -dy / length;
  const py = dx / length;
  return {
    x1: Number(from.x) + px * offset,
    y1: Number(from.y) + py * offset,
    x2: Number(to.x) + px * offset,
    y2: Number(to.y) + py * offset,
  };
}

function hash(text) {
  return [...String(text)].reduce((value, char) => ((value * 31) + char.charCodeAt(0)) >>> 0, 7);
}

function vehiclePose(vehicle, network) {
  const link = network.links?.[vehicle.linkId];
  if (!link) return { x: Number(vehicle.x), y: Number(vehicle.y), angle: 0 };
  const from = network.nodes?.[link.from];
  const to = network.nodes?.[link.to];
  if (!from || !to) return { x: Number(vehicle.x), y: Number(vehicle.y), angle: 0 };
  const dx = Number(to.x) - Number(from.x);
  const dy = Number(to.y) - Number(from.y);
  const length = Math.hypot(dx, dy) || 1;
  const px = -dy / length;
  const py = dx / length;
  const laneWithinDirection = hash(vehicle.id) % 2 === 0 ? 7 : 18;
  const carriagewayOffset = 7 + laneWithinDirection;
  return {
    x: Number(vehicle.x) + px * carriagewayOffset,
    y: Number(vehicle.y) + py * carriagewayOffset,
    angle: Math.atan2(dy, dx) * (180 / Math.PI),
  };
}

function stopPose(stop, network) {
  const link = network.links?.[stop.link];
  if (!link) return null;
  const from = network.nodes?.[link.from];
  const to = network.nodes?.[link.to];
  if (!from || !to) return null;
  const fraction = Math.max(0, Math.min(1, Number(stop.position_m || 0) / Math.max(1, Number(link.length_m || 1))));
  const dx = Number(to.x) - Number(from.x);
  const dy = Number(to.y) - Number(from.y);
  const length = Math.hypot(dx, dy) || 1;
  const px = -dy / length;
  const py = dx / length;
  return {
    x: Number(from.x) + dx * fraction + px * 31,
    y: Number(from.y) + dy * fraction + py * 31,
    angle: Math.atan2(dy, dx) * (180 / Math.PI),
  };
}

function SignalHead({ x, y, branch, state = 'RED' }) {
  const color = String(state).toUpperCase();
  return (
    <g className="traffic-head" transform={`translate(${x} ${y})`}>
      <rect x="-9" y="-22" width="18" height="44" rx="7" />
      <circle className={`bulb red ${color === 'RED' ? 'on' : ''}`} cx="0" cy="-12" r="5" />
      <circle className={`bulb yellow ${color === 'YELLOW' ? 'on' : ''}`} cx="0" cy="0" r="5" />
      <circle className={`bulb green ${color === 'GREEN' ? 'on' : ''}`} cx="0" cy="12" r="5" />
      <text x="0" y="34" textAnchor="middle">{BRANCH_VECTOR[branch]?.label || branch}</text>
    </g>
  );
}

function movementPath(node, fromBranch, toBranch) {
  const from = BRANCH_VECTOR[fromBranch];
  const to = BRANCH_VECTOR[toBranch];
  if (!from || !to) return '';
  const radius = 43;
  const x1 = Number(node.x) + from.x * radius;
  const y1 = Number(node.y) + from.y * radius;
  const x2 = Number(node.x) + to.x * radius;
  const y2 = Number(node.y) + to.y * radius;
  return `M ${x1} ${y1} Q ${node.x} ${node.y} ${x2} ${y2}`;
}

function signalPosition(node, branch) {
  const positions = {
    north: { x: Number(node.x) + 47, y: Number(node.y) - 64 },
    east: { x: Number(node.x) + 64, y: Number(node.y) + 47 },
    south: { x: Number(node.x) - 47, y: Number(node.y) + 64 },
    west: { x: Number(node.x) - 64, y: Number(node.y) - 47 },
  };
  return positions[branch];
}

function statusLabel(status) {
  return ({ normal: 'Normal', adelantado: 'Adelantado', atrasado: 'Atrasado', riesgo_bunching: 'Riesgo de bunching', critico_bunching: 'Bunching crítico' })[status] || status || 'Normal';
}

export default function NetworkVisualization({ snapshot, topology, liveStatus = 'idle', connectionStatus = 'closed', streamInfo, frameSequence = 0 }) {
  const [selected, setSelected] = useState(null);
  const staticNetwork = topology?.network;
  const network = snapshot?.nodes ? snapshot : staticNetwork;
  const view = useMemo(() => bounds(network?.nodes), [network?.nodes]);
  const roads = useMemo(() => network ? uniqueRoads(network) : [], [network]);

  if (!network?.nodes || !network?.links) {
    return <div className="sim-empty"><strong>La simulación aparecerá aquí</strong><span>Valida Clingo para cargar los dos cruces.</span></div>;
  }

  const intersectionConfig = snapshot?.intersectionsConfig || network.intersections || {};
  const states = snapshot?.intersections || {};
  const vehicles = snapshot?.vehicles || [];
  const buses = vehicles.filter((vehicle) => vehicle.kind === 'BUS');
  const cars = vehicles.filter((vehicle) => vehicle.kind !== 'BUS');
  const dtS = Number(streamInfo?.simulationDtS || 0.2);
  const realTimeFactor = Number(streamInfo?.realTimeFactor || 1);
  const frameMs = Math.max(35, (dtS / Math.max(realTimeFactor, 0.01)) * 1000);
  const streamLive = liveStatus === 'running' && ['live', 'fallback'].includes(connectionStatus);
  const transportLabel = connectionStatus === 'fallback' ? 'RESPALDO 250 ms' : 'SSE';

  return (
    <div className="city-sim-shell">
      <div className="sim-toolbar">
        <div className="sim-live-title"><span className={`live-led ${streamLive ? 'running' : liveStatus}`} /><strong>{streamLive ? 'TRÁFICO EN TIEMPO REAL' : liveStatus === 'running' ? 'RECIBIENDO SIMULACIÓN…' : 'VISTA DE LA RED'}</strong>{streamLive && <em>{transportLabel}</em>}</div>
        <div className="sim-counters"><span><b>{cars.length}</b> autos</span><span><b>{buses.length}</b> buses</span><span><b>{Number(snapshot?.timeS || 0).toFixed(1)} s</b> simulados</span>{liveStatus === 'running' && <span><b>#{frameSequence}</b> frame</span>}{streamLive && <span><b>{realTimeFactor.toFixed(1)}×</b> reloj</span>}</div>
      </div>

      <div className="city-sim-stage">
        {streamLive && <div className="realtime-overlay"><span className="pulse-dot" /><strong>EN TIEMPO REAL</strong><small>dt {dtS.toFixed(1)} s · DQN cada {Number(streamInfo?.decisionIntervalS || 5).toFixed(0)} s</small></div>}
        <svg className="city-sim" style={{ '--frame-ms': `${frameMs}ms` }} viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`} role="img" aria-label="Dos intersecciones semaforizadas conectadas en tiempo real">
          <defs>
            <filter id="signalGlow"><feGaussianBlur stdDeviation="4" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            <marker id="movementArrowGreen" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#69e2ab" /></marker>
            <marker id="movementArrowYellow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#ffd365" /></marker>
          </defs>

          <rect className="city-ground" x={view.x} y={view.y} width={view.width} height={view.height} />
          {roads.map((road) => {
            const laneA = shiftedLine(road.from, road.to, -15);
            const laneB = shiftedLine(road.from, road.to, 15);
            return (
              <g key={road.id} className="road-group">
                <line className="road-edge" x1={road.from.x} y1={road.from.y} x2={road.to.x} y2={road.to.y} />
                <line className="road-bed" x1={road.from.x} y1={road.from.y} x2={road.to.x} y2={road.to.y} />
                <line className="road-center" x1={road.from.x} y1={road.from.y} x2={road.to.x} y2={road.to.y} />
                <line className="lane-divider" {...laneA} />
                <line className="lane-divider" {...laneB} />
              </g>
            );
          })}

          {Object.entries(network.stops || {}).map(([id, stop]) => {
            const pose = stopPose(stop, network);
            if (!pose) return null;
            return <g key={id} className="bus-stop" transform={`translate(${pose.x} ${pose.y}) rotate(${pose.angle})`} onClick={() => setSelected({ type: 'stop', id, ...stop })}><rect x="-8" y="-6" width="16" height="12" rx="3" /><line x1="0" y1="-6" x2="0" y2="-18" /><circle cx="0" cy="-21" r="4" /></g>;
          })}

          {Object.entries(network.nodes).filter(([, node]) => node.kind === 'intersection').map(([id, node]) => {
            const state = states[id] || {};
            const config = intersectionConfig[id] || {};
            return (
              <g key={id} className="intersection-group" onClick={() => setSelected({ type: 'intersection', id, state, config })}>
                <rect className="intersection-asphalt" x={Number(node.x) - 39} y={Number(node.y) - 39} width="78" height="78" rx="4" />
                <rect className="intersection-border" x={Number(node.x) - 39} y={Number(node.y) - 39} width="78" height="78" rx="4" />
                {(state.activeMovements || []).map((movement) => {
                  const [lane, toBranch] = String(movement).split('->');
                  const fromBranch = config.incoming_lanes?.[lane]?.branch;
                  const path = movementPath(node, fromBranch, toBranch);
                  return path ? <path key={movement} className={`active-movement ${state.mode === 'YELLOW' ? 'yellow' : ''}`} d={path} markerEnd={state.mode === 'YELLOW' ? 'url(#movementArrowYellow)' : 'url(#movementArrowGreen)'} /> : null;
                })}
                {Object.keys(config.branches || { north: {}, east: {}, south: {}, west: {} }).map((branch) => {
                  const pos = signalPosition(node, branch);
                  return <SignalHead key={branch} x={pos.x} y={pos.y} branch={branch} state={state.branchSignals?.[branch] || 'RED'} />;
                })}
                <g className="intersection-label" transform={`translate(${node.x} ${Number(node.y) - 55})`}>
                  <rect x="-42" y="-13" width="84" height="22" rx="8" />
                  <text textAnchor="middle" y="2">{config.label || id} · F{state.phaseIndex ?? '—'}</text>
                </g>
              </g>
            );
          })}

          {vehicles.map((vehicle) => {
            const pose = vehiclePose(vehicle, network);
            const isBus = vehicle.kind === 'BUS';
            const routeClass = isBus ? `route-${String(vehicle.routeId || '').toLowerCase()}` : '';
            return (
              <g
                key={vehicle.id}
                className={`moving-vehicle ${isBus ? `bus-vehicle ${routeClass} status-${vehicle.status || 'normal'}` : 'car-vehicle'}`}
                style={{ transform: `translate(${pose.x}px, ${pose.y}px) rotate(${pose.angle}deg)` }}
                onClick={() => setSelected({ type: 'vehicle', ...vehicle })}
              >
                {isBus ? <><rect x="-11" y="-5.5" width="22" height="11" rx="3" /><rect className="vehicle-window" x="-5" y="-3.5" width="8" height="7" rx="1" /><circle cx="-6" cy="6" r="2" /><circle cx="7" cy="6" r="2" /></> : <><rect x="-6" y="-3.5" width="12" height="7" rx="2.5" /><rect className="vehicle-window" x="-1" y="-2.5" width="4" height="5" rx="1" /></>}
              </g>
            );
          })}
        </svg>

        <div className="sim-legend"><span><i className="legend-car" /> Auto</span><span><i className="legend-b1" /> Bus B1 →</span><span><i className="legend-b2" /> Bus B2 ←</span><span><i className="legend-stop" /> Paradero</span></div>
        <div className="signal-legend"><span><i className="red" /> Rojo</span><span><i className="yellow" /> Amarillo</span><span><i className="green" /> Verde</span></div>

        {selected && <aside className="sim-inspector"><button type="button" onClick={() => setSelected(null)}>×</button>{selected.type === 'vehicle' && <><span className="eyebrow">{selected.kind === 'BUS' ? 'Bus' : 'Auto'}</span><h3>{selected.id}</h3><dl><div><dt>Velocidad</dt><dd>{Number(selected.speedMps || 0).toFixed(1)} m/s</dd></div><div><dt>Tramo</dt><dd>{selected.linkId}</dd></div>{selected.kind === 'BUS' && <div><dt>Recorrido</dt><dd>{selected.routeId}</dd></div>}{selected.kind === 'BUS' && <div><dt>Estado</dt><dd>{statusLabel(selected.status)}</dd></div>}{selected.kind === 'BUS' && <div><dt>Headway</dt><dd>{selected.headwayS == null ? '—' : `${Number(selected.headwayS).toFixed(0)} s`}</dd></div>}</dl></>}{selected.type === 'intersection' && <><span className="eyebrow">Intersección</span><h3>{selected.config.label || selected.id}</h3><dl><div><dt>Fase actual</dt><dd>F{selected.state.phaseIndex ?? '—'}</dd></div><div><dt>DQN pidió</dt><dd>F{selected.state.selectedPhase ?? '—'}</dd></div><div><dt>Modo</dt><dd>{selected.state.mode || '—'}</dd></div><div><dt>Tiempo</dt><dd>{Number(selected.state.elapsedS || 0).toFixed(1)} s</dd></div></dl></>}{selected.type === 'stop' && <><span className="eyebrow">Paradero</span><h3>{selected.id}</h3><p>{selected.routes?.join(', ')}</p></>}</aside>}
      </div>
    </div>
  );
}
