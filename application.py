from flask import Flask
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from helpers import apology, format_date, clean_markdown

from auth.routes import auth
from settings.routes import settings
from subjects.routes import subjects
from periods.routes import periods
from dues.routes import dues
from notes.routes import notes
from main.routes import main

app = Flask(__name__)
import os
from flask_sqlalchemy import SQLAlchemy

# Configure session to use filesystem

db = SQLAlchemy(app)
db.create_all()

app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#session = Session(app)
#session.app.session_interface.db.create_all()
#SqlAlchemySessionInterface(app, db, "sessions", "sess_")

app.register_blueprint(auth)
app.register_blueprint(settings)
app.register_blueprint(subjects)
app.register_blueprint(periods)
app.register_blueprint(dues)
app.register_blueprint(notes)
app.register_blueprint(main)


app.jinja_env.filters['clean_markdown'] = clean_markdown
app.jinja_env.filters['format_date'] = format_date


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
