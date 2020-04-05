from flask import flash, redirect, render_template, request, session, Blueprint
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os


subjects = Blueprint('subjects', __name__)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@subjects.route("/schedule")
@login_required
def schedule():
    """Display the user's schedule"""

    q = db.execute("SELECT * FROM subjects WHERE user_id = :id ORDER BY start_time", {"id": session["user_id"]}).fetchall()
    # Sorting subjects by days
    subjects = {"Saturday": [], "Sunday": [], "Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": []}
    days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    counter = 0
    for s in q:
        subjects[s["day"]].append(s)
        counter += 1
    return render_template("schedule.html", subjects=subjects, counter=counter)


@subjects.route("/subjects/<subject>")
@login_required
def subject(subject):
    """Display a subject for the user"""

    if not subject:
        return apology(message="subject not found")
    subject = subject.replace("_", " ")
    q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND subject ILIKE :subject",
                   {"id": session["user_id"], "subject": subject.replace("_", " ")}).fetchall()
    if not q:
        return apology("can't find subject")
    for s in q:
        if s["type"] == "Lecture":
            lecturer = s["lecturer"]
            break
    else:
        lecturer = q[0]["lecturer"]
    dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND subject ILIKE :s ORDER BY deadline",
                      {"id": session["user_id"], "s": subject}).fetchall()
    # Sort it
    subjects = {"Saturday": [], "Sunday": [], "Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": []}
    days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    counter = 0
    for s in q:
        subjects[s["day"]].append(s)
        counter += 1
    notes = db.execute("SELECT * FROM notes WHERE user_id = :id AND subject ILIKE :s ORDER BY date DESC", {"id": session["user_id"], "s": subject}).fetchall()
    return render_template("subject.html", info=subjects, subject=subject, counter=counter, lecturer=lecturer, dues=dues, notes=notes)


@subjects.route("/delete/all_subjects", methods=["POST"])
@login_required
def delete():
    """Delete all subjects"""
    try:
        db.execute("DELETE FROM subjects WHERE user_id = :id", {"id": session["user_id"]})
        db.execute("DELETE FROM dues WHERE user_id = :id", {"id": session["user_id"]})
        db.execute("DELETE FROM notes WHERE user_id = :id", {"id": session["user_id"]})
        db.commit()
    except:
        return apology("something went wrong")
    flash("Subjects deleted!")
    return redirect("/")


@subjects.route("/delete/subject", methods=["POST"])
@login_required
def delete_subject():
    """Deletes entire subject"""

    subject = request.form.get("subject")
    if not subject:
        return apology("subject doesn't exist")
    try:
        db.execute("DELETE FROM subjects WHERE user_id = :id AND subject = :s", {"id": session["user_id"], "s": subject})
        db.execute("DELETE FROM dues WHERE user_id = :id AND subject = :s", {"id": session["user_id"], "s": subject})
        db.execute("DELETE FROM notes WHERE user_id = :id AND subject = :s", {"id": session["user_id"], "s": subject})
        db.commit()
    except:
        return apology("somethign went wrong")
    # Update the session['subjects']
    session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                     {"id": session["user_id"]}).fetchall()
    flash("Subject deleted!")
    return redirect("/")


@subjects.route("/rename_subject", methods=["POST"])
@login_required
def rename_subject():
    old_name = request.form.get("old_name")
    new_name = request.form.get("new_name")
    if not old_name or not new_name:
        return apology("something went wrong")
    try:
        new_name = new_name.strip().title()
        if len(new_name) < 2:
            return apology("Nnew name must be more than 1 character long")
        db.execute("UPDATE subjects SET subject = :new_name WHERE subject = :old_name AND user_id = :id", {"new_name": new_name, "old_name": old_name, "id": session["user_id"]})
        db.execute("UPDATE dues SET subject = :new_name WHERE subject = :old_name AND user_id = :id", {"new_name": new_name, "old_name": old_name, "id": session["user_id"]})
        db.execute("UPDATE notes SET subject = :new_name WHERE subject = :old_name AND user_id = :id", {"new_name": new_name, "old_name": old_name, "id": session["user_id"]})
        db.commit()
        session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject", {"id": session["user_id"]}).fetchall()
        flash("Subject name updated!")
        return redirect(f"/subjects/{new_name.replace(' ', '_')}")
    except:
        return apology("something went wrong", 403)
