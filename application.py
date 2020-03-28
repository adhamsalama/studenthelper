from flask import Flask, flash, json, jsonify, redirect, render_template, request, session
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


app = Flask(__name__)


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


cache = TTLCache(maxsize=10, ttl=86400)
cache["quote"] = quote_of_the_day()

week_days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

def clean_markdown(note):
    """Cleans notes and converts them to markdown"""
    
    return markdown(bleach.clean(note))


app.jinja_env.filters['clean_markdown'] = clean_markdown

@app.route("/")
@login_required
def index():
    """Display index page"""
    try:
        quote = cache["quote"]
    except:
        cache["quote"] = quote_of_the_day()
        quote = cache["quote"]

    today_subjects = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :day ORDER BY start_time",
                   {"id": session["user_id"], "day": session['today_name']}).fetchall()
    tomorrow_subjects = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :next ORDER BY start_time",
                         {"id": session["user_id"], "next": session['tomorrow_name']}).fetchall()
    session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                     {"id": session["user_id"]}).fetchall()
    week = session['today_date_object']  + timedelta(days=7)
    # Getting this week's dues
    dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND deadline <= :w AND deadline >= :d ORDER BY deadline", {"id": session["user_id"], 'w': week, "d": session['today_date']}).fetchall()
    return render_template("index.html", subjects=today_subjects, tomorrow_subjects=tomorrow_subjects, dues=dues, quote=quote)


@app.route("/update_date", methods=["POST"])
@login_required
def update_date():
    """Updates the date"""

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


@app.route("/profile")
@login_required
def profile():
    """Display user's profile"""

    # Getting number of subjects
    subjects = db.execute("SELECT COUNT(DISTINCT subject) FROM subjects WHERE user_id = :id",
                          {"id": session["user_id"]}).fetchone()[0]
    subjects_type_count = db.execute("SELECT DISTINCT type, COUNT(*) FROM subjects WHERE user_id = :id GROUP BY type ORDER BY type",
                          {"id": session["user_id"]}).fetchall()
    if not subjects_type_count:
        labs = 0
        lectures = 0
        sections = 0
        total = 0
    else:
        labs = subjects_type_count[0]["count"]
        lectures = subjects_type_count[1]["count"]
        sections = subjects_type_count[2]["count"]
        total = labs + sections + lectures
    days = db.execute("SELECT DISTINCT day, COUNT(day) FROM subjects WHERE user_id = :id GROUP BY day",
                      {"id": session["user_id"]}).fetchall()
    days_off = 7 - int(len(days))
    # Sorting days
    d = {"Saturday": "", "Sunday": "", "Monday": "", "Tuesday": "", "Wednesday": "", "Thursday": "", "Friday": ""}
    for x in days:
        d[x["day"]] = x["count"]
    time = db.execute("SELECT date FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()[0]
    return render_template("profile.html", subjects=subjects, lectures=lectures, sections=sections, labs=labs, total=total,
                           days=d, days_off=days_off, date=time)


@app.route("/schedule")
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


@app.route("/subjects/<subject>")
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


@app.route("/subjects")
@login_required
def subjects():
    return redirect("/schedule")


@app.route("/delete/all_subjects", methods=["POST"])
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


@app.route("/delete/subject", methods=["POST"])
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

#For Server Worker
@app.route("/pwabuilder-sw.js")
#@login_required
def send_js():
    from flask import current_app
    return current_app.send_static_file('pwabuilder-sw.js')

    
@app.route("/delete/period", methods=["POST"])
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


@app.route("/type/<module_type>")
@login_required
def s_type(module_type):
    """Display all subjects of this type"""

    if not module_type:
        return apology("please enter a type")
    module_type = module_type.capitalize()
    if module_type != "Lecture" and module_type != "Section" and module_type != "Lab":
        return apology("invalid module type") 
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = :id AND type = :type ORDER BY start_time",
                          {"id": session["user_id"], "type": module_type}).fetchall()
    if not subjects:
        return apology("type not found")
    subjects_day = {"Saturday": [], "Sunday": [], "Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": []}
    days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    counter = 0
    for s in subjects:
        subjects_day[s["day"]].append(s)
        counter += 1
    return render_template("module.html", subjects=subjects_day, module_type=module_type, counter=counter)


@app.route("/place/<place>")
@login_required
def place(place):
    """Display subjects in this place"""

    if not place:
        return apology(message="place not found")
    place = place.replace("_", " ").title()
    q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND place = :place",
                   {"id": session["user_id"], "place": place}).fetchall()
    if not q:
        return apology("place not found")
        # Sorting days
    d = {"Saturday": [], "Sunday": [], "Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": []}
    for s in q:
        d[s["day"]].append(s)
    days = 0
    periods = 0
    for day in d.values():
        if len(day) > 0:
            days += 1
        periods += len(day)
    # days = set()
    # for s in q:
    #     days.add(s["day"])
    return render_template("place.html", place=place, subjects=d, days=days, periods=periods)


@app.route("/days/<day>")
@login_required
def day(day):
    """Display subjects on a specific day"""

    if not day:
        return apology(message="please enter a day")
    day = day.title()
    subjects = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :day ORDER BY start_time",
                          {"id": session["user_id"], "day": day}).fetchall()
    if not subjects:
        return apology("day not found")
    return render_template("day.html", subjects=subjects, day=day)


@app.route("/delete/day", methods=["POST"])
@login_required
def delete_day():
    """Delete an entire day's subjects"""

    day = request.form.get("day")
    if not day:
        return apology("please enter a day")
    q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :day", {"id": session["user_id"], "day": day}).fetchall()
    if not q:
        return apology("day not found")
    db.execute("DELETE FROM subjects WHERE user_id = :id AND day = :day", {"id": session["user_id"], "day": day})
    db.commit()
    flash("Day deleted!")
    return redirect("/")


@app.route("/add/period", methods=["POST"])
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

@app.route("/notes")
@login_required
def notes():
    notes = db.execute("SELECT * FROM notes WHERE user_id = :id ORDER BY date DESC", {"id": session["user_id"]}).fetchall()
    return render_template("notes.html", notes=notes)

@app.route("/add/note", methods=["POST"])
@login_required
def add_note():
    subject = request.form.get("subject")
    note = request.form.get("note")
    if not subject or not note:
        return apology("please fill the form")
    try:
        db.execute("INSERT INTO notes (user_id, subject, note, date) VALUES(:id, :s, :n, :d)", {"id": session["user_id"], "s": subject, "n": note, "d": session["today_date"]})
        db.commit()
    except:
        return apology("something went wrong")
    flash("Note added!")
    return redirect("/notes")

@app.route("/edit/note", methods=["GET", "POST"])
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

@app.route("/delete/note", methods=["POST"])
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

@app.route("/delete/notes", methods=["POST"])
@login_required
def delete_notes():
    db.execute("DELETE FROM notes WHERE user_id = :id", {"id": session["user_id"]})
    db.commit()
    flash("All notes deleted!")
    return redirect("/")
    
@app.route("/rename_subject", methods=["POST"])
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


@app.route("/edit/period", methods=["GET", "POST"])
@login_required
def edit_period():
    """Edit a subject"""
    if request.method == "POST":
        #recieved_token = request.form.get("token")
        #if not recieved_token or recieved_token != session["form_token"]:
            #return apology("fuck off cross-site forgeing piece of shit")
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
        #token = secrets.token_hex()
        #session["form_token"] = token
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
@app.route("/ece/section/<n>", methods=["GET", "POST"])
@login_required
def sfe(n):
    try:
        n = int(n)
    except:
        return apology("section number must be an integer")
    if request.method == "GET":
        return render_template("sfe.html", n=n)
    else:
        if n > 3:
            return apology("section not found")
        q = db.execute("SELECT * FROM subjects WHERE user_id = :id", {"id": 10+n}).fetchall()
        for s in q:
            db.execute("INSERT INTO subjects (user_id, subject, type, lecturer, place, start_time, end_time, day) VALUES(:id, :s, :t, :l, :p, :st, :e, :d)",
                       {"id": session["user_id"], "s": s["subject"], "t": s["type"], "l": s["lecturer"], "p": s["place"], "st": s["start_time"], "e": s["end_time"], "d": s["day"]})
        db.commit()
        flash(f"Section {n} schedule added successfully!")
        return redirect("/")


@app.route("/add/uni", methods=["POST"])
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


@app.route("/dues")
@login_required
def dues():
    """Display dues for user"""

    dues = db.execute("SELECT * FROM dues WHERE user_id = :id ORDER BY deadline", {"id": session["user_id"]}).fetchall()
    return render_template("dues.html", dues=dues)


@app.route("/add/due", methods=["POST"])
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


@app.route("/delete/due", methods=["POST"])
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


@app.route("/delete/dues", methods=["POST"])
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


@app.route("/search", methods=["GET"])
@login_required
def search():
    """Search for user input"""

    q = request.args.get("q").strip()
    if not q:
        return apology(message="please enter a name to search")
    try:
        results = db.execute("SELECT * FROM subjects WHERE user_id = :id AND (subject ILIKE :q OR type ILIKE :q OR lecturer ILIKE :q OR place ILIKE :q OR day ILIKE :q)",
                         {"id": session["user_id"], "q": "%" + q + "%"}).fetchall()
        dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND (subject ILIKE :q OR type ILIKE :q OR required ILIKE :q)",
                          {"id": session["user_id"], "q": "%" + q + "%"}).fetchall()
        notes = db.execute("SELECT * FROM notes WHERE user_id = :id AND (subject ILIKE :q OR note ILIKE :q)",{"id": session["user_id"], "q": "%" + q + "%"}).fetchall()
    except:
        return apology("something went wrong")
    return render_template("results.html", results=results, dues=dues, notes=notes, q=q)


@app.route("/settings/change_password", methods=["GET", "POST"])
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


@app.route("/settings/change_email", methods=["GET", "POST"])
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


@app.route("/settings/add_email", methods=["GET", "POST"])
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


@app.route("/feedback", methods=["GET", "POST"])
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


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": request.form.get("username")}).fetchone()

        # Ensure username exists and password is correct
        if not rows or not check_password_hash(rows["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows["id"]
        session["username"] = rows["username"]
        session["email"] = rows["email"]
        session["uni"] = rows["university"]

        # Setup the dates
        today_date = request.form.get('today_date')
        if not today_date:
            today_date = datetime.today()
        else:
            today_date = today_date.split("-")
            today_date = datetime(int(today_date[2]), int(today_date[0]), int(today_date[1]))
        session['today_date_object'] = today_date
        session['today_name'] = today_date.strftime("%A")
        session['tomorrow_name'] = week_days[(week_days.index(session['today_name']) + 1) % 7]
        session['today_date'] = today_date.strftime("%D")
        session['tomorrow_date'] = (today_date + timedelta(days=1)).strftime("%D")
        session['full_date'] = session['today_name'] + ", " + today_date.strftime("%b %d %Y")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        session.clear()
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        email = request.form.get("email")
        university = request.form.get("university")
        if not username or not password or not confirmation or password != confirmation:
            return apology("please fill the form correctly to register.")
    # Checking for username
    c = db.execute("SELECT username FROM users WHERE username ILIKE :username", {"username": username}).fetchall()
    if c:
        return apology("username already taken")

    # Specifications for password

    # password length
    if len(password) < 6:
        return apology(message="password must be longer than 6 characters")
    # password must contain numbers
    if password.isalpha():
        return apology(message="password must contain numbers")
    # password must contain letters
    if password.isdigit():
        return apology(message="password must contain letters")

    for c in username:
        if not c.isalpha() and not c.isdigit() and c != "_":
            return apology(message="Please enter a valid username.")
    if len(username) < 3:
        return apology("please enter a username with 3 or more characters")
    if len(username) > 50:
        return apology("username limit is 50 characters")
    hash_pw = generate_password_hash(password)
    try:
        if email:
            if len(email) > 70:
                return apology("email limit is 50 characters")
            q = db.execute("SELECT email FROM users WHERE email = :email", {"email": email}).fetchone()
            if q:
                return apology("this email already exists")
        if not email:
            email = None
        if university:
            if len(university) > 70:
                return apology("university limit is 70 characters")
            university = university.title()
        else:
            university = None
        db.execute("INSERT INTO users(username, hash, email, date, university) VALUES(:username, :hash_pw, :email, CURRENT_DATE, :university)",
                   {"username": username, "hash_pw": hash_pw, "email": email, "university": university})
        db.commit()
    except:
        return apology("something went wrong with the database.")
    if email:
        try:
            send_email(email, username, "Registeration for Student Helper", "Congratulations!\n You're now registered on Student Helper!")
        except Exception as x:
            print(x)
    rows = db.execute("SELECT id, username, email, university FROM users WHERE username = :username", {"username": username}).fetchone()
    session["user_id"] = rows["id"]
    session["username"] = rows["username"]
    session["email"] = rows["email"]
    session["uni"] = rows["university"]
    flash("You're now registered!")

    # Setup the dates
    today_date = request.form.get('today_date')
    if not today_date:
        return apology('please enable javascript your account has been registered')
    today_date = today_date.split("-")
    today_date = datetime(int(today_date[2]), int(today_date[0]), int(today_date[1]))
    session['today_date_object'] = today_date
    session['today_name'] = today_date.strftime("%A")
    session['tomorrow_name'] = week_days[(week_days.index(session['today_name']) + 1) % 7]
    session['today_date'] = today_date.strftime("%D")
    session['tomorrow_date'] = (today_date + timedelta(days=1)).strftime("%D")
    session['full_date'] = session['today_name'] + ", " + today_date.strftime("%b %d %Y")
    return redirect("/")


@app.route("/check", methods=["GET"])
def check():
    """Check if username or email is taken"""

    email = request.args.get("email")
    username = request.args.get("username")
    email = request.args.get("email")
    verify_username = db.execute("SELECT username FROM users WHERE username ILIKE :username", {"username": username}).fetchone()
    if email:
        verify_email = db.execute("SELECT email FROM users WHERE email = :email", {"email": email}).fetchone()
        if verify_email and verify_username:
            return jsonify("Username and email already taken.")
        if verify_username:
            return jsonify("Username already taken.")
        if verify_email:
            return jsonify("Email already taken.")
    if verify_username:
        return jsonify("Username already taken.")
    return jsonify(True)


@app.route("/about_me")
def about_me():
    return render_template("about_me.html")

    
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
