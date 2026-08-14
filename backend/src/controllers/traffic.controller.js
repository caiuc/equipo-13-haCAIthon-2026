const { Controller, Get, Post, Body, Param } = require('@nestjs/common');
const { TrafficControlService } = require('../services/traffic-control.service');
const {
  parseTopologyRequest,
  parseSimulationRequest,
  parseTrainingRequest,
  parseEvaluationRequest,
} = require('../dtos/traffic-request.dto');

class TrafficController {
  constructor(trafficControlService) {
    this.trafficControlService = trafficControlService;
  }

  listScenarios() {
    return this.trafficControlService.listScenarios();
  }

  topology(body) {
    return this.trafficControlService.topology(parseTopologyRequest(body));
  }

  createSimulation(body) {
    return {
      success: true,
      data: this.trafficControlService.startSimulation(parseSimulationRequest(body)),
    };
  }

  createTraining(body) {
    return {
      success: true,
      data: this.trafficControlService.startTraining(parseTrainingRequest(body)),
    };
  }

  createEvaluation(body) {
    return {
      success: true,
      data: this.trafficControlService.startEvaluation(parseEvaluationRequest(body)),
    };
  }

  getJob(jobId) {
    return {
      success: true,
      data: this.trafficControlService.getJob(jobId),
    };
  }

  getJobResult(jobId) {
    return {
      success: true,
      data: this.trafficControlService.getJobResult(jobId),
    };
  }
}

Controller('api/traffic')(TrafficController);
Get('scenarios')(
  TrafficController.prototype,
  'listScenarios',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'listScenarios'),
);
Post('topology')(
  TrafficController.prototype,
  'topology',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'topology'),
);
Body()(TrafficController.prototype, 'topology', 0);
Post('simulations')(
  TrafficController.prototype,
  'createSimulation',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createSimulation'),
);
Body()(TrafficController.prototype, 'createSimulation', 0);
Post('training')(
  TrafficController.prototype,
  'createTraining',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createTraining'),
);
Body()(TrafficController.prototype, 'createTraining', 0);
Post('evaluations')(
  TrafficController.prototype,
  'createEvaluation',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createEvaluation'),
);
Body()(TrafficController.prototype, 'createEvaluation', 0);
Get('jobs/:jobId')(
  TrafficController.prototype,
  'getJob',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'getJob'),
);
Param('jobId')(TrafficController.prototype, 'getJob', 0);
Get('jobs/:jobId/results')(
  TrafficController.prototype,
  'getJobResult',
  Object.getOwnPropertyDescriptor(TrafficController.prototype, 'getJobResult'),
);
Param('jobId')(TrafficController.prototype, 'getJobResult', 0);

Reflect.defineMetadata('design:paramtypes', [TrafficControlService], TrafficController);

module.exports = { TrafficController };
