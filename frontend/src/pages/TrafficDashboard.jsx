import { useEffect, useMemo, useState } from 'react';
import MetricsPanel from '../components/MetricsPanel';
import TopologyPanel from '../components/TopologyPanel';
import TrafficControls from '../components/TrafficControls';
import { useTrafficJob } from '../hooks/useTrafficJob';
import {
  getScenarios,
  getTopology,
  startEvaluation,
  startSimulation,
  startTraining,
} from '../services/trafficControlService';
import NetworkVisualization from '../visualization/NetworkVisualization';

export default function TrafficDashboard() {
  const [scenarios, setScenarios] = useState(['example_network.yaml']);
  const [topology, setTopology] = useState(null);
  const [pageError, setPageError] = useState('');
  const [values, setValues] = useState({
    scenario: 'example_network.yaml',
    seconds: 900,
    episodes: 10,
    checkpointRunId: '',
  });
  const { job, result, error: jobError, run } = useTrafficJob();

  const busy = job && !['completed', 'failed', 'cancelled'].includes(job.status);
  const snapshot = result?.snapshot || null;
  const metrics = result?.metrics || null;

  useEffect(() => {
    getScenarios()
      .then((items) => {
        if (items.length) {
          setScenarios(items);
          setValues((current) => ({ ...current, scenario: items.includes(current.scenario) ? current.scenario : items[0] }));
        }
      })
      .catch((caught) => setPageError(caught.message));
  }, []);

  const statusText = useMemo(() => {
    if (!job) return 'Sin trabajos activos';
    const labels = {
      pending: 'Pendiente',
      running: 'Ejecutando',
      completed: 'Completado',
      failed: 'Falló',
      cancelled: 'Cancelado',
    };
    return `${labels[job.status] || job.status} · ${job.operation} · ${job.id}`;
  }, [job]);

  const onChange = (event) => {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
  };

  const loadTopology = async () => {
    setPageError('');
    try {
      const response = await getTopology({ scenario: values.scenario });
      setTopology(response.data);
    } catch (caught) {
      setPageError(caught.message);
    }
  };

  const common = () => ({ scenario: values.scenario, seconds: Number(values.seconds) });

  const simulate = () => run(() => startSimulation(common())).catch(() => null);
  const train = () => run(() => startTraining({ ...common(), episodes: Number(values.episodes) }))
    .then((data) => {
      if (data?.runId) setValues((current) => ({ ...current, checkpointRunId: data.runId }));
    })
    .catch(() => null);
  const evaluate = () => run(() => startEvaluation({ ...common(), checkpointRunId: values.checkpointRunId })).catch(() => null);

  return (
    <main className="app-shell">
      <header className="hero">
        <div>
          <span className="badge">haCAIthon 2026 · Equipo 13</span>
          <h1>Control semafórico multiagente orientado a buses</h1>
          <p>
            Clingo determina la legalidad; el entorno microscópico representa el tráfico; los agentes DQN deciden únicamente entre fases seguras.
          </p>
        </div>
        <div className="hero-status">
          <span>Estado</span>
          <strong>{statusText}</strong>
        </div>
      </header>

      {(pageError || jobError) && <div className="alert error">{pageError || jobError}</div>}

      <TrafficControls
        scenarios={scenarios}
        values={values}
        onChange={onChange}
        onTopology={loadTopology}
        onSimulate={simulate}
        onTrain={train}
        onEvaluate={evaluate}
        busy={busy}
      />

      <section className="panel network-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Red</span>
            <h2>Vista global</h2>
          </div>
          {snapshot && <span className="status-pill">t = {snapshot.timeS.toFixed(1)} s</span>}
        </div>
        <NetworkVisualization snapshot={snapshot} topology={topology} />
      </section>

      <MetricsPanel metrics={metrics} />
      <TopologyPanel topology={topology} />
    </main>
  );
}
