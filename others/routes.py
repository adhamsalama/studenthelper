from flask import Flask, flash, json, jsonify, redirect, render_template, request, session, Blueprint
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from helpers import apology, login_required, connectdb, quote_of_the_day, rowproxy_to_dict
from cachetools import TTLCache
from datetime import datetime, timedelta



others = Blueprint('others', __name__, template_folder='templates')

# Set up database
db = connectdb()


cache = TTLCache(maxsize=10, ttl=86400)
cache["quote"] = quote_of_the_day()

@others.route("/")
@login_required
def index():
    """Display index page"""
    return render_template("index.html")


@others.route("/data/<date>")
@login_required
def data(date):
    """Return today's data as an HTML snippet"""
    try:
        quote = cache["quote"]
    except:
        cache["quote"] = quote_of_the_day()
        quote = cache["quote"]
    date = date.split("-")
    today_date = datetime(year=int(date[0]), month=int(date[1]), day=int(date[2]))
    today_subjects = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :day ORDER BY start_time",
                   {"id": session["user_id"], "day": today_date.strftime("%A")}).fetchall()
    tomorrow_subjects = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :tomorrow ORDER BY start_time",
                         {"id": session["user_id"], "tomorrow": (today_date + timedelta(days=1)).strftime("%A")}).fetchall()
    res = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                     {"id": session["user_id"]}).fetchall()
    #changed RowProxy result to python dict cuz sessions can't deal with RowProxy cuz they are unserializable json
    session["subjects"] = rowproxy_to_dict(res)
    week = today_date + timedelta(days=7)
    # Getting this week's dues
    dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND deadline <= :w AND deadline >= :d ORDER BY deadline", {"id": session["user_id"], 'w': week, "d": today_date.strftime("%Y-%m-%d")}).fetchall()
    #head =  render_template("head.html", subjects=today_subjects, tomorrow_subjects=tomorrow_subjects, dues=dues, quote=quote)
    main =  render_template("main.html", subjects=today_subjects, tomorrow_subjects=tomorrow_subjects, dues=dues, quote=quote)
    return jsonify({"main": main, "periods_count": len(today_subjects), "dues_count": len(dues)})
    #return jsonify({"today_subjects": rowproxy_to_dict(today_subjects), "tomorrow_subjects": rowproxy_to_dict(tomorrow_subjects), "dues": rowproxy_to_dict(dues)})

@others.route("/search", methods=["GET"])
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


@others.route("/profile")
@login_required
def profile():
    """Display user's profile"""

    # Getting number of subjects
    subjects = db.execute("SELECT COUNT(DISTINCT subject) FROM subjects WHERE user_id = :id",
                          {"id": session["user_id"]}).fetchone()[0]
    labs_count = db.execute("SELECT COUNT(*) FROM subjects WHERE user_id = :id AND type = 'Lab'",
                          {"id": session["user_id"]}).fetchone()[0]
    lectures_count = db.execute("SELECT COUNT(*) FROM subjects WHERE user_id = :id AND type = 'Lecture'",
                          {"id": session["user_id"]}).fetchone()[0]
    sections_count = db.execute("SELECT COUNT(*) FROM subjects WHERE user_id = :id AND type = 'Section'",
                          {"id": session["user_id"]}).fetchone()[0]
    days = db.execute("SELECT DISTINCT day, COUNT(day) FROM subjects WHERE user_id = :id GROUP BY day",
                      {"id": session["user_id"]}).fetchall()
    days_off = 7 - int(len(days))
    # Sorting days
    d = {"Saturday": "", "Sunday": "", "Monday": "", "Tuesday": "", "Wednesday": "", "Thursday": "", "Friday": ""}
    for x in days:
        d[x["day"]] = x["count"]
    time = db.execute("SELECT date FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()[0]
    return render_template("profile.html", subjects=subjects, lectures=lectures_count, sections=sections_count, labs=labs_count, total=labs_count+lectures_count+sections_count,
                           days=d, days_off=days_off, date=time)


#For Server Worker
@others.route("/pwabuilder-sw.js")
#@login_required
def send_js():
    from flask import current_app
    return current_app.send_static_file('pwabuilder-sw.js')


@others.route("/type/<module_type>")
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
    #days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    counter = 0
    for s in subjects:
        subjects_day[s["day"]].append(s)
        counter += 1
    return render_template("module.html", subjects=subjects_day, module_type=module_type, counter=counter)


@others.route("/place/<place>")
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


@others.route("/days/<day>")
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


@others.route("/delete/day", methods=["POST"])
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


@others.route("/about_me")
def about_me():
    return render_template("about_me.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    others.errorhandler(code)(errorhandler)
