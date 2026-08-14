import { useMemo, useState } from 'react';

const OPTIONS = {
  reward: {
    label: 'Recompensa',
    value: (row) => Number(row.totalReward || 0),
  },

  loss: {
    label: 'Pérdida',
    value: (row) => {
      const values = Object.values(row.loss || {}).map(Number);

      return values.length
        ? values.reduce((a, b) => a + b, 0) / values.length
        : 0;
    },
  },

  bunching: {
    label: 'Bunching',
    value: (row) => Number(row.bunchingEvents || 0),
  },

  epsilon: {
    label: 'Exploración',
    value: (row) => {
      const values = Object.values(row.epsilon || {}).map(Number);

      return values.length
        ? values.reduce((a, b) => a + b, 0) / values.length
        : 0;
    },
  },
};

export default function TrainingHistoryChart({ history }) {
  const [mode, setMode] = useState('reward');

  const points = useMemo(
    () =>
      (history || []).map((row) => ({
        x: Number(row.episode),
        y: OPTIONS[mode].value(row),
      })),
    [history, mode],
  );

  if (!points.length) return null;

  const width = 820;
  const height = 260;
  const left = 56;
  const right = 20;
  const top = 20;
  const bottom = 38;

  let min = Math.min(...points.map((p) => p.y));
  let max = Math.max(...points.map((p) => p.y));

  if (min === max) {
    min -= 1;
    max += 1;
  }

  const x = (value) =>
    left +
    ((value - 1) / Math.max(1, points.length - 1)) *
      (width - left - right);

  const y = (value) =>
    top +
    (1 - (value - min) / (max - min)) *
      (height - top - bottom);

  const path = points
    .map(
      (point, index) =>
        `${index ? 'L' : 'M'} ${x(point.x)} ${y(point.y)}`,
    )
    .join(' ');

  return (
    <section className="panel training-panel">
      <div className="section-heading">
        <div>
          <small>ENTRENAMIENTO</small>
          <h2>Evolución del modelo</h2>
        </div>

        <div className="chart-tabs">
          {Object.entries(OPTIONS).map(([key, item]) => (
            <button
              key={key}
              type="button"
              className={mode === key ? 'active' : ''}
              onClick={() => setMode(key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <svg
        className="learning-chart"
        viewBox={`0 0 ${width} ${height}`}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const yy =
            top + ratio * (height - top - bottom);

          const value =
            max - ratio * (max - min);

          return (
            <g key={ratio}>
              <line
                x1={left}
                x2={width - right}
                y1={yy}
                y2={yy}
              />

              <text
                x={left - 8}
                y={yy + 4}
                textAnchor="end"
              >
                {value.toFixed(1)}
              </text>
            </g>
          );
        })}

        <path d={path} />

        {points.map((point) => (
          <circle
            key={point.x}
            cx={x(point.x)}
            cy={y(point.y)}
            r="4"
          >
            <title>
              Episodio {point.x}: {point.y.toFixed(3)}
            </title>
          </circle>
        ))}
      </svg>
    </section>
  );
}