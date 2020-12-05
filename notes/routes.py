from flask import flash, redirect, render_template, request, session, Blueprint
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from helpers import apology, login_required, connectdb


notes = Blueprint('notes', __name__)

# Set up database
db = connectdb()


@notes.route("/notes")
@login_required
def notes_():
    notes = db.execute("SELECT * FROM notes WHERE user_id = :id ORDER BY id DESC", {"id": session["user_id"]}).fetchall()
    return render_template("notes.html", notes=notes)


@notes.route("/add/note", methods=["POST"])
@login_required
def add_note():
    subject = request.form.get("subject")
    note = request.form.get("note")
    current_date = request.form.get("current_date")
    if not subject or not note:
        return apology("please fill the form")
    try:
        db.execute("INSERT INTO notes (user_id, subject, note, date) VALUES(:id, :s, :n, :d)", {"id": session["user_id"], "s": subject, "n": note, "d": current_date})
        db.commit()
    except:
        return apology("something went wrong")
    flash("Note added!")
    return redirect("/notes")


@notes.route("/edit/note", methods=["GET", "POST"])
@login_required
def edit_note():
    if request.method == "GET":
        subject = request.args.get("subject")
        note = request.args.get("note")
        if not subject or not note:
            return apology("something went wrong")
        return render_template("edit_note.html", subject=subject, note=note)
    else:
        subject = request.form.get("subject")
        note = request.form.get("note")
        old_subject = request.form.get("old_subject")
        old_note = request.form.get("old_note")
        if not subject or not note or not old_subject or not old_note:
            return apology("something went wrong")
        q = db.execute("SELECT * FROM notes WHERE user_id = :id AND subject = :s AND note = :n",
                       {"id": session["user_id"], "s": old_subject, "n": old_note}).fetchone()
        if not q:
            return apology("note doesn't exist")
        try:
            db.execute("UPDATE notes SET subject = :s, note = :n WHERE user_id = :id AND subject = :o_s AND note = :o_n",
                       {"id": session["user_id"], "s": subject, "n": note, "o_s": old_subject, "o_n": old_note})
            db.commit()
        except:
            return apology("something went wrong")
        flash("Note edited!")
        return redirect("/notes")


@notes.route("/delete/note", methods=["POST"])
@login_required
def delete_note():
    subject = request.form.get("subject")
    note = request.form.get("note")
    if not subject or not note:
        return apology("something went wrong")
    try:
        db.execute("DELETE FROM notes WHERE user_id = :id AND subject = :s AND note = :n", {"id": session["user_id"], "s": subject, "n": note})
        db.commit()
    except Exception as x:
        return apology(x)
    flash("Note deleted!")
    return redirect("/notes")

@notes.route("/delete/notes", methods=["POST"])
@login_required
def delete_notes():
    db.execute("DELETE FROM notes WHERE user_id = :id", {"id": session["user_id"]})
    db.commit()
    flash("All notes deleted!")
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    notes.errorhandler(code)(errorhandler)