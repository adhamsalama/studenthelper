from flask import Flask, flash, json, jsonify, redirect, render_template, request, session, Blueprint
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from cachetools import TTLCache
import time
import bleach
import os
from datetime import *
from markdown import markdown


settings = Blueprint('settings', __name__)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@settings.route("/settings/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change user password"""

    if request.method == "GET":
        return render_template("change_password.html")
    else:
        password = request.form.get("password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")
        pw_hash = db.execute("SELECT hash FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()["hash"]
        if not password or not new_password or new_password != confirmation:
            return apology("please fill the form correctly")
        elif password == new_password:
            return apology(message="new and old password can't be the same")
        elif not check_password_hash(pw_hash, password):
            return apology(message="incorrect password")
        else:
            # Specifications for password
            # password length
            if len(new_password) < 6:
                return apology(message="password must be longer than 6 characters")
            capital = None
            lower = None
            for c in new_password:
                if c.isupper():
                    capital = True
                if c.islower():
                    lower = True
            if not capital and not lower:
                return apology(message="password must contain atleast 1 uppercase and lowercase letter")
            # password must contain numbers
            if new_password.isalpha():
                return apology(message="password must contain numbers")
            # password must contain letters
            if new_password.isdigit():
                return apology(message="password must contain letters")
            db.execute("UPDATE users SET hash = :new_password WHERE id = :id",
                       {"new_password": generate_password_hash(new_password), "id": session["user_id"]})
            db.commit()
            flash("Password updated!")
            return redirect("/")


@settings.route("/settings/change_email", methods=["GET", "POST"])
@login_required
def change_email():
    """Change user email"""

    if request.method == "GET":
        return render_template("change_email.html")
    else:
        email = request.form.get("email")
        new_email = request.form.get("new_email")
        if not email or not new_email:
            return apology(message="please fill the form")
        emails = db.execute("SELECT email FROM users WHERE email = :email", {"email": new_email}).fetchone()
        if email != session["email"]:
            return apology(message="wrong email")
        if emails:
            return apology(message="email already taken")
        else:
            db.execute("UPDATE users SET email = :new_email WHERE id = :id",
                       {"new_email": new_email, "id": session["user_id"]})
            db.commit()
            session["email"] = new_email
            try:
                send_email(email, session["username"], "Changing email", "Your email was successfully changed!")
            except Exception as x:
                print(x)
            flash("Email updated!")
            return redirect("/profile")


@settings.route("/settings/add_email", methods=["GET", "POST"])
@login_required
def add_email():
    """Add email to user account"""

    if request.method == "GET":
        return render_template("add_email.html")
    else:
        email = request.form.get("email")
        if not email:
            return apology(message="please enter an email")
        q = db.execute("SELECT email FROM users WHERE email = :email", {"email": email}).fetchone()
        if q:
            return apology(message="this email is already taken")
        try:
            db.execute("UPDATE users SET email = :new_email WHERE id = :id",
                   {"new_email": email, "id": session["user_id"]})
            db.commit()
        except:
            return apology("something went wrong")
        try:
            send_email(email, session["username"], "Adding email", "Your email was successfully added to your account!")
        except Exception as x:
            print(x)
        session["email"] = email
        flash("Email added!")
        return redirect("/profile")


@settings.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    """Get user feedback"""

    if request.method == "GET":
        return render_template("feedback.html")
    else:
        feedback_type = request.form.get("type")
        feedback = request.form.get("feedback")
        if not feedback_type or not feedback:
            return apology("please fill the form")
        try:
            db.execute("INSERT INTO user_feedback (id, feedback, type) VALUES(:id, :feedback, :type)",
                       {"id": session["user_id"], "feedback": feedback, "type": feedback_type})
            db.commit()
        except:
            return apology("something went wrong with the database")
        flash("Feedback submitted! Thanks for your feedback!")
        return redirect("/")


@settings.route("/update_date", methods=["POST"])
@login_required
def update_date():
    """Updates the date"""

    week_days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if not request.form.get('today_date'):
        return apology("something went wrong")
    today_date = request.form.get('today_date')
    today_date = today_date.split("-")
    try:
        today_date = datetime(int(today_date[2]), int(today_date[0]), int(today_date[1]))
    except:
        return apology("incorrect Date")
    session['today_name'] = today_date.strftime("%A")
    session['tomorrow_name'] = week_days[(week_days.index(session['today_name']) + 1) % 7]
    session['today_date'] = today_date.strftime("%D")
    session['tomorrow_date'] = (today_date + timedelta(days=1)).strftime("%D")
    session['full_date'] = session['today_name'] + ", " + today_date.strftime("%b %d %Y")

    return redirect("/")


@settings.route("/add/uni", methods=["POST"])
@login_required
def add_uni():
    """Add university to user account"""

    uni = request.form.get("university")
    if not uni:
        return apology("please enter university")
    uni = uni.title()
    try:
        db.execute("UPDATE users SET university = :uni WHERE id= :id", {"id": session["user_id"], "uni": uni})
        db.commit()
        session["uni"] = uni
    except:
        return apology("something went wrong")
    flash("University added!")
    return redirect("/profile")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    settings.errorhandler(code)(errorhandler)
    