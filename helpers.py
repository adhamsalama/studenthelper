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


def lookup(isbn):
    """Look up book for reviews."""

    # Contact API
    try:
        #api_key = os.environ.get("API_KEY")
        response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "WHj59OKYTc5wetwygm5g", "isbns": isbn})
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        book = response.json()
        return {
            "ratings_count" : book["books"][0]["work_ratings_count"],
            "average_rating" : book["books"][0]["average_rating"],
            # "isbn": book["books"][0]["isbn"]
        }
    except (KeyError, TypeError, ValueError):
        return None

def send_email(email, name, message):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("aaa.books1@gmail.com", "adhamsalama123")
    server.sendmail("aaa.books1@gmail.com", email, f"To: {email}\nSubject: Registeration for AAA Books\nHello {name},\n {message}")

def get_time():
    """Get time"""
    return str(date.today())
