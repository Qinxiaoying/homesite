# -*- coding: utf8 -*-
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail

from config import config

app = Flask(__name__)
app.config.from_object(config['default'])

db = SQLAlchemy(app)
mail = Mail(app)

from . import models, views

@app.context_processor
def inject_permissions():
    return dict(Permission=models.Permission,Article=models.Article)

from .myhtmlstrip import myhtmlstrip, mytimestrip, mycreatedstrip
env = app.jinja_env
env.filters['myhtmlstrip'] = myhtmlstrip
env.filters['mytimestrip'] = mytimestrip
env.filters['mycreatedstrip'] = mycreatedstrip
