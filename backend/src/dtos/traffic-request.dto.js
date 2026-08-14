const { BadRequestException } = require('@nestjs/common');

const MAX_CLINGO_BYTES = 200 * 1024;

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

function clingoProgram(body) {
  const value = asObject(body).clingoProgram;
  if (value === undefined || value === null || value === '') return undefined;
  if (typeof value !== 'string') {
    throw new BadRequestException('clingoProgram debe ser texto');
  }
  if (Buffer.byteLength(value, 'utf8') > MAX_CLINGO_BYTES) {
    throw new BadRequestException('El archivo Clingo no puede superar 200 KB');
  }
  const lowered = value.toLowerCase();
  if (lowered.includes('#script') || lowered.includes('#include')) {
    throw new BadRequestException('El archivo Clingo contiene una directiva no permitida');
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

function checkpointRunId(input, required = false) {
  const value = asObject(input).checkpointRunId;
  if (!value) {
    if (required) throw new BadRequestException('checkpointRunId es obligatorio');
    return undefined;
  }
  if (typeof value !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(value)) {
    throw new BadRequestException('checkpointRunId inválido');
  }
  return value;
}

function common(input) {
  const customClingo = clingoProgram(input);
  return {
    scenario: scenario(input),
    ...(customClingo ? { clingoProgram: customClingo } : {}),
  };
}

function parseTopologyRequest(body) {
  return common(asObject(body));
}

function parseSimulationRequest(body) {
  const input = asObject(body);
  return {
    ...common(input),
    seconds: boundedNumber(input.seconds, 'seconds', 900, 5, 86400),
  };
}

function parseTrainingRequest(body) {
  const input = asObject(body);
  return {
    ...common(input),
    seconds: boundedNumber(input.seconds, 'seconds', 300, 5, 86400),
    episodes: Math.trunc(boundedNumber(input.episodes, 'episodes', 10, 1, 10000)),
  };
}

function parseEvaluationRequest(body) {
  const input = asObject(body);
  const runId = checkpointRunId(input, false);
  return {
    ...common(input),
    seconds: boundedNumber(input.seconds, 'seconds', 1200, 5, 86400),
    ...(runId ? { checkpointRunId: runId } : {}),
  };
}

function parseLiveSimulationRequest(body) {
  const input = asObject(body);
  return {
    ...common(input),
    checkpointRunId: checkpointRunId(input, true),
    cycleSeconds: boundedNumber(input.cycleSeconds, 'cycleSeconds', 1800, 60, 86400),
    realTimeFactor: boundedNumber(input.realTimeFactor, 'realTimeFactor', 1, 0.25, 4),
  };
}

module.exports = {
  parseTopologyRequest,
  parseSimulationRequest,
  parseTrainingRequest,
  parseEvaluationRequest,
  parseLiveSimulationRequest,
};
