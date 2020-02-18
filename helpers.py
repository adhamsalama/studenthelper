import requests
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


def send_email(email, name, subject, message):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login("the.student.helper.11@gmail.com", "!7jwO2Efw5ViPTSMXEWo3$!k9N7qv^C")
    server.sendmail("the.student.helper.11@gmail.com", email, f"To: {email}\nSubject: {subject}\nHello {name},\n {message}")
    server.quit()

def get_time():
    """Get time"""
    return str(date.today())

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
