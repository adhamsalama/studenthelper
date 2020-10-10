from flask import flash, redirect, render_template, request, session, Blueprint
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from helpers import apology, login_required, connectdb


periods = Blueprint('periods', __name__)

# Set up database
db = connectdb()


@periods.route("/add/period", methods=["POST"])
@login_required
def add_period():
    """Adds a period"""

    subject = request.form.get("subject")
    subject_type = request.form.get("type")
    lecturer = request.form.get("lecturer")
    place = request.form.get("place")
    start = request.form.get("start")
    end = request.form.get("end")
    days = request.form.getlist("day")
    if not subject or not subject_type or not lecturer or not place or not start or not end or not days:
        return apology(message="please fill the form")
    if end <= start:
        return apology("end time is before start time")
    if len(subject) > 80:
        return apology("maximum subject length is 80 characters")
    if (len(lecturer) or len(place)) > 50:
        return apology("maximum lecturer or place length is 50 characters")
    # days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    # day = days.index(day)
    subject = subject.strip().title()
    subject_type = subject_type.capitalize()
    lecturer = lecturer.strip().title()
    place = place.strip().title()
    if subject_type not in ["Lab", "Lecture", "Section"]:
        return apology("invalid subject type")
    for day in days:
        q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND place = :p AND start_time = :s_t AND end_time = :e AND day = :d",
                       {"id": session["user_id"], "s": subject, "t": subject_type, "l": lecturer, "p": place, "s_t": start, "e": end, "d": day}).fetchall()
        if q:
            continue
        try:
            db.execute("INSERT INTO subjects (user_id, subject, type, lecturer, place, start_time, end_time, day) VALUES(:id, :subject, :type, :lecturer, :place, :start, :end, :day)",
                       {"id": session["user_id"], "subject": subject, "type": subject_type, "lecturer": lecturer, "place": place, "start": start, "end": end, "day": day})
            db.commit()
            session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                             {"id": session["user_id"]}).fetchall()
        except:
            return apology("something went wrong with the database")
    flash("Period added!")
    return redirect(f"/subjects/{subject}")


@periods.route("/edit/period", methods=["GET", "POST"])
@login_required
def edit_period():
    """Edit a subject"""
    if request.method == "POST":
        # recieved_token = request.form.get("token")
        # if not recieved_token or recieved_token != session["form_token"]:
        # return apology("fuck off cross-site forgeing piece of shit")
        subject = request.form.get("subject")
        subject_type = request.form.get("type")
        lecturer = request.form.get("lecturer")
        place = request.form.get("place")
        start = request.form.get("start")
        end = request.form.get("end")
        day = request.form.get("day")
        old_subject = request.form.get("old_subject")
        old_subject_type = request.form.get("old_type")
        old_lecturer = request.form.get("old_lecturer")
        old_place = request.form.get("old_place")
        old_start = request.form.get("old_start")
        old_end = request.form.get("old_end")
        old_day = request.form.get("old_day")
        if not subject or not subject_type or not lecturer or not place or not start or not end or not day:
            return apology("please fill the form")
        subject = subject.title()
        lecturer = lecturer.title()
        place = place.title()
        day = day.capitalize()
        if not old_subject or not old_subject_type or not old_lecturer or not old_place or not old_start or not old_end or not old_day:
            return apology("something went form")
        try:
            db.execute("UPDATE subjects SET subject = :s, type = :t, lecturer = :l, place = :p, start_time = :st, end_time = :e, day = :d WHERE user_id = :id AND subject = :o_s AND type = :o_t AND lecturer = :o_l AND place = :o_p AND start_time = :o_st AND end_time = :o_e AND day = :o_d",
                       {"s": subject, "t": subject_type, "p": place, "l": lecturer, "st": start, "e": end, "d": day, "id": session["user_id"],
                        "o_s": old_subject, "o_t": old_subject_type, "o_p": old_place, "o_l": old_lecturer, "o_st": old_start, "o_e": old_end, "o_d": old_day})
            db.commit()
        except:
            return apology("something went wrong")
        session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                         {"id": session["user_id"]}).fetchall()
        flash("Period edited!")
        return redirect(f"/subjects/{subject}")
    else:
        # token = secrets.token_hex()
        # session["form_token"] = token
        subject = request.args.get("subject")
        subject_type = request.args.get("type")
        lecturer = request.args.get("lecturer")
        place = request.args.get("place")
        start = request.args.get("start")
        end = request.args.get("end")
        day = request.args.get("day")
        if not subject or not subject_type or not lecturer or not place or not start or not end or not day:
            return apology(message="please fill the form")
        q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND place = :p AND start_time = :s_t AND end_time = :e AND day = :d",
                       {"id": session["user_id"], "s": subject, "t": subject_type, "l": lecturer, "p": place, "s_t": start, "e": end, "d": day}).fetchall()
        if not q:
            return apology("subject doesn't exist")
        return render_template("edit_period.html", subject=subject, type=subject_type,
                               lecturer=lecturer, place=place, start=start, end=end, day=day)


@periods.route("/delete/period", methods=["POST"])
@login_required
def delete_period():
    """Deletes one period"""

    s = request.form.get("subject")
    t = request.form.get("type")
    l = request.form.get("lecturer")
    d = request.form.get("day")
    p = request.form.get("place")
    st = request.form.get("start")
    e = request.form.get("end")
    if not s or not t or not l or not d or not p or not st or not e:
        return apology("something unusual happened")
    q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND day = :d AND place = :p AND start_time = :st AND end_time = :e",
                   {"id": session["user_id"], "s": s, "t": t, "l": l, "d": d, "p": p, "st": st, "e": e}).fetchall()
    if not q:
        return apology(message="subject doesn't exist")

    db.execute("DELETE FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND day = :d AND place = :p AND start_time = :st AND end_time = :e",
               {"id": session["user_id"], "s": s, "t": t, "l": l, "d": d, "p": p, "st": st, "e": e})
    db.commit()

    # Update session['subjects'] (used in navbar and filling forms) because this might be the last period of the subject (which deletes it entirely)
    subject_count = db.execute("SELECT COUNT(subject) FROM subjects WHERE user_id = :id AND subject = :s", {"id": session["user_id"], 's': s}).fetchone()[0]
    print(subject_count)
    if subject_count == 0:
        session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                         {"id": session["user_id"]}).fetchall()
        # Delete the subject's dues
        db.execute("DELETE FROM dues WHERE user_id = :id AND subject = :s", {"id": session["user_id"], "s": s})
        # Delete the subjetc's notes
        db.execute("DELETE FROM notes WHERE user_id = :id AND subject = :s", {"id": session["user_id"], "s": s})
        db.commit()
    flash("Period deleted!")
    return redirect("/schedule")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    periods.errorhandler(code)(errorhandler)
