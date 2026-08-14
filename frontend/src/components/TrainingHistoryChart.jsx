import { useMemo, useState } from 'react';

const OPTIONS = {
  reward: { label: 'Reward total', value: (row) => Number(row.totalReward || 0) },
  loss: { label: 'Loss promedio', value: (row) => { const values = Object.values(row.loss || {}).map(Number); return values.length ? values.reduce((a,b) => a+b,0)/values.length : 0; } },
  bunching: { label: 'Bunching', value: (row) => Number(row.bunchingEvents || 0) },
  epsilon: { label: 'Epsilon', value: (row) => { const values = Object.values(row.epsilon || {}).map(Number); return values.length ? values.reduce((a,b) => a+b,0)/values.length : 0; } },
};

export default function TrainingHistoryChart({ history }) {
  const [mode, setMode] = useState('reward');
  const points = useMemo(() => (history || []).map((row) => ({ x: Number(row.episode), y: OPTIONS[mode].value(row) })), [history, mode]);
  if (!points.length) return null;
  const width=820, height=260, left=56, right=20, top=20, bottom=38;
  let min=Math.min(...points.map(p=>p.y)), max=Math.max(...points.map(p=>p.y));
  if (min===max) { min-=1; max+=1; }
  const x=(value)=>left+((value-1)/Math.max(1,points.length-1))*(width-left-right);
  const y=(value)=>top+(1-(value-min)/(max-min))*(height-top-bottom);
  const path=points.map((p,i)=>`${i?'L':'M'} ${x(p.x)} ${y(p.y)}`).join(' ');
  return <section className="panel training-panel">
    <div className="section-heading"><div><small>ENTRENAMIENTO</small><h2>¿El modelo está aprendiendo?</h2></div><div className="chart-tabs">{Object.entries(OPTIONS).map(([key,item])=><button key={key} className={mode===key?'active':''} onClick={()=>setMode(key)}>{item.label}</button>)}</div></div>
    <svg className="learning-chart" viewBox={`0 0 ${width} ${height}`}>
      {[0,.25,.5,.75,1].map(r=>{const yy=top+r*(height-top-bottom); const val=max-r*(max-min); return <g key={r}><line x1={left} x2={width-right} y1={yy} y2={yy}/><text x={left-8} y={yy+4} textAnchor="end">{val.toFixed(1)}</text></g>})}
      <path d={path}/>{points.map(p=><circle key={p.x} cx={x(p.x)} cy={y(p.y)} r="4"><title>Episodio {p.x}: {p.y.toFixed(3)}</title></circle>)}
    </svg>
  </section>;
}
