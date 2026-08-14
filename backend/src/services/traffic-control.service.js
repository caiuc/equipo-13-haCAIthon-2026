const { Injectable } = require('@nestjs/common');
const { PythonProcessService } = require('./python-process.service');
const { TrafficJobService } = require('./traffic-job.service');

class TrafficControlService {
  constructor(pythonProcessService, trafficJobService) {
    this.pythonProcessService = pythonProcessService;
    this.trafficJobService = trafficJobService;
  }

  async listScenarios() {
    return this.pythonProcessService.run('scenarios', { parameters: {} });
  }

  async topology(parameters) {
    return this.pythonProcessService.run('topology', { parameters });
  }

  startSimulation(parameters) {
    return this.trafficJobService.start('simulate', parameters);
  }

  startTraining(parameters) {
    return this.trafficJobService.start('train', parameters);
  }

  startEvaluation(parameters) {
    return this.trafficJobService.start('evaluate', parameters);
  }

  getJob(jobId) {
    return this.trafficJobService.get(jobId);
  }

  getJobResult(jobId) {
    return this.trafficJobService.result(jobId);
  }
}

Injectable()(TrafficControlService);
Reflect.defineMetadata(
  'design:paramtypes',
  [PythonProcessService, TrafficJobService],
  TrafficControlService,
);

module.exports = { TrafficControlService };
