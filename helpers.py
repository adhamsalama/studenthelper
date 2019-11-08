import os
import requests
import urllib.parse
import smtplib

from datetime import date
from flask import redirect, render_template, request, session
from functools import wraps


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


def send_email(email, name, message):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("the.student.helper.11@gmail.com", "thestudenthelper")
    server.sendmail("the.student.helper.11@gmail.com", email, f"To: {email}\nSubject: Registeration for Student Helper\nHello {name},\n {message}")

def get_time():
    """Get time"""
    return str(date.today())
