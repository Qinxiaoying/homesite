# -*- coding: utf8 -*-
import datetime
import hashlib
from flask import current_app, request
from webhelpers.date import time_ago_in_words
from webhelpers.text import urlify
from werkzeug.security import generate_password_hash, check_password_hash
#import flask.ext.whooshalchemy as whooshalchemy
import flask_whooshalchemy_zh as whooshalchemy
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from . import app, db


def beijingtime():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MORERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User',backref='role',lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User':(Permission.FOLLOW |
                    Permission.COMMENT |
                    Permission.WRITE_ARTICLES, True),
            'Moderator':(Permission.FOLLOW |
                    Permission.COMMENT |
                    Permission.WRITE_ARTICLES |
                    Permission.MORERATE_COMMENTS, False),
            'Administrator':(0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return u'<Role %s>' % self.name


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=beijingtime)


class Collection(db.Model):
    __tablename__ = 'collections'
    collector_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=beijingtime)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64), unique=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    pwdhash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    nickname = db.Column(db.String(64))
    location = db.Column(db.String(64), default=u'E星球')
    about_me = db.Column(db.Text, default=u'这家伙骨头真硬，啥都不肯说……')
    member_since = db.Column(db.DateTime, default=beijingtime)
    last_seen = db.Column(db.DateTime, default=beijingtime)
    avatar_hash = db.Column(db.String(32))
    articles = db.relationship('Article',backref='user',lazy='dynamic')
    followed = db.relationship('Follow',
                                foreign_keys=[Follow.follower_id],
                                backref=db.backref('follower', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    collected = db.relationship('Collection',
                                foreign_keys=[Collection.collector_id],
                                backref=db.backref('collector', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def __init__(self, name, nickname, email, password):
        self.name = name
        self.nickname = nickname
        self.email = email.lower() # 小写
        self.set_password(password)
        if self.role is None:
            if self.email == current_app.config['THISSITE_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first() # 管理员
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first() # 默认角色，普通用户
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()

    def __repr__(self):
        return '<User %r>' % self.name

    def set_password(self, password):
        self.pwdhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pwdhash, password)

    def last_login(self):
        self.last_seen = beijingtime()
        db.session.add(self)
        db.session.commit()

    @property
    def last_seen_time_ago(self):
        return time_ago_in_words(self.last_seen)

    @classmethod
    def all(cls):
        return User.query.all()

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
            db.session.commit()

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
            db.session.commit()

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def is_collecting(self, article):
        return self.collected.filter_by(collected_id=article.id).first() is not None

    def collect(self, article):
        if not self.is_collecting(article):
            c = Collection(collector=self, collected=article)
            db.session.add(c)
            db.session.commit()

    def uncollect(self, article):
        c = self.collected.filter_by(collected_id=article.id).first()
        if c:
            db.session.delete(c)
            db.session.commit()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'  # 'http://gravatar.duoshuo.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    @property
    def followed_articles(self):
        return Article.query.join(Follow, Follow.followed_id == Article.user_id)\
            .filter(Follow.follower_id == self.id)


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=beijingtime)
    articles = db.relationship('Article',backref='category',lazy='dynamic')

    def __unicode__(self):
        return self.name

    # def __str__(self):
    #     return '<Category %s>' % self.name

    @classmethod
    def all(cls):
        return Category.query.all()


class Article(db.Model):
    __tablename__ = 'articles'
    __searchable__ = ['title', 'body'] # these fields will be indexed by whoosh
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    body = db.Column(db.Text)
    created = db.Column(db.DateTime, default=beijingtime)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', onupdate="CASCADE", ondelete="CASCADE"))
    read = db.Column(db.Integer, server_default='0', nullable=False)
    collectors = db.relationship('Collection',
                                foreign_keys=[Collection.collected_id],
                                backref=db.backref('collected', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def __unicode__(self):
        return self.name

    # def __repr__(self):
    #     return '<Article %s>' % self.title

    @classmethod
    def counts(cls):
        return Article.query.count()

    @classmethod
    def all(cls):
        return Article.query.order_by(Article.created.desc()).all()

    @classmethod
    def last(cls, limit=10, page=0):
        offset = page * limit
        return Article.query.order_by(Article.created.desc()).limit(limit).offset(offset).all()

    @classmethod
    def top_10_read(cls, n=10):
        return Article.query.order_by(Article.read.desc()).order_by(Article.created.desc()).limit(n).all()
 
    @property
    def slug(self):
        try:
            return urlify(self.title)
        except:
            return urlify(self.title.encode('gbk')) # .encode('gbk') 解决标题是中文的问题
 
    @property
    def created_time_ago(self):
        return time_ago_in_words(self.created)

    def is_collected_by(self, user):
        return self.collected.filter_by(user_id=user.id).first() is not None


""" 创建搜索的索引 """
whooshalchemy.whoosh_index(app, Article)

