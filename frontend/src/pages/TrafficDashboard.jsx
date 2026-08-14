import { useState } from 'react';
import LiveDecisionPanel from '../components/LiveDecisionPanel';
import MetricsPanel from '../components/MetricsPanel';
import TopologyPanel from '../components/TopologyPanel';
import TrafficControls from '../components/TrafficControls';
import TrainingHistoryChart from '../components/TrainingHistoryChart';
import { useLiveSimulation } from '../hooks/useLiveSimulation';
import { useTrafficJob } from '../hooks/useTrafficJob';
import { getTopology, startTraining } from '../services/trafficControlService';
import NetworkVisualization from '../visualization/NetworkVisualization';

const DEFAULTS = {
  scenario: 'example_network.yaml',
  episodes: 10,
  trainSeconds: 300,
  cycleSeconds: 1800,
  realTimeFactor: 1,
};

export default function TrafficDashboard() {
  const [values, setValues] = useState(DEFAULTS);
  const [clingoFile, setClingoFile] = useState(null);
  const [clingoProgram, setClingoProgram] = useState('');
  const [topology, setTopology] = useState(null);
  const [topologyBusy, setTopologyBusy] = useState(false);
  const [trainingResult, setTrainingResult] = useState(null);
  const [trainedRunId, setTrainedRunId] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [pageError, setPageError] = useState('');
  const { job, error: jobError, run, reset: resetJob } = useTrafficJob();
  const live = useLiveSimulation();

  const common = () => ({
    scenario: values.scenario,
    ...(clingoProgram ? { clingoProgram } : {}),
  });

  const invalidateModel = () => {
    setTopology(null);
    setTrainingResult(null);
    setTrainedRunId('');
    resetJob();
  };

  const onFile = async (file) => {
    if (!file) return;
    setPageError('');
    if (!file.name.toLowerCase().endsWith('.lp')) {
      setPageError('Selecciona un archivo Clingo con extensión .lp');
      return;
    }
    if (file.size > 200 * 1024) {
      setPageError('El archivo Clingo no puede superar 200 KB.');
      return;
    }
    const text = await file.text();
    setClingoFile(file);
    setClingoProgram(text);
    invalidateModel();
    setFeedback({ type: 'info', title: 'Archivo cargado', message: `${file.name} se aplicará como extensión de las reglas Clingo seguras.` });
  };

  const onClearFile = () => {
    setClingoFile(null);
    setClingoProgram('');
    invalidateModel();
    setFeedback({ type: 'info', title: 'Reglas base', message: 'Se usará únicamente backend/src/ia/clingo/rules.lp.' });
  };

  const onChange = (event) => {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
  };

  const onPreset = (episodes, seconds) => {
    setValues((current) => ({ ...current, episodes, trainSeconds: seconds }));
  };

  const validateTopology = async () => {
    setTopologyBusy(true);
    setPageError('');
    try {
      const response = await getTopology(common());
      setTopology(response.data);
      setFeedback({ type: 'success', title: 'Clingo validó la red', message: 'Los dos cruces ya tienen movimientos, conflictos y fases legales.' });
    } catch (caught) {
      setTopology(null);
      setPageError(caught.message);
    } finally {
      setTopologyBusy(false);
    }
  };

  const train = async () => {
    setPageError('');
    setFeedback({ type: 'info', title: 'Entrenamiento iniciado', message: `${values.episodes} episodios. El modelo se guardará al terminar.` });
    try {
      const data = await run(() => startTraining({
        ...common(),
        episodes: Number(values.episodes),
        seconds: Number(values.trainSeconds),
      }));
      if (!data) return;
      setTrainingResult(data);
      setTrainedRunId(data.runId);
      setFeedback({ type: 'success', title: 'Modelo DQN listo', message: `Run ID ${data.runId}. Ya puedes iniciar la simulación continua.` });
    } catch (caught) {
      setFeedback({ type: 'error', title: 'Falló el entrenamiento', message: caught.message });
    }
  };

  const startLive = async () => {
    setPageError('');
    try {
      const session = await live.start({
        ...common(),
        checkpointRunId: trainedRunId,
        cycleSeconds: Number(values.cycleSeconds),
        realTimeFactor: Number(values.realTimeFactor),
      });
      setFeedback({ type: 'success', title: 'Simulación iniciada', message: `Sesión ${session.id.slice(0, 8)}. El DQN seguirá tomando decisiones hasta que la detengas.` });
    } catch (caught) {
      setPageError(caught.message);
    }
  };

  const stopLive = async () => {
    try {
      await live.stop();
      setFeedback({ type: 'info', title: 'Deteniendo simulación', message: 'Se está cerrando el proceso Python de forma segura.' });
    } catch (caught) {
      setPageError(caught.message);
    }
  };

  const snapshot = live.session?.snapshot || trainingResult?.snapshot || null;
  const metrics = live.session?.metrics || trainingResult?.metrics || null;
  const visibleError = pageError || jobError || live.error;
  const liveRunning = ['starting', 'running', 'stopping'].includes(live.session?.status);

  return (
    <main className="app-shell demo-shell">
      <header className="demo-hero">
        <div><span className="badge">haCAIthon 2026 · Equipo 13</span><h1>Dos cruces. Ocho semáforos. Un DQN coordinando el tráfico.</h1><p>Carga reglas Clingo, entrena los agentes y observa una simulación continua donde autos y buses reaccionan a decisiones semafóricas reales.</p></div>
        <div className="hero-live-diagram"><span>CLINGO</span><i>→</i><span>DQN</span><i>→</i><span>TRÁFICO</span></div>
      </header>

      {visibleError && <div className="alert error"><strong>Error:</strong> {visibleError}</div>}
      {feedback && <div className={`toast-feedback ${feedback.type}`} role="status"><span className="toast-icon">{feedback.type === 'success' ? '✓' : feedback.type === 'error' ? '!' : 'i'}</span><div><strong>{feedback.title}</strong><p>{feedback.message}</p></div><button type="button" onClick={() => setFeedback(null)}>×</button></div>}

      <TrafficControls
        values={values}
        clingoFile={clingoFile}
        onFile={onFile}
        onClearFile={onClearFile}
        onChange={onChange}
        onPreset={onPreset}
        onValidate={validateTopology}
        onTrain={train}
        onStartLive={startLive}
        onStopLive={stopLive}
        topologyReady={Boolean(topology)}
        trainedRunId={trainedRunId}
        job={job}
        topologyBusy={topologyBusy}
        liveSession={live.session}
        connectionStatus={live.connectionStatus}
      />

      <section className={`panel simulation-main-panel ${liveRunning ? 'simulation-running' : ''}`}>
        <div className="panel-heading simulation-heading"><div><span className="eyebrow">Simulación microscópica</span><h2>Dos intersecciones conectadas</h2><p className="section-description">Cada calzada muestra dos pistas por sentido. Los cuatro cabezales de cada cruce reflejan rojo, amarillo y verde del controlador real.</p></div>{liveRunning && <span className="live-status-badge running"><i />EN VIVO · ciclo {live.session?.cycle || 1}</span>}</div>
        <NetworkVisualization snapshot={snapshot} topology={topology} liveStatus={live.session?.status || 'idle'} connectionStatus={live.connectionStatus} streamInfo={live.session?.streamInfo} frameSequence={live.session?.frameSequence || 0} />
      </section>

      <LiveDecisionPanel snapshot={snapshot} decisions={live.session?.decisions || []} sessionStatus={live.session?.status} />
      <TrainingHistoryChart history={trainingResult?.history} />
      <MetricsPanel metrics={metrics} mode={liveRunning ? 'live' : trainingResult ? 'training' : 'idle'} />

      {topology && <details className="topology-details"><summary>Inspeccionar fases y conflictos calculados por Clingo</summary><TopologyPanel topology={topology} /></details>}

      <section className="demo-explainer panel"><div><span className="eyebrow">Qué estás viendo</span><h2>El DQN no controla luces arbitrarias</h2></div><div className="explainer-chain"><article><strong>1 · Clingo</strong><p>Deriva movimientos, conflictos y fases seguras.</p></article><b>→</b><article><strong>2 · DQN</strong><p>Escoge una de esas fases según tráfico, GPS y headway.</p></article><b>→</b><article><strong>3 · Controlador</strong><p>Respeta verde mínimo y aplica amarillo antes del cambio.</p></article><b>→</b><article><strong>4 · Simulador</strong><p>Autos y buses avanzan, esperan y vuelven a alimentar al agente.</p></article></div></section>
    </main>
  );
}
