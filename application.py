from flask import Flask, session, Blueprint
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, format_date
import bleach
from markdown import markdown
from helpers import clean_markdown

from auth.routes import auth
from settings.routes import settings
from subjects.routes import subjects
from periods.routes import periods
from dues.routes import dues
from notes.routes import notes
from others.routes import others

app = Flask(__name__)

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


app.register_blueprint(auth)
app.register_blueprint(settings)
app.register_blueprint(subjects)
app.register_blueprint(periods)
app.register_blueprint(dues)
app.register_blueprint(notes)
app.register_blueprint(others)


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
