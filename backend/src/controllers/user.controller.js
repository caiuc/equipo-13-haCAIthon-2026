const { Controller, Get, Param, NotFoundException } = require('@nestjs/common');
const { UserService } = require('../services/user.service');

class UserController {
  constructor(userService) {
    this.userService = userService;
  }

  findAll() {
    return this.userService.findAll();
  }

  findOne(id) {
    const user = this.userService.findById(id);

    if (!user) {
      throw new NotFoundException('Usuario no encontrado');
    }

    return user;
  }
}

Controller('api/users')(UserController);
Get()(UserController.prototype, 'findAll', Object.getOwnPropertyDescriptor(UserController.prototype, 'findAll'));
Get(':id')(UserController.prototype, 'findOne', Object.getOwnPropertyDescriptor(UserController.prototype, 'findOne'));
Param('id')(UserController.prototype, 'findOne', 0);

Reflect.defineMetadata('design:paramtypes', [UserService], UserController);

module.exports = { UserController };
