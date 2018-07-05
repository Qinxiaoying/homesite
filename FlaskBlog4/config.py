# -*- coding: utf8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # wtf
    CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    # mail
    MAIL_SERVER = 'smtp.163.com'
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'bmobliam'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'mailbomb'
    MAIL_SENDER = os.environ.get('MAIL_SENDER') or 'FlaskBlog Admin <bmobliam@163.com>'
    MAIL_SUBJECT_PREFIX = '[FlaskBlog]'
    # administrator
    THISSITE_ADMIN = os.environ.get('THISSITE_ADMIN') or '758831425@qq.com'
    # set the number of articles to be shown per page
    ARTICLES_PER_PAGE = 7
    # set the location for the whoosh index
    WHOOSH_BASE = os.path.join(basedir,'whoosh_index')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'+os.path.join(basedir,'db.sqlite')


class TestingConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://root:123455@localhost:3306/blog'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://tjclimate:qhzx123@mysql.server/tjclimate$flask'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': TestingConfig
}