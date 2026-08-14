const { Injectable } = require('@nestjs/common');
const { spawn } = require('node:child_process');
const path = require('node:path');

const ALLOWED_OPERATIONS = new Set(['scenarios', 'topology', 'simulate', 'train', 'evaluate']);
const MAX_OUTPUT_BYTES = 20 * 1024 * 1024;

class PythonProcessService {
  run(operation, payload = {}) {
    if (!ALLOWED_OPERATIONS.has(operation)) {
      return Promise.reject(new Error(`Operación Python no permitida: ${operation}`));
    }

    const backendRoot = path.resolve(__dirname, '../..');
    const srcRoot = path.join(backendRoot, 'src');
    const bridgePath = path.join(srcRoot, 'ia', 'scripts', 'bridge.py');
    const pythonBin = process.env.PYTHON_BIN || 'python3';
    const timeoutMs = operation === 'train'
      ? Number(process.env.PYTHON_TRAIN_TIMEOUT_MS || 14400000)
      : Number(process.env.PYTHON_TIMEOUT_MS || 600000);

    return new Promise((resolve, reject) => {
      const child = spawn(pythonBin, [bridgePath, operation], {
        cwd: backendRoot,
        env: {
          ...process.env,
          PYTHONPATH: [srcRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
        },
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
          finish(
            reject,
            new Error(`Respuesta Python inválida. exitCode=${exitCode}. stderr=${stderr || 'sin stderr'}`),
          );
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
}

Injectable()(PythonProcessService);

module.exports = { PythonProcessService, ALLOWED_OPERATIONS };
