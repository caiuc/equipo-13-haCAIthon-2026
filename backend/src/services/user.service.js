const { Injectable } = require('@nestjs/common');
const { UserModel } = require('../models/user.model');

class UserService {
  constructor() {
    this.users = [
      new UserModel(1, 'Usuario Demo', 'demo@example.com'),
      new UserModel(2, 'Usuario React', 'react@example.com'),
    ];
  }

  findAll() {
    return this.users;
  }

  findById(id) {
    return this.users.find((user) => user.id === Number(id)) || null;
  }
}

Injectable()(UserService);

module.exports = { UserService };
