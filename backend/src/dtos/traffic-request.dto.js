const { BadRequestException } = require('@nestjs/common');

function asObject(body) {
  if (body === undefined || body === null) return {};
  if (typeof body !== 'object' || Array.isArray(body)) {
    throw new BadRequestException('El body debe ser un objeto JSON');
  }
  return body;
}

function scenario(body) {
  const value = asObject(body).scenario ?? 'example_network.yaml';
  if (typeof value !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(value)) {
    throw new BadRequestException('scenario inválido');
  }
  return value;
}

function boundedNumber(value, name, defaultValue, min, max) {
  if (value === undefined || value === null || value === '') return defaultValue;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) {
    throw new BadRequestException(`${name} debe estar entre ${min} y ${max}`);
  }
  return parsed;
}

function parseTopologyRequest(body) {
  return { scenario: scenario(body) };
}

function parseSimulationRequest(body) {
  const input = asObject(body);
  return {
    scenario: scenario(input),
    seconds: boundedNumber(input.seconds, 'seconds', 900, 5, 86400),
  };
}

function parseTrainingRequest(body) {
  const input = asObject(body);
  return {
    scenario: scenario(input),
    seconds: boundedNumber(input.seconds, 'seconds', 900, 5, 86400),
    episodes: Math.trunc(boundedNumber(input.episodes, 'episodes', 20, 1, 10000)),
  };
}

function parseEvaluationRequest(body) {
  const input = asObject(body);
  const checkpointRunId = input.checkpointRunId;
  if (checkpointRunId !== undefined && (
    typeof checkpointRunId !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(checkpointRunId)
  )) {
    throw new BadRequestException('checkpointRunId inválido');
  }
  return {
    scenario: scenario(input),
    seconds: boundedNumber(input.seconds, 'seconds', 1800, 5, 86400),
    ...(checkpointRunId ? { checkpointRunId } : {}),
  };
}

module.exports = {
  parseTopologyRequest,
  parseSimulationRequest,
  parseTrainingRequest,
  parseEvaluationRequest,
};
