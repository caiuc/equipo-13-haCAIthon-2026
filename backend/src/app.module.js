const { Module } = require('@nestjs/common');
const { AppController } = require('./app.controller');
const { UserController } = require('./controllers/user.controller');
const { TrafficController } = require('./controllers/traffic.controller');
const { UserService } = require('./services/user.service');
const { PythonProcessService } = require('./services/python-process.service');
const { TrafficJobService } = require('./services/traffic-job.service');
const { TrafficLiveService } = require('./services/traffic-live.service');
const { TrafficControlService } = require('./services/traffic-control.service');

class AppModule {}

Module({
  controllers: [AppController, UserController, TrafficController],
  providers: [UserService, PythonProcessService, TrafficJobService, TrafficLiveService, TrafficControlService],
})(AppModule);

module.exports = { AppModule };
