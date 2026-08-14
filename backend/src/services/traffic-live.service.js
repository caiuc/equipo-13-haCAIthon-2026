const { Injectable, NotFoundException } = require('@nestjs/common');
const { randomUUID } = require('node:crypto');
const { PythonProcessService } = require('./python-process.service');

class TrafficLiveService {
  constructor(pythonProcessService) {
    this.pythonProcessService = pythonProcessService;
    this.sessions = new Map();
  }

  publish(session, event) {
    for (const subscriber of session.subscribers) {
      try {
        subscriber(event);
      } catch (_) {
        // Una conexión HTTP cerrada no debe detener la simulación Python.
      }
    }
  }

  start(parameters = {}) {
    const id = randomUUID();
    const session = {
      id,
      status: 'starting',
      createdAt: new Date().toISOString(),
      startedAt: null,
      stoppedAt: null,
      parameters: {
        scenario: parameters.scenario,
        checkpointRunId: parameters.checkpointRunId,
        cycleSeconds: parameters.cycleSeconds,
        realTimeFactor: parameters.realTimeFactor,
      },
      frameSequence: 0,
      decisionSequence: 0,
      cycle: 0,
      latestFrame: null,
      metrics: null,
      decisions: [],
      streamInfo: null,
      error: null,
      stderr: '',
      child: null,
      subscribers: new Set(),
    };
    this.sessions.set(id, session);

    session.child = this.pythonProcessService.startLiveSimulation(parameters, {
      onMessage: (message) => {
        if (message.type === 'error') {
          session.status = 'failed';
          session.error = message.error;
          this.publish(session, { type: 'error', ...this.publicState(session, true) });
          return;
        }

        if (message.type === 'stopped') {
          session.status = 'stopped';
          session.stoppedAt = new Date().toISOString();
          this.publish(session, { type: 'stopped', ...this.publicState(session, true) });
          return;
        }

        if (message.snapshot) session.latestFrame = message.snapshot;
        if (message.metrics) session.metrics = message.metrics;

        if (message.simulationDtS || message.decisionIntervalS || message.realTimeFactor) {
          session.streamInfo = {
            simulationDtS: Number(message.simulationDtS || session.streamInfo?.simulationDtS || 0.2),
            decisionIntervalS: Number(message.decisionIntervalS || session.streamInfo?.decisionIntervalS || 5),
            realTimeFactor: Number(message.realTimeFactor || session.streamInfo?.realTimeFactor || 1),
          };
        }

        if (message.type === 'cycle') {
          session.cycle = Number(message.cycle || session.cycle || 1);
          if (!session.startedAt) session.startedAt = new Date().toISOString();
          session.status = 'running';
        }

        if (message.type === 'decision') {
          session.status = 'running';
          session.decisionSequence = Number(message.sequence || session.decisionSequence + 1);
          session.cycle = Number(message.cycle || session.cycle || 1);
          session.decisions.push({
            sequence: session.decisionSequence,
            timeS: Number(message.timeS ?? message.snapshot?.timeS ?? 0),
            cycle: session.cycle,
            actions: message.actions || {},
          });
          if (session.decisions.length > 100) {
            session.decisions.splice(0, session.decisions.length - 100);
          }
        }

        if (message.type === 'frame') {
          session.status = 'running';
          session.frameSequence = Number(message.frameSequence || session.frameSequence + 1);
          session.decisionSequence = Number(message.decisionSequence || session.decisionSequence);
          session.cycle = Number(message.cycle || session.cycle || 1);
        }

        this.publish(session, {
          type: message.type,
          id: session.id,
          status: session.status,
          cycle: session.cycle,
          frameSequence: session.frameSequence,
          decisionSequence: session.decisionSequence,
          sequence: session.decisionSequence,
          snapshot: message.snapshot,
          metrics: message.metrics,
          actions: message.actions,
          rewards: message.rewards,
          streamInfo: session.streamInfo,
          decision: message.type === 'decision' ? session.decisions.at(-1) : undefined,
        });
      },
      onLog: (stderr) => {
        session.stderr = String(stderr || '').slice(-8000);
      },
      onError: (error) => {
        session.status = 'failed';
        session.error = { code: error.code || 'LIVE_PROCESS_FAILED', message: error.message };
        this.publish(session, { type: 'error', ...this.publicState(session, true) });
      },
      onClose: ({ code, signal, stderr }) => {
        session.stderr = String(stderr || session.stderr || '').slice(-8000);
        if (session.status === 'stopping' || session.status === 'stopped') {
          session.status = 'stopped';
        } else if (code === 0) {
          session.status = 'stopped';
        } else if (session.status !== 'failed') {
          session.status = 'failed';
          session.error = {
            code: 'LIVE_PROCESS_EXIT',
            message: `La simulación terminó inesperadamente (code=${code}, signal=${signal || 'none'}).`,
          };
        }
        session.stoppedAt = new Date().toISOString();
        this.publish(session, { type: session.status, ...this.publicState(session, true) });
      },
    });

    return this.publicState(session);
  }

  getSession(id) {
    const session = this.sessions.get(id);
    if (!session) throw new NotFoundException('Sesión de simulación no encontrada');
    return session;
  }

  get(id) {
    return this.publicState(this.getSession(id), true);
  }

  subscribe(id, subscriber) {
    const session = this.getSession(id);
    session.subscribers.add(subscriber);
    subscriber({ type: 'session', ...this.publicState(session, true) });
    return () => session.subscribers.delete(subscriber);
  }

  stop(id) {
    const session = this.getSession(id);
    if (['stopped', 'failed'].includes(session.status)) return this.publicState(session, true);
    session.status = 'stopping';
    this.publish(session, { type: 'stopping', ...this.publicState(session, true) });
    session.child?.kill('SIGTERM');
    return this.publicState(session, true);
  }

  publicState(session, includeData = false) {
    return {
      id: session.id,
      status: session.status,
      createdAt: session.createdAt,
      startedAt: session.startedAt,
      stoppedAt: session.stoppedAt,
      parameters: session.parameters,
      sequence: session.decisionSequence,
      frameSequence: session.frameSequence,
      decisionSequence: session.decisionSequence,
      cycle: session.cycle,
      streamInfo: session.streamInfo,
      error: session.error,
      ...(includeData ? {
        snapshot: session.latestFrame,
        metrics: session.metrics,
        decisions: session.decisions.slice(-30),
      } : {}),
    };
  }
}

Injectable()(TrafficLiveService);
Reflect.defineMetadata('design:paramtypes', [PythonProcessService], TrafficLiveService);

module.exports = { TrafficLiveService };
