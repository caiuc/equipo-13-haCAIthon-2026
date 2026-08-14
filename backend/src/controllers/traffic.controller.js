const { Controller, Get, Post, Body, Param, Res } = require('@nestjs/common');
const { TrafficControlService } = require('../services/traffic-control.service');
const {
  parseTopologyRequest,
  parseSimulationRequest,
  parseTrainingRequest,
  parseEvaluationRequest,
  parseLiveSimulationRequest,
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
    return { success: true, data: this.trafficControlService.startSimulation(parseSimulationRequest(body)) };
  }

  createTraining(body) {
    return { success: true, data: this.trafficControlService.startTraining(parseTrainingRequest(body)) };
  }

  createEvaluation(body) {
    return { success: true, data: this.trafficControlService.startEvaluation(parseEvaluationRequest(body)) };
  }

  createLiveSimulation(body) {
    return { success: true, data: this.trafficControlService.startLiveSimulation(parseLiveSimulationRequest(body)) };
  }

  getLiveSimulation(sessionId) {
    return { success: true, data: this.trafficControlService.getLiveSimulation(sessionId) };
  }

  streamLiveSimulation(sessionId, response) {
    response.status(200);
    response.set({
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    });
    response.flushHeaders?.();
    response.socket?.setTimeout(0);
    response.socket?.setNoDelay?.(true);
    response.write('retry: 750\n\n');

    const send = (event) => {
      if (response.writableEnded) return;
      response.write(`data: ${JSON.stringify(event)}\n\n`);
      response.flush?.();
    };

    let unsubscribe;
    try {
      unsubscribe = this.trafficControlService.subscribeLiveSimulation(sessionId, send);
    } catch (error) {
      send({ type: 'error', error: { code: 'LIVE_SESSION_NOT_FOUND', message: error.message } });
      response.end();
      return;
    }

    const heartbeat = setInterval(() => {
      if (!response.writableEnded) response.write(': heartbeat\n\n');
    }, 15000);

    response.on('close', () => {
      clearInterval(heartbeat);
      unsubscribe?.();
    });
  }

  stopLiveSimulation(sessionId) {
    return { success: true, data: this.trafficControlService.stopLiveSimulation(sessionId) };
  }

  getJob(jobId) {
    return { success: true, data: this.trafficControlService.getJob(jobId) };
  }

  getJobResult(jobId) {
    return { success: true, data: this.trafficControlService.getJobResult(jobId) };
  }
}

Controller('api/traffic')(TrafficController);
Get('scenarios')(TrafficController.prototype, 'listScenarios', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'listScenarios'));
Post('topology')(TrafficController.prototype, 'topology', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'topology'));
Body()(TrafficController.prototype, 'topology', 0);
Post('simulations')(TrafficController.prototype, 'createSimulation', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createSimulation'));
Body()(TrafficController.prototype, 'createSimulation', 0);
Post('training')(TrafficController.prototype, 'createTraining', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createTraining'));
Body()(TrafficController.prototype, 'createTraining', 0);
Post('evaluations')(TrafficController.prototype, 'createEvaluation', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createEvaluation'));
Body()(TrafficController.prototype, 'createEvaluation', 0);
Post('live')(TrafficController.prototype, 'createLiveSimulation', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'createLiveSimulation'));
Body()(TrafficController.prototype, 'createLiveSimulation', 0);
Get('live/:sessionId/stream')(TrafficController.prototype, 'streamLiveSimulation', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'streamLiveSimulation'));
Param('sessionId')(TrafficController.prototype, 'streamLiveSimulation', 0);
Res()(TrafficController.prototype, 'streamLiveSimulation', 1);
Get('live/:sessionId')(TrafficController.prototype, 'getLiveSimulation', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'getLiveSimulation'));
Param('sessionId')(TrafficController.prototype, 'getLiveSimulation', 0);
Post('live/:sessionId/stop')(TrafficController.prototype, 'stopLiveSimulation', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'stopLiveSimulation'));
Param('sessionId')(TrafficController.prototype, 'stopLiveSimulation', 0);
Get('jobs/:jobId')(TrafficController.prototype, 'getJob', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'getJob'));
Param('jobId')(TrafficController.prototype, 'getJob', 0);
Get('jobs/:jobId/results')(TrafficController.prototype, 'getJobResult', Object.getOwnPropertyDescriptor(TrafficController.prototype, 'getJobResult'));
Param('jobId')(TrafficController.prototype, 'getJobResult', 0);

Reflect.defineMetadata('design:paramtypes', [TrafficControlService], TrafficController);
module.exports = { TrafficController };
