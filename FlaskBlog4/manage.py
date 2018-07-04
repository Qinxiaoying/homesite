# -*- coding: utf8 -*-
from app import app, db, models
from flask.ext.script import Manager, Server, Shell
from flask.ext.migrate import Migrate, MigrateCommand


migrate = Migrate(app, db)
manager = Manager(app)


def make_shell_context():
    return dict(app=app,db=db,Article=models.Article,
        User=models.User,Category=models.Category,
        Role=models.Role,Permission=models.Permission,
        Follow=models.Follow)


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
manager.add_command('runserver', Server(host = '0.0.0.0'))


if __name__ == '__main__':
    manager.run()