from flask import flash, redirect, render_template, request, session, Blueprint
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from helpers import apology, login_required
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os


dues = Blueprint('dues', __name__)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@dues.route("/dues")
@login_required
def dues_():
    """Display dues for user"""

    dues = db.execute("SELECT * FROM dues WHERE user_id = :id ORDER BY deadline", {"id": session["user_id"]}).fetchall()
    return render_template("dues.html", dues=dues)


@dues.route("/add/due", methods=["POST"])
@login_required
def add_due():
    """Add due"""

    subject = request.form.get("subject")
    s_type = request.form.get("type")
    required = request.form.get("required")
    deadline = request.form.get("deadline")
    if not subject or not s_type or not deadline:
        return apology("something went wrong")
    subject = subject.title()
    subjects = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                          {"id": session["user_id"]}).fetchall()
    for s in subjects:
        if subject == s[0]:
            q = db.execute("SELECT * FROM dues WHERE user_id = :id AND subject = :s AND type = :t AND required = :r AND deadline = :d",
                           {"id": session["user_id"], "t": s_type, "s": subject, "r": required, "d": deadline}).fetchone()
            if q:
                return apology("due already exists")
            try:
                db.execute("INSERT INTO dues (user_id, subject, type, required, deadline) VALUES(:id, :s, :t, :r, :d)",
                           {"id": session["user_id"], "t": s_type, "s": subject, "r": required, "d": deadline})
                db.commit()
            except:
                return apology("something went wrong with the database")
            flash("Due added!")
            return redirect("/dues")
    return apology("subject doesn't exist")


@dues.route("/delete/due", methods=["POST"])
@login_required
def delete_due():
    """Delete one due"""

    subject = request.form.get("subject")
    required = request.form.get("required")
    type_ = request.form.get("type")
    deadline = request.form.get("deadline")
    if not subject or not type_ or not deadline:
        return apology("something went wrong")
    q = db.execute("SELECT * FROM dues WHERE user_id = :id AND subject = :s AND type = :t AND required = :r AND deadline = :d",
                   {"id": session["user_id"], "s": subject, 't': type_, "r": required, "d": deadline}).fetchone()
    if not q:
        return apology("due doesn't exist")
    try:
        db.execute("DELETE FROM dues WHERE user_id = :id AND subject = :s AND type = :t AND required = :r AND deadline = :d",
                   {"id": session["user_id"], "s": subject, "t": type_, "r": required, "d": deadline})
        db.commit()
    except:
        return apology("something went wrong with the database")
    flash("Due deleted!")
    return redirect("/dues")


@dues.route("/delete/dues", methods=["POST"])
@login_required
def delete_dues():
    """Delete all dues"""

    try:
        db.execute("DELETE FROM dues WHERE user_id = :id", {"id": session["user_id"]})
        db.commit()
    except:
        return apology("something went wrong")
    flash("All dues deleted!")
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    dues.errorhandler(code)(errorhandler)