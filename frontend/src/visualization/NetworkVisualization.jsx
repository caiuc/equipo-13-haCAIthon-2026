function bounds(nodes) {
  const values = Object.values(nodes || {});
  if (!values.length) return { minX: -1, minY: -1, width: 2, height: 2 };
  const xs = values.map((node) => Number(node.x));
  const ys = values.map((node) => Number(node.y));
  const minX = Math.min(...xs) - 70;
  const maxX = Math.max(...xs) + 70;
  const minY = Math.min(...ys) - 70;
  const maxY = Math.max(...ys) + 70;
  return { minX, minY, width: maxX - minX, height: maxY - minY };
}

function stopPosition(stop, links, nodes) {
  const link = links?.[stop.link];
  if (!link) return null;
  const from = nodes?.[link.from];
  const to = nodes?.[link.to];
  if (!from || !to) return null;
  const fraction = Math.max(0, Math.min(1, Number(stop.position_m) / Math.max(Number(link.length_m), 1)));
  return {
    x: Number(from.x) + (Number(to.x) - Number(from.x)) * fraction,
    y: Number(from.y) + (Number(to.y) - Number(from.y)) * fraction,
  };
}

export default function NetworkVisualization({ snapshot, topology }) {
  const network = snapshot || topology?.network;
  if (!network?.nodes || !network?.links) {
    return <div className="empty-state">Ejecuta topología o una simulación para visualizar la red.</div>;
  }

  const view = bounds(network.nodes);
  const intersections = snapshot?.intersections || {};
  const vehicles = snapshot?.vehicles || [];

  return (
    <div className="network-wrap">
      <svg
        className="network-canvas"
        viewBox={`${view.minX} ${view.minY} ${view.width} ${view.height}`}
        role="img"
        aria-label="Red de control semafórico"
      >
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" className="road-arrow" />
          </marker>
        </defs>

        {Object.entries(network.links).map(([linkId, link]) => {
          const from = network.nodes[link.from];
          const to = network.nodes[link.to];
          if (!from || !to) return null;
          return (
            <g key={linkId}>
              <line
                className="road"
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                markerEnd="url(#arrow)"
              />
              <title>{linkId}</title>
            </g>
          );
        })}

        {Object.entries(network.stops || {}).map(([stopId, stop]) => {
          const position = stopPosition(stop, network.links, network.nodes);
          if (!position) return null;
          return (
            <g key={stopId}>
              <rect className="stop" x={position.x - 5} y={position.y - 5} width="10" height="10" rx="2" />
              <text className="map-label" x={position.x + 7} y={position.y - 7}>{stopId}</text>
            </g>
          );
        })}

        {Object.entries(network.nodes).map(([nodeId, node]) => {
          const signal = intersections[nodeId];
          const isIntersection = node.kind === 'intersection';
          return (
            <g key={nodeId}>
              <circle
                className={isIntersection ? 'node intersection-node' : 'node'}
                cx={node.x}
                cy={node.y}
                r={isIntersection ? 9 : 5}
              />
              {signal && (
                <circle
                  className={signal.mode === 'GREEN' ? 'signal signal-green' : 'signal signal-yellow'}
                  cx={Number(node.x) + 12}
                  cy={Number(node.y) - 12}
                  r="5"
                />
              )}
              <text className="map-label" x={Number(node.x) + 12} y={Number(node.y) + 18}>{nodeId}</text>
            </g>
          );
        })}

        {vehicles.map((vehicle) => (
          <g key={vehicle.id}>
            <circle
              className={vehicle.kind === 'BUS' ? `vehicle bus bus-${vehicle.status || 'normal'}` : 'vehicle car'}
              cx={vehicle.x}
              cy={vehicle.y}
              r={vehicle.kind === 'BUS' ? 7 : 3.5}
            />
            {vehicle.kind === 'BUS' && (
              <text className="vehicle-label" x={vehicle.x + 9} y={vehicle.y - 9}>{vehicle.id}</text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
