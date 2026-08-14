const { Injectable, NotFoundException } = require('@nestjs/common');
const { randomUUID } = require('node:crypto');
const { PythonProcessService } = require('./python-process.service');

class TrafficJobService {
  constructor(pythonProcessService) {
    this.pythonProcessService = pythonProcessService;
    this.jobs = new Map();
  }

  start(operation, parameters = {}) {
    const jobId = randomUUID();
    const createdAt = new Date().toISOString();
    const job = {
      id: jobId,
      operation,
      status: 'pending',
      createdAt,
      startedAt: null,
      completedAt: null,
      result: null,
      error: null,
    };
    this.jobs.set(jobId, job);

    Promise.resolve().then(async () => {
      job.status = 'running';
      job.startedAt = new Date().toISOString();
      try {
        const response = await this.pythonProcessService.run(operation, {
          operation,
          simulationId: jobId,
          parameters: {
            ...parameters,
            ...(operation === 'train' ? { runId: jobId } : {}),
          },
        });
        job.result = response;
        job.status = 'completed';
      } catch (error) {
        job.status = 'failed';
        job.error = {
          code: error.code || 'JOB_FAILED',
          message: error.message,
        };
      } finally {
        job.completedAt = new Date().toISOString();
      }
    });

    return this.publicState(job);
  }

  get(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new NotFoundException('Trabajo no encontrado');
    }
    return this.publicState(job);
  }

  result(jobId) {
    const job = this.jobs.get(jobId);
    if (!job) {
      throw new NotFoundException('Trabajo no encontrado');
    }
    if (job.status !== 'completed') {
      return {
        id: job.id,
        status: job.status,
        error: job.error,
        result: null,
      };
    }
    return {
      id: job.id,
      status: job.status,
      result: job.result,
    };
  }

  publicState(job) {
    return {
      id: job.id,
      operation: job.operation,
      status: job.status,
      createdAt: job.createdAt,
      startedAt: job.startedAt,
      completedAt: job.completedAt,
      error: job.error,
    };
  }
}

Injectable()(TrafficJobService);
Reflect.defineMetadata('design:paramtypes', [PythonProcessService], TrafficJobService);

module.exports = { TrafficJobService };
