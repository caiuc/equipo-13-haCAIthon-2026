const { Controller, Get } = require('@nestjs/common');

class AppController {
  health() {
    return {
      status: 'ok',
      message: 'Backend NestJS funcionando',
    };
  }
}

Controller()(AppController);
Get('api/health')(AppController.prototype, 'health', Object.getOwnPropertyDescriptor(AppController.prototype, 'health'));

module.exports = { AppController };
