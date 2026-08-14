const { Injectable } = require('@nestjs/common');
const { PythonProcessService } = require('./python-process.service');
const { TrafficJobService } = require('./traffic-job.service');
const { TrafficLiveService } = require('./traffic-live.service');

class TrafficControlService {
  constructor(pythonProcessService, trafficJobService, trafficLiveService) {
    this.pythonProcessService = pythonProcessService;
    this.trafficJobService = trafficJobService;
    this.trafficLiveService = trafficLiveService;
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

  startLiveSimulation(parameters) {
    return this.trafficLiveService.start(parameters);
  }

  getLiveSimulation(sessionId) {
    return this.trafficLiveService.get(sessionId);
  }

  stopLiveSimulation(sessionId) {
    return this.trafficLiveService.stop(sessionId);
  }

  subscribeLiveSimulation(sessionId, subscriber) {
    return this.trafficLiveService.subscribe(sessionId, subscriber);
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
  [PythonProcessService, TrafficJobService, TrafficLiveService],
  TrafficControlService,
);

module.exports = { TrafficControlService };
