import { useState } from 'react';
import LiveDecisionPanel from '../components/LiveDecisionPanel';
import MetricsPanel from '../components/MetricsPanel';
import TrafficControls from '../components/TrafficControls';
import TrainingHistoryChart from '../components/TrainingHistoryChart';
import { useLiveSimulation } from '../hooks/useLiveSimulation';
import { useTrafficJob } from '../hooks/useTrafficJob';
import { getTopology, startTraining } from '../services/trafficControlService';
import NetworkVisualization from '../visualization/NetworkVisualization';

const DEFAULTS={scenario:'example_network.yaml',episodes:3,trainSeconds:120,cycleSeconds:600,realTimeFactor:1};

export default function TrafficDashboard(){
  const[values,setValues]=useState(DEFAULTS); const[clingoFile,setClingoFile]=useState(null); const[clingoProgram,setClingoProgram]=useState('');
  const[topology,setTopology]=useState(null); const[topologyBusy,setTopologyBusy]=useState(false); const[trainingResult,setTrainingResult]=useState(null); const[trainedRunId,setTrainedRunId]=useState(''); const[message,setMessage]=useState('');
  const{job,error:jobError,run}=useTrafficJob(); const live=useLiveSimulation();
  const common=()=>({scenario:values.scenario,...(clingoProgram?{clingoProgram}:{})});
  const onChange=(e)=>setValues(v=>({...v,[e.target.name]:e.target.value}));
  const onPreset=(episodes,seconds)=>setValues(v=>({...v,episodes,trainSeconds:seconds}));
  const onFile=async(file)=>{if(!file)return;if(!file.name.toLowerCase().endsWith('.lp')){setMessage('El archivo debe terminar en .lp');return;}const text=await file.text();setClingoFile(file);setClingoProgram(text);setTopology(null);setTrainedRunId('');setMessage(`Archivo ${file.name} cargado.`);};
  const onClearFile=()=>{setClingoFile(null);setClingoProgram('');setTopology(null);setTrainedRunId('');};
  const validate=async()=>{setTopologyBusy(true);setMessage('');try{const response=await getTopology(common());setTopology(response.data);setMessage('Clingo validó la red. Ya puedes entrenar.');}catch(e){setMessage(e.message);}finally{setTopologyBusy(false);}};
  const train=async()=>{setMessage('Entrenando…');try{const data=await run(()=>startTraining({...common(),episodes:Number(values.episodes),seconds:Number(values.trainSeconds)}));if(data){setTrainingResult(data);setTrainedRunId(data.runId);setMessage(`Modelo listo: ${data.runId}`);}}catch(e){setMessage(e.message);}};
  const startLive=async()=>{try{await live.start({...common(),checkpointRunId:trainedRunId,cycleSeconds:Number(values.cycleSeconds),realTimeFactor:Number(values.realTimeFactor)});setMessage('Simulación iniciada. Los frames llegan directamente desde el mismo entorno usado para entrenar.');}catch(e){setMessage(e.message);}};
  const stopLive=async()=>{try{await live.stop();}catch(e){setMessage(e.message);}};
  const snapshot=live.session?.snapshot || trainingResult?.snapshot || null; const metrics=live.session?.metrics || trainingResult?.metrics || null;
  const error=jobError||live.error;
  return <main className="app-shell">
    <header className="hero"><div><span className="pill">haCAIthon 2026 · Equipo 13</span><h1>Control semafórico DQN<br/>sobre dos cruces conectados</h1><p>Arquitectura rehecha sobre el patrón funcional del proyecto de referencia: una sola física para entrenar y para visualizar.</p></div><div className="hero-flow"><span>CLINGO</span><b>→</b><span>DQN A + B</span><b>→</b><span>SIMULADOR 0,2 s</span></div></header>
    {(message||error)&&<div className={`notice ${error?'error':''}`}>{error||message}</div>}
    <TrafficControls values={values} clingoFile={clingoFile} onFile={onFile} onClearFile={onClearFile} onChange={onChange} onPreset={onPreset} onValidate={validate} onTrain={train} onStartLive={startLive} onStopLive={stopLive} topologyReady={Boolean(topology)} trainedRunId={trainedRunId} job={job} topologyBusy={topologyBusy} liveSession={live.session} connectionStatus={live.connectionStatus}/>
    <section className="panel simulator-panel"><div className="section-heading"><div><small>SIMULACIÓN MICROSCÓPICA</small><h2>La calle en tiempo real</h2></div><p>El frente del vehículo se detiene en la línea blanca. Amarillo bloquea nuevas entradas; los vehículos ya dentro despejan el cruce.</p></div><NetworkVisualization snapshot={snapshot} topology={topology} connectionStatus={live.connectionStatus} frameSequence={live.session?.frameSequence||0}/></section>
    <LiveDecisionPanel snapshot={snapshot} decisions={live.session?.decisions||[]}/>
    <TrainingHistoryChart history={trainingResult?.history}/>
    <MetricsPanel metrics={metrics}/>
    <section className="panel architecture-note"><small>POR QUÉ ESTA VERSIÓN ES DISTINTA</small><h2>Entrenamiento y demo ejecutan el mismo <code>MultiAgentTrafficEnv.step()</code></h2><div><span><b>5 s</b> decisión DQN</span><span><b>25</b> subpasos físicos</span><span><b>0,2 s</b> por frame real</span><span><b>0</b> física en React</span></div></section>
  </main>;
}
