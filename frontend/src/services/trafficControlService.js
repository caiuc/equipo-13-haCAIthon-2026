const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok || payload?.success === false) {
    throw new Error(payload?.error?.message || `Error HTTP ${response.status}`);
  }
  return payload;
}

export async function getScenarios() {
  const response = await request('/traffic/scenarios');
  return response.data.scenarios;
}

export async function getTopology(parameters) {
  return request('/traffic/topology', {
    method: 'POST',
    body: JSON.stringify(parameters),
  });
}

export async function startSimulation(parameters) {
  const response = await request('/traffic/simulations', {
    method: 'POST',
    body: JSON.stringify(parameters),
  });
  return response.data;
}

export async function startTraining(parameters) {
  const response = await request('/traffic/training', {
    method: 'POST',
    body: JSON.stringify(parameters),
  });
  return response.data;
}

export async function startEvaluation(parameters) {
  const response = await request('/traffic/evaluations', {
    method: 'POST',
    body: JSON.stringify(parameters),
  });
  return response.data;
}

export async function getJob(jobId) {
  const response = await request(`/traffic/jobs/${encodeURIComponent(jobId)}`);
  return response.data;
}

export async function getJobResult(jobId) {
  const response = await request(`/traffic/jobs/${encodeURIComponent(jobId)}/results`);
  return response.data;
}
