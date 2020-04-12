import os
import requests
import smtplib
from datetime import date
from flask import redirect, render_template, request, session
from functools import wraps
import bleach
from markdown import markdown
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


def connectdb():
    """Connects to a db"""
    # Check for environment variable
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")
    # Set up database
    engine = create_engine(os.getenv('DATABASE_URL'))
    db = scoped_session(sessionmaker(bind=engine))
    return db

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def send_email(email, name, subject, message):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(os.getenv("email"), os.getenv("password"))
    server.sendmail(os.getenv("email"), email, f"To: {email}\nSubject: {subject}\nHello {name},\n {message}")
    server.quit()


def quote_of_the_day():
    """ Get motivational quote of the day """
    try:
        response = requests.get("http://quotes.rest/qod.json?category=inspire")
        response.raise_for_status()
    except requests.RequestException:
        return None
    try:
        response = response.json()
        return {
            "quote": response["contents"]["quotes"][0]["quote"],
            "author": response["contents"]["quotes"][0]["author"],
        }
    except (KeyError, TypeError, ValueError):
        return None


def clean_markdown(note):
    """Cleans notes and converts them to markdown"""
    
    return markdown(bleach.clean(note))
    

def format_date(d):
    """Formats a date"""

    return d.strftime("%A %B %d %Y")