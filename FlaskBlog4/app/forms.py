# -*- coding: utf8 -*-
from flask import g
from flask.ext.wtf import Form
from wtforms import TextField, PasswordField, TextAreaField, HiddenField
from wtforms.validators import InputRequired, Email, EqualTo, Length, ValidationError, Regexp
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from .models import User,Category


strip_filter = lambda x: x.strip() if x else None


def category_choice():
    return Category.query.all()


class ArticleCreateForm(Form):
    title = TextField('Title', [InputRequired(u"请输入标题")], filters=[strip_filter])
    body = TextAreaField('Body', [InputRequired(u"请输入正文")], filters=[strip_filter])
    category = QuerySelectField('Category', query_factory=category_choice, get_label="name")


class SignupForm(Form):
    name = TextField("First name", [InputRequired(u"请输入姓名"),
        Regexp(ur"[\u4e00-\u9fa5]+", message=u"姓名必须为中文")], filters=[strip_filter])
    nickname = TextField("Last name", [InputRequired(u"请输入昵称")], filters=[strip_filter])
    email = TextField("Email", [InputRequired(u"请输入Email"), Email(u"请输入Email")])
    password = PasswordField('Password', [InputRequired(u"请输入密码"),
        Regexp(r'^[0-9a-zA-Z]{2,10}$', message=u"密码只允许2-10位的数字和字母"),
        EqualTo('password_confirm', message=u"两次密码输入不一致")])
    password_confirm = PasswordField('Password_confirm', [InputRequired(u"请再次输入密码")])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):return False
        user_in_this_name = User.query.filter_by(name=self.name.data).first()
        user_in_this_email = User.query.filter_by(email=self.email.data.lower()).first()
        if user_in_this_name:
            self.name.errors.append(u"姓名已被使用");return False
        elif user_in_this_email:
            self.email.errors.append(u"Email已被使用");return False
        else:
            return True


class SigninForm(Form):
    email = TextField("email", [InputRequired(u"请输入Email")])
    password = PasswordField('Password', [InputRequired(u"请输入密码")])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):return False
        user = User.query.filter_by(email=self.email.data.lower()).first()
        if user and user.check_password(self.password.data):
            return True
        else:
            self.email.errors.append(u"用户名或密码错误");return False
			

class CategoryCreateForm(Form):
    name = TextField('Name', [InputRequired(u"请输入分类名"),
        Length(min=1, max=20, message=u"分类名字符数不能超过20")], filters=[strip_filter])
    description = TextAreaField('Description', [InputRequired(u"请输入描述"),
        Length(min=1, max=140, message=u"描述字符数不能超过140")], filters=[strip_filter])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):return False
        if Category.query.filter_by(name=self.name.data).first():
            self.name.errors.append(u'分类已存在');return False
        else:
            return True


class UserUpdateForm(Form):
    name = TextField("Name", [InputRequired(u"请输入姓名"),
        Regexp(ur"[\u4e00-\u9fa5]+", message=u"姓名必须为中文")], filters=[strip_filter])
    nickname = TextField("Nickname", [InputRequired(u"请输入昵称")], filters=[strip_filter])
    password = PasswordField('Password', [InputRequired(u"请输入新密码"),
        Regexp(r'^[0-9a-zA-Z]{2,10}$', message=u"密码只允许2-10位的数字和字母"),
        EqualTo('password_confirm', message=u"两次密码输入不一致")])
    password_confirm = PasswordField('Password_confirm', [InputRequired(u"请再次输入密码")])
    location = TextField("Location", [Length(min=0, max=20, message=u"地址字符数不能超过20")], filters=[strip_filter])
    about_me = TextAreaField('About me', [Length(min=0, max=140, message=u"简介字符数不能超过140")], filters=[strip_filter])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self):
        if not Form.validate(self):return False
        user_in_this_name = User.query.filter_by(name=self.name.data).first()
        if user_in_this_name and user_in_this_name.id != g.user.id:
            self.name.errors.append(u"姓名已被使用");return False
        else:
            return True
