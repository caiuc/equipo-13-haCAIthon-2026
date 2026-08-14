import { useMemo, useState } from 'react';

const MODES = {
  reward: { label: 'Recompensa', help: 'Más alta suele indicar mejores decisiones globales.' },
  bunching: { label: 'Bunching', help: 'Menos eventos es mejor.' },
  loss: { label: 'Loss', help: 'Error medio de aprendizaje de los agentes.' },
};

function averageObject(values) {
  const numbers = Object.values(values || {}).filter((value) => Number.isFinite(Number(value))).map(Number);
  if (!numbers.length) return null;
  return numbers.reduce((sum, value) => sum + value, 0) / numbers.length;
}

function valueFor(row, mode) {
  if (mode === 'reward') return averageObject(row.reward);
  if (mode === 'loss') return averageObject(row.loss);
  return Number(row.bunching_events ?? 0);
}

function formatValue(value) {
  if (!Number.isFinite(value)) return '—';
  if (Math.abs(value) >= 1000) return value.toFixed(0);
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
}

export default function TrainingHistoryChart({ history }) {
  const [mode, setMode] = useState('reward');
  const points = useMemo(() => (history || [])
    .map((row) => ({ episode: Number(row.episode), value: valueFor(row, mode) }))
    .filter((point) => Number.isFinite(point.episode) && Number.isFinite(point.value)), [history, mode]);

  if (!history?.length || !points.length) return null;

  const width = 820;
  const height = 280;
  const padding = { left: 58, right: 22, top: 22, bottom: 42 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const values = points.map((point) => point.value);
  let minY = Math.min(...values);
  let maxY = Math.max(...values);
  if (minY === maxY) {
    const margin = Math.max(1, Math.abs(minY) * 0.1);
    minY -= margin;
    maxY += margin;
  }
  const yPad = (maxY - minY) * 0.08;
  minY -= yPad;
  maxY += yPad;

  const minEpisode = Math.min(...points.map((point) => point.episode));
  const maxEpisode = Math.max(...points.map((point) => point.episode));
  const xFor = (episode) => padding.left + ((episode - minEpisode) / Math.max(1, maxEpisode - minEpisode)) * chartWidth;
  const yFor = (value) => padding.top + (1 - (value - minY) / Math.max(1e-9, maxY - minY)) * chartHeight;
  const path = points.map((point, index) => `${index ? 'L' : 'M'} ${xFor(point.episode)} ${yFor(point.value)}`).join(' ');
  const last = points.at(-1);
  const first = points[0];
  const change = first && last ? last.value - first.value : 0;

  return (
    <section className="panel training-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Aprendizaje</span>
          <h2>Evolución del entrenamiento</h2>
          <p className="section-description">Cada punto corresponde a un episodio completo.</p>
        </div>
        <div className="chart-tabs">
          {Object.entries(MODES).map(([key, item]) => (
            <button key={key} type="button" className={mode === key ? 'active' : ''} onClick={() => setMode(key)}>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-summary-row">
        <div><span>Último valor</span><strong>{formatValue(last?.value)}</strong></div>
        <div>
          <span>Cambio desde episodio 1</span>
          <strong className={change > 0 ? 'trend-up' : change < 0 ? 'trend-down' : ''}>
            {change > 0 ? '+' : ''}{formatValue(change)}
          </strong>
        </div>
        <p>{MODES[mode].help}</p>
      </div>

      <div className="training-chart-wrap">
        <svg viewBox={`0 0 ${width} ${height}`} className="training-chart" role="img" aria-label={`Gráfico de ${MODES[mode].label}`}>
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = padding.top + ratio * chartHeight;
            const value = maxY - ratio * (maxY - minY);
            return (
              <g key={ratio}>
                <line className="chart-grid-line" x1={padding.left} x2={width - padding.right} y1={y} y2={y} />
                <text className="chart-axis-label" x={padding.left - 10} y={y + 4} textAnchor="end">{formatValue(value)}</text>
              </g>
            );
          })}
          <line className="chart-axis" x1={padding.left} x2={padding.left} y1={padding.top} y2={height - padding.bottom} />
          <line className="chart-axis" x1={padding.left} x2={width - padding.right} y1={height - padding.bottom} y2={height - padding.bottom} />
          {points.map((point, index) => {
            if (points.length > 12 && index % Math.ceil(points.length / 10) !== 0 && index !== points.length - 1) return null;
            return <text key={`x-${point.episode}`} className="chart-axis-label" x={xFor(point.episode)} y={height - 16} textAnchor="middle">{point.episode}</text>;
          })}
          <path className="training-line" d={path} />
          {points.map((point) => (
            <circle className="training-point" key={point.episode} cx={xFor(point.episode)} cy={yFor(point.value)} r="4">
              <title>Episodio {point.episode}: {formatValue(point.value)}</title>
            </circle>
          ))}
        </svg>
      </div>
    </section>
  );
}
