# -*- coding: utf8 -*-
import os
import math
import random
import datetime
from functools import wraps
from flask import render_template, request, session, url_for, redirect, current_app, g, \
                    flash, abort, make_response, Markup, escape, jsonify

from . import app, db
from .models import User, Article, Category, Follow, Permission
from .forms import SignupForm, ArticleCreateForm, \
                    SigninForm, CategoryCreateForm, UserUpdateForm
from .myhtmlstrip import myhtmlstrip, mytimestrip, mycreatedstrip
from .email import send_email
from .flash_alert import flash_alert


@app.before_request
def before_request():
    g.user = None
    user_id = session.get('user_id')
    if user_id:
        g.user = User.query.filter_by(id=user_id).first()


def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kw):
        # 未登录状态不不允许访问的路由，重定向到首页
        if not g.user:
            return redirect(url_for('signin'))
        wrapped = f(*args,**kw)
        return wrapped
    return decorated_function


def confirmed_required(f):
    @wraps(f)
    def decorated_function(*args,**kw):
        # 未确认邮件账户的用户不能访问，重定向到 dashboard
        if not g.user.confirmed:
            return redirect(url_for('author',name=g.user.name))
        wrapped = f(*args,**kw)
        return wrapped
    return decorated_function


def logout_required(f):
    @wraps(f)
    def decorated_function(*args,**kw):
        # 已登录状态下不可再访问登录和注册页面，返回 404
        if g.user:
            abort(403)
        wrapped = f(*args,**kw)
        return wrapped
    return decorated_function


def ip_access(f):
    @wraps(f)
    def decorated_function(*args,**kw):
        # 只有 IP 所列的 ip 用户可以访问，否则返回 405
        try:
            IP = request.headers['X-Real-IP']
        except:
            IP = request.remote_addr
        IPs = ['10.226.110', '127.0.0.1', '::1']
        if True not in map(lambda x:IP.startswith(x), IPs):
            abort(403)
        wrapped = f(*args,**kw)
        return wrapped
    return decorated_function


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args,**kwargs):
            if not g.user.can(permission):
                abort(403)
            return f(*args,**kwargs)
        return decorated_function
    return decorator


def admin_requried(f):
    return permission_required(Permission.ADMINISTER)(f)


@app.route('/')
def index():
    page = request.args.get('page', 0, type=int)
    try:
        # last 10 articles in sidebar
        last_10_articles = Article.last(limit=10, page=0)
        # show 7 articles per page in main
        articles = Article.last(limit=app.config['ARTICLES_PER_PAGE'], page=page)
        # lastpage
        lastpage = int(math.ceil(float(Article.counts())/app.config['ARTICLES_PER_PAGE']))
    except:
        abort(500)
    # query all users and categorys
    users, categorys = User.all(), Category.all()
    # init {user:number-of-articles} and {category:number-of-articles}
    user_articles, category_articles = {}, {}
    # get the dicts
    for u in users:
        user_articles.update({u.name:u.articles.count()})
    for c in categorys:
        category_articles.update({c.name:c.articles.count()})
    # sort dict by values in reversed order
    user_articles = sorted(user_articles.iteritems(), key=lambda x : x[1], reverse=True)
    category_articles = sorted(category_articles.iteritems(), key=lambda x : x[1], reverse=True)
    # top_10_read
    top_10_read = Article.top_10_read()
    return render_template('index.html',
        articles=articles, last_10_articles=last_10_articles, user_articles=user_articles,
        category_articles=category_articles, top_10_read=top_10_read,
        lastpage=lastpage, perpage=app.config['ARTICLES_PER_PAGE'], page=page)


@app.route('/_load_more')
def load_more():
    # get page
    page = request.args.get('page', 1, type=int)
    try:
        # load data from Database
        thispage = Article.last(limit=app.config['ARTICLES_PER_PAGE'], page=page)
        nextpage = Article.last(limit=app.config['ARTICLES_PER_PAGE'], page=page+1)
        # init return
        myjson = jsonify({'isnextpage':'none'})
        isnextpage = 'more' if nextpage else 'no_more'
    except:
        # error in connection to database
        thispage = None
        myjson = jsonify({'isnextpage':'error'})
    # format data to json if thispage != []
    if thispage:
        lens, title, user_name, created, category_name, read, body, art_url, name_url, cat_url = \
            [list(range(len(thispage))) for k in range(10)]
        for i in lens:
            title[i] = escape(thispage[i].title) # escape
            user_name[i] = escape(thispage[i].user_name) # escape
            category_name[i] = escape(thispage[i].category_name) # escape
            created[i] = mycreatedstrip(str(thispage[i].created))
            read[i] = thispage[i].read or 0
            body[i] = myhtmlstrip(thispage[i].body, n=3)
            art_url[i] = url_for('show_article', id=thispage[i].id, slug=thispage[i].slug)
            name_url[i] = url_for('author', name=thispage[i].user_name)
            cat_url[i] = url_for('category_articles', category=thispage[i].category_name)
        myjson = jsonify({'title':title, 'user_name':user_name, 'created':created,
            'category_name':category_name, 'read':read, 'body':body,
            'art_url':art_url, 'name_url':name_url, 'cat_url':cat_url,
            'lens':len(thispage), 'isnextpage':isnextpage })
    return myjson


@app.route('/signup', methods=['GET', 'POST'])
@logout_required
@ip_access
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        user = User(form.name.data, form.nickname.data, form.email.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        user = User.query.filter_by(name=user.name).first()
        session['user_id'] = user.id
        g.user = user
        token = g.user.generate_confirmation_token()
        send_email(g.user.email, '确认您的帐户', 'mail/confirm', user=g.user, token=token)
        flash_alert(
            Markup(u"尊敬的<strong>%s</strong>，一封确认邮件已发送至您的邮箱，请查收！") % g.user.name,
            typename="info"
        )
        if current_app.config['THISSITE_ADMIN']:
            send_email(current_app.config['THISSITE_ADMIN'], '新用户注册', 'mail/new_user', user=g.user)
        return redirect(url_for('author',name=g.user.name))
    return render_template('signup.html', form=form)


@app.route('/confirm/<token>')
@login_required
def confirm(token):
    if g.user.confirmed:
        return redirect(url_for('author',name=g.user.name))
    if g.user.confirm(token):
        flash_alert(u'您的账户已确认，谢谢！')
    else:
        flash_alert(u'抱歉，确认链接不正确或已过期！', typename="danger")
    return redirect(url_for('author',name=g.user.name))


@app.route('/reconfirm')
@login_required
def resend_confirmation():
    token = g.user.generate_confirmation_token()
    send_email(g.user.email, 'Confirm Your Account', 'mail/confirm', user=g.user, token=token)
    flash_alert(u'一封新的确认邮件已发送至您的邮箱！', typename="info")
    return redirect(url_for('author',name=g.user.name))


@app.route('/create', methods=['GET', 'POST'])
@login_required
@confirmed_required
def article_create():
    article = Article(user_id=g.user.id)
    form = ArticleCreateForm()
    if form.validate_on_submit():
        form.populate_obj(article)
        db.session.add(article)
        db.session.commit()
        flash_alert(Markup(u"<strong>%s</strong> 已发表成功") % article.title)
        return redirect(url_for('author',name=g.user.name))
    return render_template('article_create.html', form=form)


@app.route('/signin', methods=['GET', 'POST'])
@logout_required
def signin():
    form = SigninForm()
    if form.validate_on_submit():
        email = form.email.data
        g.user = User.query.filter_by(email=email).first()
        session['user_id'] = g.user.id
        g.user.last_login()
        flash_alert(Markup(u"欢迎 <strong>%s</strong>") % g.user.name, typename="info")
        return redirect(url_for('author',name=g.user.name))
    return render_template('signin.html', form=form)


@app.route('/signout')
@login_required
def signout():
    name = g.user.name
    session.pop('user_id', None)
    flash_alert(Markup(u"<strong>%s</strong> 已退出") % name, typename="info")
    return redirect(url_for('index'))


@app.route('/article/<int:id>/<slug>')
def show_article(id, slug):
    article = Article.query.get_or_404(id)
    if article.read is None: article.read = 0
    article.read += 1
    db.session.merge(article)
    db.session.commit()
    before = Article.query.filter(Article.created<article.created).order_by(Article.created.desc()).first()
    after = Article.query.filter(Article.created>article.created).first()
    before_and_after = {'before':before, 'after':after}
    return render_template('article_view.html', article=article, before_and_after=before_and_after)


@app.route('/article/<int:id>/<slug>/edit', methods=['GET', 'POST'])
@login_required
@confirmed_required
def article_update(id, slug):
    article = Article.query.get_or_404(id)
    title = article.title
    form = ArticleCreateForm(request.form, article)
    # 登录的用户不能编辑别人的文章
    if article.user_id != g.user.id:
        abort(403)
    if form.validate_on_submit():
        form.populate_obj(article)
        db.session.add(article)
        db.session.commit()
        flash_alert(Markup(u"已更新 <strong>%s</strong>") % title)
        return redirect(url_for('author',name=g.user.name))
    return render_template('article_create.html', form=form)


@app.route('/category/create', methods=['GET', 'POST'])
@login_required
@confirmed_required
def category():
    form = CategoryCreateForm()
    category = Category()
    created_categories = Category.all()
    if form.validate_on_submit():
        form.populate_obj(category)
        db.session.add(category)
        db.session.commit()
        flash_alert(Markup(u"已创建分类 <strong>%s</strong>") % escape(form.name.data))
        return redirect(url_for('category'))
    return render_template('category_create.html', form=form, created_categories=created_categories)


@app.route('/author/<name>', methods=['GET'])
def author(name):
    author = User.query.filter_by(name=name).first()
    if not author:
        abort(404)
    return render_template('author.html', author=author)


@app.route('/category/<category>', methods=['GET'])
def category_articles(category):
    category = Category.query.filter_by(name=category).first()
    if not category:
        abort(404)
    return render_template('category_view.html', category=category)


@app.route('/article/<int:id>/<slug>/delete', methods=['GET','POST'])
@login_required
@confirmed_required
def delete(id, slug):
    article = Article.query.get_or_404(id)
    title = article.title
    # 登录的用户不能删除别人的文章
    if article.user_id != g.user.id:
        abort(403)
    db.session.delete(article)
    db.session.commit()
    flash_alert(Markup(u"已删除 <strong>%s</strong>") % title)
    return redirect(url_for('author',name=g.user.name))
	

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = UserUpdateForm(request.form, g.user)
    if form.validate_on_submit():
        g.user.name = form.name.data
        g.user.nickname = form.nickname.data
        g.user.location = form.location.data
        g.user.about_me = form.about_me.data
        g.user.set_password(form.password.data)
        db.session.merge(g.user)
        db.session.commit()
        flash_alert(u"信息已更新")
    return render_template('settings.html', form=form)


@app.route('/author/delete', methods=['GET','POST'])
@login_required
def delete_profile():
    # 注销时删除自己所有文章
    articles = g.user.articles.all()
    for a in articles:
        db.session.delete(a)
    db.session.delete(g.user)
    db.session.commit()
    name = g.user.name
    session.pop('user_id', None)
    flash_alert(Markup(u"<strong>%s</strong> 已注销") % name)
    return redirect(url_for('index'))


# ckupload for CKEditor
def gen_rnd_filename():
    filename_prefix = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return '%s%s' % (filename_prefix, str(random.randrange(1000, 10000)))


@app.route('/ckupload/', methods=['POST', 'OPTIONS'])
@login_required
@confirmed_required
def ckupload():
    name = g.user.name

    """CKEditor file upload"""
    error, url, callback = '', '', request.args.get("CKEditorFuncNum")

    if request.method == 'POST' and 'upload' in request.files:
        fileobj = request.files['upload']
        fname, fext = os.path.splitext(fileobj.filename)
        rnd_name = '%s%s%s' % (name, gen_rnd_filename(), fext)

        filepath = os.path.join(app.static_folder, 'upload', rnd_name)

        dirname = os.path.dirname(filepath)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                error = 'ERROR_CREATE_DIR'
        elif not os.access(dirname, os.W_OK):
            error = 'ERROR_DIR_NOT_WRITEABLE'

        if not error:
            fileobj.save(filepath)
            url = url_for('static', filename='%s/%s' % ('upload', rnd_name))
    else:
        error = 'post error'

    res = """<script type="text/javascript">
    window.parent.CKEDITOR.tools.callFunction('%s', '%s', '%s');
    </script>""" % (callback, url, error)

    response = make_response(res)
    response.headers["Content-Type"] = "text/html"
    return response


@app.route('/search', methods=['GET','POST'])
def search():
    # if request.method == 'POST':
    #     keyword = request.form.get('keyword')
    # if request.method == 'GET':
    #     keyword = request.args.get('keyword')
    keyword = request.values.get('keyword')
    result = Article.query.whoosh_search(keyword).all()
    return render_template('search.html', keyword=keyword, result=result)


@app.route('/follow/<name>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(name):
    user = User.query.filter_by(name=name).first()
    if not user:
        abort(404)
    if g.user.is_following(user):
        flash_alert(Markup(u'不能重复关注<strong>%s</strong>' % name), typename="warning")
        return redirect(url_for('author', name=name))
    g.user.follow(user)
    flash_alert(Markup(u'您已关注<strong>%s</strong>' % name))
    return redirect(url_for('author', name=name))


@app.route('/unfollow/<name>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(name):
    user = User.query.filter_by(name=name).first()
    if not user:
        abort(404)
    if not g.user.is_following(user):
        flash_alert(Markup(u'您尚未关注<strong>%s</strong>' % name), typename="warning")
        return redirect(url_for('author', name=name))
    g.user.unfollow(user)
    flash_alert(Markup(u'您已取消关注<strong>%s</strong>' % name))
    return redirect(url_for('author', name=name))


# 我的粉丝
@app.route('/author/<name>/follower')
def follower(name):
    user = User.query.filter_by(name=name).first()
    if not user:
        abort(404)
    followers = user.followers.all()
    return render_template('follower.html', user=user, followers=followers)


# 我关注的
@app.route('/author/<name>/followed')
def followed(name):
    user = User.query.filter_by(name=name).first()
    if not user:
        abort(404)
    followeds = user.followed.all()
    return render_template('followed.html', user=user, followeds=followeds)


# 我的收藏
@app.route('/author/<name>/collect')
def collect(name):
    return render_template('collect.html')


# 全部作者
@app.route('/author')
def author_all():
    return render_template('author_all.html')


# 全部分类
@app.route('/category')
def category_all():
    return render_template('category_all.html')


@app.errorhandler(403)
def HTTPNotFound(e):
    return render_template('error403.html'), 403


@app.errorhandler(404)
def HTTPNotFound(e):
    return render_template('error404.html'), 404


@app.errorhandler(405)
def HTTPNotAllowed(e):
    return render_template('error405.html'), 405


@app.errorhandler(500)
def ServerError(e):
    return render_template('error500.html'), 500