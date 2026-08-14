import { useEffect, useMemo, useRef } from 'react';

const SIGNAL_RGB = { RED: '#ff4d57', YELLOW: '#ffd54a', GREEN: '#42e878' };
const BRANCH_SHORT = { north: 'N', east: 'E', south: 'S', west: 'O' };

function uniqueRoads(network) {
  const nodes = network?.nodes || {};
  const seen = new Set();
  const roads = [];
  for (const [id, link] of Object.entries(network?.links || {})) {
    const a = nodes[link.from], b = nodes[link.to];
    if (!a || !b) continue;
    const p1 = `${a.x},${a.y}`, p2 = `${b.x},${b.y}`;
    const key = [p1,p2].sort().join('|');
    if (seen.has(key)) continue;
    seen.add(key); roads.push({ id, a, b });
  }
  return roads;
}

function boundsFor(network) {
  const values = Object.values(network?.nodes || {});
  if (!values.length) return { minX:-380,maxX:380,minY:-220,maxY:220 };
  return {
    minX: Math.min(...values.map(n=>Number(n.x))), maxX: Math.max(...values.map(n=>Number(n.x))),
    minY: Math.min(...values.map(n=>Number(n.y))), maxY: Math.max(...values.map(n=>Number(n.y))),
  };
}

function vehicleMap(snapshot) { return new Map((snapshot?.vehicles || []).map(v => [v.id, v])); }

export default function NetworkVisualization({ snapshot, topology, connectionStatus='closed', frameSequence=0 }) {
  const canvasRef = useRef(null);
  const previousRef = useRef(snapshot);
  const targetRef = useRef(snapshot);
  const receivedAtRef = useRef(performance.now());
  const topologyRef = useRef(topology);
  topologyRef.current = topology;

  useEffect(() => {
    if (!snapshot) return;
    previousRef.current = targetRef.current || snapshot;
    targetRef.current = snapshot;
    receivedAtRef.current = performance.now();
  }, [snapshot]);

  const roads = useMemo(() => uniqueRoads(topology?.network), [topology]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    let raf = 0;
    let disposed = false;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(640, rect.width);
      const height = Math.max(420, rect.height);
      if (canvas.width !== Math.round(width*dpr) || canvas.height !== Math.round(height*dpr)) {
        canvas.width = Math.round(width*dpr); canvas.height = Math.round(height*dpr);
      }
      ctx.setTransform(dpr,0,0,dpr,0,0);
      return { width, height };
    };

    const draw = (now) => {
      if (disposed) return;
      const { width, height } = resize();
      const network = topologyRef.current?.network;
      const bounds = boundsFor(network);
      const margin = 55;
      const scale = Math.min((width-2*margin)/Math.max(1,bounds.maxX-bounds.minX), (height-2*margin)/Math.max(1,bounds.maxY-bounds.minY));
      const ox = (width-(bounds.maxX-bounds.minX)*scale)/2 - bounds.minX*scale;
      const oy = (height-(bounds.maxY-bounds.minY)*scale)/2 - bounds.minY*scale;
      const screen = (x,y) => [ox+Number(x)*scale, oy+Number(y)*scale];

      ctx.clearRect(0,0,width,height);
      ctx.fillStyle='#0a1018'; ctx.fillRect(0,0,width,height);

      // Calles: una calzada con dos pistas, una por cada sentido.
      ctx.lineCap='butt';
      for (const road of roads) {
        const [x1,y1]=screen(road.a.x,road.a.y), [x2,y2]=screen(road.b.x,road.b.y);
        ctx.strokeStyle='#273241'; ctx.lineWidth=34; ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
        ctx.strokeStyle='#657081'; ctx.lineWidth=1.5; ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
        ctx.save(); ctx.setLineDash([9,9]); ctx.strokeStyle='#e6c95c'; ctx.lineWidth=1.5; ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke(); ctx.restore();
      }

      // Flechas de sentido en cada link dirigido.
      for (const link of Object.values(network?.links || {})) {
        const a=network.nodes[link.from], b=network.nodes[link.to]; if(!a||!b) continue;
        const ax=Number(a.x), ay=Number(a.y), bx=Number(b.x), by=Number(b.y);
        const dx=bx-ax, dy=by-ay, len=Math.hypot(dx,dy)||1, ux=dx/len, uy=dy/len, nx=-uy, ny=ux;
        const wx=ax+dx*.45+nx*3.2, wy=ay+dy*.45+ny*3.2; const [sx,sy]=screen(wx,wy);
        ctx.save(); ctx.translate(sx,sy); ctx.rotate(Math.atan2(dy,dx)); ctx.fillStyle='rgba(235,241,248,.55)'; ctx.beginPath(); ctx.moveTo(8,0);ctx.lineTo(-5,-4);ctx.lineTo(-5,4);ctx.closePath();ctx.fill();ctx.restore();
      }

      // Cuadrados de intersección y etiquetas.
      for (const [iid, config] of Object.entries(network?.intersections || {})) {
        const node=network.nodes[iid]; if(!node) continue; const [cx,cy]=screen(node.x,node.y); const half=12*scale;
        ctx.fillStyle='#344252'; ctx.fillRect(cx-half,cy-half,half*2,half*2);
        ctx.strokeStyle='#778394'; ctx.lineWidth=1; ctx.strokeRect(cx-half,cy-half,half*2,half*2);
        ctx.fillStyle='#eef4fb'; ctx.font='700 12px system-ui'; ctx.textAlign='center'; ctx.fillText(config.label || iid,cx,cy-half-12);
      }

      // Paraderos.
      for (const [stopId, stop] of Object.entries(network?.stops || {})) {
        const link=network.links[stop.link]; if(!link) continue; const a=network.nodes[link.from], b=network.nodes[link.to];
        const len=Number(link.length_m)||1, t=Number(stop.position_m)/len; const wx=Number(a.x)+(Number(b.x)-Number(a.x))*t, wy=Number(a.y)+(Number(b.y)-Number(a.y))*t;
        const [sx,sy]=screen(wx,wy); ctx.fillStyle='#53d4ff'; ctx.fillRect(sx-3,sy-9,6,18); ctx.fillStyle='#bdefff'; ctx.font='10px system-ui'; ctx.textAlign='left'; ctx.fillText('P',sx+6,sy-5);
      }

      const target=targetRef.current; const previous=previousRef.current || target;
      const durationMs=Math.max(80, Number(target?.trafficRules?.dtS || .2)*1000);
      const alpha=Math.max(0,Math.min(1,(now-receivedAtRef.current)/durationMs));
      const prevMap=vehicleMap(previous);

      // Líneas de detención y cabezales de 3 luces. Se usan coordenadas generadas por Python.
      for (const state of Object.values(target?.intersections || {})) {
        for (const head of state.signalHeads || []) {
          const [sx,sy]=screen(head.x,head.y); const angle=Number(head.headingDeg||0)*Math.PI/180;
          ctx.save(); ctx.translate(sx,sy); ctx.rotate(angle); ctx.strokeStyle='#ffffff'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(0,-9);ctx.lineTo(0,9);ctx.stroke(); ctx.restore();
          const off=22, px=sx+Math.cos(angle+Math.PI/2)*off, py=sy+Math.sin(angle+Math.PI/2)*off;
          ctx.save(); ctx.translate(px,py); ctx.fillStyle='#070a0e'; ctx.strokeStyle='#7d8794'; ctx.lineWidth=1; ctx.beginPath(); ctx.roundRect(-8,-24,16,48,5);ctx.fill();ctx.stroke();
          ['RED','YELLOW','GREEN'].forEach((color,index)=>{const yy=-15+index*15; ctx.beginPath();ctx.arc(0,yy,5,0,Math.PI*2);ctx.fillStyle=head.color===color?SIGNAL_RGB[color]:'#252b33';ctx.shadowColor=head.color===color?SIGNAL_RGB[color]:'transparent';ctx.shadowBlur=head.color===color?10:0;ctx.fill();ctx.shadowBlur=0;});
          ctx.fillStyle='#dce5ef';ctx.font='700 9px system-ui';ctx.textAlign='center';ctx.fillText(BRANCH_SHORT[head.branch]||head.branch,0,34); ctx.restore();
        }
      }

      // Vehículos: la coordenada recibida es el parachoques delantero.
      for (const vehicle of target?.vehicles || []) {
        const prev=prevMap.get(vehicle.id) || vehicle;
        const wx=Number(prev.x)+(Number(vehicle.x)-Number(prev.x))*alpha;
        const wy=Number(prev.y)+(Number(vehicle.y)-Number(prev.y))*alpha;
        const heading=Number(prev.headingDeg)+(Number(vehicle.headingDeg)-Number(prev.headingDeg))*alpha;
        const [sx,sy]=screen(wx,wy); const isBus=vehicle.kind==='BUS';
        const length=Math.max(isBus?24:13,Number(vehicle.lengthM||4.5)*scale);
        const bodyWidth=Math.max(isBus?9:7,Number(vehicle.widthM||1.8)*scale);
        ctx.save();ctx.translate(sx,sy);ctx.rotate(heading*Math.PI/180);
        ctx.fillStyle=isBus?(vehicle.routeId==='B2'?'#ff9f43':'#2dd4bf'):'#4da3ff';
        ctx.strokeStyle=vehicle.status==='critico_bunching'?'#ff3d4f':'#07111c';ctx.lineWidth=vehicle.status==='critico_bunching'?3:1.5;
        ctx.beginPath();ctx.roundRect(-length,-bodyWidth/2,length,bodyWidth,Math.min(4,bodyWidth/2));ctx.fill();ctx.stroke();
        if(isBus){ctx.fillStyle='rgba(235,248,255,.85)';for(let x=-length+5;x<-3;x+=7)ctx.fillRect(x,-bodyWidth/2+2,4,2);}
        ctx.restore();
        if(isBus){ctx.fillStyle='#f3f7fb';ctx.font='700 10px system-ui';ctx.textAlign='center';ctx.fillText(vehicle.id,sx,sy-11); if(Number(vehicle.dwellRemainingS)>0){ctx.fillStyle='#53d4ff';ctx.fillText('PARADERO',sx,sy+18);}}
      }

      // Indicador de que el canvas está recibiendo frames verdaderos.
      ctx.fillStyle='rgba(5,9,14,.82)';ctx.fillRect(14,14,238,62);ctx.fillStyle='#f4f7fb';ctx.textAlign='left';ctx.font='700 13px system-ui';ctx.fillText(target?`t = ${Number(target.timeS||0).toFixed(1)} s`:'Esperando simulación…',26,37);
      ctx.font='11px system-ui';ctx.fillStyle='#9fb0c2';ctx.fillText(`Frame #${frameSequence} · ${connectionStatus==='live'?'SSE conectado':'sin stream'}`,26,58);

      raf=requestAnimationFrame(draw);
    };
    raf=requestAnimationFrame(draw);
    return()=>{disposed=true;cancelAnimationFrame(raf);};
  }, [roads, connectionStatus, frameSequence]);

  return <div className="traffic-canvas-shell"><canvas ref={canvasRef}/><div className="canvas-legend"><span><i className="car"/>Auto</span><span><i className="bus b1"/>Bus B1</span><span><i className="bus b2"/>Bus B2</span><span><i className="stop"/>Paradero</span></div></div>;
}
