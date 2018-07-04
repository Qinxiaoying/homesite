FlaskBlog
=========

This is the Blog Engine built with Flask, Flask-SQLAlchemy, WTForms, Flask-WTF, Flask-Migrate and WebHelpers.

Installation
========

1. Git clone the repostory.
2. Install Flask, Flask-SQLAlchemy, WTForms, Flask-WTF, Flask-Migrate and Webhelpers using `pip` command.
3. Change the database settings inside `app/__init__.py` file.
4. Run the migration by this command

        $ python manage.py db init
        $ python manage.py db migrate
        $ python manage.py db upgrade

5. Run the server by this command
        
        $ python manage.py runserver

6. Enjoy!
