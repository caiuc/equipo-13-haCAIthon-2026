const { Module } = require('@nestjs/common');
const { AppController } = require('./app.controller');
const { UserController } = require('./controllers/user.controller');
const { UserService } = require('./services/user.service');

class AppModule {}

Module({
  controllers: [AppController, UserController],
  providers: [UserService],
})(AppModule);

module.exports = { AppModule };
