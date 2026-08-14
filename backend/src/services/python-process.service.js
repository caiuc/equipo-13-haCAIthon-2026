const { Injectable } = require('@nestjs/common');
const { spawn } = require('node:child_process');
const path = require('node:path');

const ALLOWED_OPERATIONS = new Set(['scenarios', 'topology', 'simulate', 'train', 'evaluate']);
const MAX_OUTPUT_BYTES = 20 * 1024 * 1024;
const MAX_STREAM_LINE_BYTES = 2 * 1024 * 1024;

class PythonProcessService {
  runtimePaths() {
    const backendRoot = path.resolve(__dirname, '../..');
    const srcRoot = path.join(backendRoot, 'src');
    const pythonBin = process.env.PYTHON_BIN || 'python3';
    return { backendRoot, srcRoot, pythonBin };
  }

  pythonEnv(srcRoot) {
    return {
      ...process.env,
      PYTHONPATH: [srcRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
    };
  }

  run(operation, payload = {}) {
    if (!ALLOWED_OPERATIONS.has(operation)) {
      return Promise.reject(new Error(`Operación Python no permitida: ${operation}`));
    }

    const { backendRoot, srcRoot, pythonBin } = this.runtimePaths();
    const bridgePath = path.join(srcRoot, 'ia', 'scripts', 'bridge.py');
    const timeoutMs = operation === 'train'
      ? Number(process.env.PYTHON_TRAIN_TIMEOUT_MS || 14400000)
      : Number(process.env.PYTHON_TIMEOUT_MS || 600000);

    return new Promise((resolve, reject) => {
      const child = spawn(pythonBin, [bridgePath, operation], {
        cwd: backendRoot,
        env: this.pythonEnv(srcRoot),
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let stdout = '';
      let stderr = '';
      let totalBytes = 0;
      let settled = false;

      const finish = (callback, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        callback(value);
      };

      const timer = setTimeout(() => {
        child.kill('SIGTERM');
        finish(reject, new Error(`Proceso Python excedió timeout (${timeoutMs} ms)`));
      }, timeoutMs);

      child.stdout.on('data', (chunk) => {
        totalBytes += chunk.length;
        if (totalBytes > MAX_OUTPUT_BYTES) {
          child.kill('SIGTERM');
          finish(reject, new Error('Salida Python excedió el límite permitido'));
          return;
        }
        stdout += chunk.toString('utf8');
      });

      child.stderr.on('data', (chunk) => {
        const text = chunk.toString('utf8');
        stderr = `${stderr}${text}`.slice(-20000);
      });

      child.on('error', (error) => {
        finish(reject, new Error(`No fue posible iniciar ${pythonBin}: ${error.message}`));
      });

      child.on('close', (exitCode) => {
        if (settled) return;
        let response;
        try {
          response = JSON.parse(stdout || '{}');
        } catch (error) {
          finish(reject, new Error(`Respuesta Python inválida. exitCode=${exitCode}. stderr=${stderr || 'sin stderr'}`));
          return;
        }

        if (exitCode !== 0 || response.success === false) {
          const message = response?.error?.message || stderr || `Python terminó con código ${exitCode}`;
          const wrapped = new Error(message);
          wrapped.code = response?.error?.code || 'PYTHON_PROCESS_FAILED';
          finish(reject, wrapped);
          return;
        }
        finish(resolve, response);
      });

      child.stdin.end(JSON.stringify(payload));
    });
  }

  startLiveSimulation(parameters, handlers = {}) {
    const { backendRoot, srcRoot, pythonBin } = this.runtimePaths();
    const scriptPath = path.join(srcRoot, 'ia', 'scripts', 'live_simulation.py');
    const child = spawn(pythonBin, [scriptPath], {
      cwd: backendRoot,
      env: this.pythonEnv(srcRoot),
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdoutBuffer = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdoutBuffer += chunk.toString('utf8');
      if (Buffer.byteLength(stdoutBuffer, 'utf8') > MAX_STREAM_LINE_BYTES * 2) {
        handlers.onError?.(new Error('Buffer de simulación en vivo excedió el límite'));
        child.kill('SIGTERM');
        return;
      }
      const lines = stdoutBuffer.split('\n');
      stdoutBuffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        if (Buffer.byteLength(line, 'utf8') > MAX_STREAM_LINE_BYTES) {
          handlers.onError?.(new Error('Frame de simulación demasiado grande'));
          child.kill('SIGTERM');
          return;
        }
        try {
          handlers.onMessage?.(JSON.parse(line));
        } catch (error) {
          handlers.onError?.(new Error(`Frame Python inválido: ${error.message}`));
        }
      }
    });

    child.stderr.on('data', (chunk) => {
      stderr = `${stderr}${chunk.toString('utf8')}`.slice(-20000);
      handlers.onLog?.(stderr);
    });
    child.on('error', (error) => handlers.onError?.(error));
    child.on('close', (code, signalName) => handlers.onClose?.({ code, signal: signalName, stderr }));
    child.stdin.end(`${JSON.stringify(parameters)}\n`);
    return child;
  }
}

Injectable()(PythonProcessService);

module.exports = { PythonProcessService, ALLOWED_OPERATIONS };
