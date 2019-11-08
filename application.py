from flask import Flask, flash, json, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, get_time, send_email
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

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


# Set up database
engine = create_engine(
    "postgres://grqmmiufuzsfza:a13a64718d2c4d935697f2e615b6f06433646079629bf670c3e285bc2d35d8a2@ec2-54-204-37-92.compute-1.amazonaws.com:5432/d6vhlm4n2rs2f4")
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    """Display index page"""

    import time
    day = time.strftime("%A")
    days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    # day = days.index(day)
    next_day = days[(days.index(day) + 1) % 7]
    q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :day ORDER BY start_time",
                   {"id": session["user_id"], "day": day}).fetchall()
    nxt_day = db.execute("SELECT * FROM subjects WHERE user_id = :id AND day = :next",
                         {"id": session["user_id"], "next": next_day}).fetchall()
    session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                     {"id": session["user_id"]}).fetchall()
    date = time.strftime("%D")
    dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND deadline = :d", {"id": session["user_id"], "d": date}).fetchall()
    return render_template("index.html", subjects=q, next=nxt_day, next_day=next_day, day=day, dues=dues)


@app.route("/profile")
@login_required
def profile():
    """Display user's profile"""

    # Getting number of subjects
    uni = db.execute("SELECT university FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()
    subjects = db.execute("SELECT COUNT(DISTINCT subject) FROM subjects WHERE user_id = :id",
                          {"id": session["user_id"]}).fetchone()[0]
    lectures = db.execute("SELECT COUNT(*) FROM subjects WHERE user_id = :id AND type = 'Lecture'",
                          {"id": session["user_id"]}).fetchone()[0]
    sections = db.execute("SELECT COUNT(*) FROM subjects WHERE user_id = :id AND type = 'Section'",
                          {"id": session["user_id"]}).fetchone()[0]
    labs = db.execute("SELECT COUNT(*) FROM subjects WHERE user_id = :id AND type = 'Lab'",
                      {"id": session["user_id"]}).fetchone()[0]
    days = db.execute("SELECT DISTINCT day, COUNT(day) FROM subjects WHERE user_id = :id GROUP BY day",
                      {"id": session["user_id"]}).fetchall()
    days_off = 7 - int(len(days))
    # Sorting days
    d = {"Saturday": "", "Sunday": "", "Monday": "", "Tuesday": "", "Wednesday": "", "Thursday": "", "Friday": ""}
    for x in days:
        d[x["day"]] = x["count"]
    time = db.execute("SELECT time FROM users WHERE id = :id", {"id": session["user_id"]}).fetchone()["time"]
    return render_template("profile.html", subjects=subjects, lectures=lectures, sections=sections, labs=labs, days=d, days_off=days_off, email=session["email"], time=time, uni=uni)


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
    else:
        lecturer = q[0]["lecturer"]
    dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND subject ILIKE :s",
                      {"id": session["user_id"], "s": subject}).fetchall()
    return render_template("subject.html", info=q, lecturer=lecturer, dues=dues)


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
        db.commit()
    except:
        return apology("something went wrong")
    flash("Subjects deleted!")
    return redirect("/")


@app.route("/delete/entire_subject", methods=["POST"])
@login_required
def delete_entire_subject():
    """Delete entire subject"""

    subject = request.form.get("subject")
    if not subject:
        return apology("subject doesn't exist")
    try:
        db.execute("DELETE FROM subjects WHERE user_id = :id AND subject = :s", {"id": session["user_id"], "s": subject})
        db.commit()
    except:
        return apology("somethign went wrong")
    flash("Subject deleted!")
    return redirect("/")


@app.route("/delete/subject", methods=["POST"])
@login_required
def delete_subject():
    """Delete one subject"""

    s = request.form.get("subject")
    t = request.form.get("type")
    l = request.form.get("lecturer")
    d = request.form.get("day")
    p = request.form.get("place")
    st = request.form.get("start")
    e = request.form.get("end")
    print(s, t, l, d, p, st, e)
    if not s or not t or not l or not d or not p or not st or not e:
        return apology("something unsual happened")
    q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND day = :d AND place = :p AND start_time = :st AND end_time = :e",
                   {"id": session["user_id"], "s": s, "t": t, "l": l, "d": d, "p": p, "st": st, "e": e}).fetchall()
    if not q:
        return apology(message="subject doesn't exist")

    db.execute("DELETE FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND day = :d AND place = :p AND start_time = :st AND end_time = :e",
               {"id": session["user_id"], "s": s, "t": t, "l": l, "d": d, "p": p, "st": st, "e": e})
    db.commit()
    flash(f"{t} deleted!")
    return redirect("/schedule")


@app.route("/type/<module_type>")
@login_required
def s_type(module_type):
    """Display all subjects of this type"""

    if not module_type:
        return apology("please enter a type")
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
    days = set()
    for s in q:
        days.add(s["day"])
    return render_template("place.html", place=place, subjects=q, days=days)


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


@app.route("/add/subject", methods=["GET", "POST"])
def setup():
    """Add subject"""

    if request.method == "GET":
        return render_template("setup.html")
    else:
        subject = request.form.get("subject")
        subject_type = request.form.get("type")
        lecturer = request.form.get("lecturer")
        place = request.form.get("place")
        start = request.form.get("start")
        end = request.form.get("end")
        day = request.form.get("day")
        if not subject or not type or not lecturer or not place or not start or not end or not day:
            return apology(message="please fill the form")
        # days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        # day = days.index(day)
        subject = subject.rstrip().title()
        subject_type = subject_type.capitalize()
        lecturer = lecturer.rstrip().title()
        place = place.rstrip().title()
        q = db.execute("SELECT * FROM subjects WHERE user_id = :id AND subject = :s AND type = :t AND lecturer = :l AND place = :p AND start_time = :s_t AND end_time = :e AND day = :d",
                       {"id": session["user_id"], "s": subject, "t": subject_type, "l": lecturer, "p": place, "s_t": start, "e": end, "d": day}).fetchall()
        if q:
            return apology(message=f"{subject_type} already exists")
        try:
            db.execute("INSERT INTO subjects (user_id, subject, type, lecturer, place, start_time, end_time, day) VALUES(:id, :subject, :type, :lecturer, :place, :start, :end, :day)",
                       {"id": session["user_id"], "subject": subject, "type": subject_type, "lecturer": lecturer, "place": place, "start": start, "end": end, "day": day})
            db.commit()
            session["subjects"] = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                             {"id": session["user_id"]}).fetchall()
        except:
            return apology("something went wrong with the database")
        flash("Subject added!")
        return redirect(f"/subjects/{subject}")


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
        if n > 2:
            return apology(message="section 3 not added yet")
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
    except:
        return apology("something went wrong")
    flash("University added!")
    return redirect("/profile")


@app.route("/dues")
@login_required
def dues():
    """Display dues for user"""

    dues = db.execute("SELECT * FROM dues WHERE user_id = :id ORDER BY deadline", {"id": session["user_id"]}).fetchall()
    subjects = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                                     {"id": session["user_id"]}).fetchall()
    return render_template("dues.html", dues=dues, subjects=subjects)


@app.route("/add/due", methods=["POST"])
@login_required
def add_due():
    """Add due"""

    subject = request.form.get("subject")
    s_type = request.form.get("type")
    required = request.form.get("required")
    deadline = request.form.get("deadline")
    if not subject or not s_type or not required or not deadline:
        return apology("something went wrong")
    subject = subject.title()
    subjects = db.execute("SELECT DISTINCT subject FROM subjects WHERE user_id = :id ORDER BY subject",
                          {"id": session["user_id"]}).fetchall()
    print(subject)
    print(subjects)
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
            except Exception as x:
                return apology("something went wrong with the database")
            flash("Due added successfully!")
            return redirect("/dues")
    else:
        return apology("subject doesn't exist")


@app.route("/delete/due", methods=["POST"])
@login_required
def delete_due():
    """Delete one due"""

    subject = request.form.get("subject")
    required = request.form.get("required")
    deadline = request.form.get("deadline")
    if not subject or not required or not deadline:
        return apology("something went wrong")
    q = db.execute("SELECT * FROM dues WHERE user_id = :id AND subject = :s AND required = :r AND deadline = :d",
                   {"id": session["user_id"], "s": subject, "r": required, "d": deadline}).fetchone()
    if not q:
        return apology("due doesn't exist")
    try:
        db.execute("DELETE FROM dues WHERE user_id = :id AND subject = :s AND required = :r AND deadline = :d",
                   {"id": session["user_id"], "s": subject, "r": required, "d": deadline})
        db.commit()
    except:
        return apology("something went wrong with the database")
    flash("Due deleted successfully!")
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

    q = request.args.get("q").rstrip()
    if not q:
        return apology(message="please enter a name to search")
    try:
        results = db.execute("SELECT * FROM subjects WHERE user_id = :id AND (subject ILIKE :q OR type ILIKE :q OR lecturer ILIKE :q OR place ILIKE :q OR day ILIKE :q)",
                         {"id": session["user_id"], "q": "%" + q + "%"}).fetchall()
        dues = db.execute("SELECT * FROM dues WHERE user_id = :id AND (subject ILIKE :q OR subject ILIKE :q OR type ILIKE :q OR required ILIKE :q)",
                          {"id": session["user_id"], "q": "%" + q + "%"}).fetchall()
    except:
        return apology("something went wrong")
    return render_template("results.html", results=results, dues=dues, q=q)


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
                send_email(new_email, session["username"], message)
                message="Success!\n Your email was successfully changed!"
            except Exception as x:
                print()
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
        db.execute("UPDATE users SET email = :new_email WHERE id = :id",
                   {"new_email": email, "id": session["user_id"]})
        db.commit()
        message="Success!\n Your email was successfully added to your account!"
        send_email(email, session["username"], message)
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
            return apology(message="please fill the form")
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
    c = db.execute("SELECT username FROM users WHERE username = :username", {"username": username}).fetchall()
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
    if len(username) < 1:
        return apology(message="please enter a username with more than 1 character.")
    hash_pw = generate_password_hash(password)
    time = get_time()
    try:
        if email:
            q = db.execute("SELECT email FROM users WHERE email = :email", {"email": email}).fetchone()
            if q:
                return apology("this email already exists")
        if not email:
            email = None
        if university:
            university = university.title()
        else:
            university = None
        db.execute("INSERT INTO users(username, hash, email, time, university) VALUES(:username, :hash_pw, :email, :time, :university)",
                   {"username": username, "hash_pw": hash_pw, "email": email, "time": time, "university": university})
        db.commit()
    except:
        return apology("something went wrong with the database.")
    try:
        message = "Congratulations!\n You're now registered on Student Helper!"
        send_email(email, username, message)
    except Exception as x:
        print(x)
    rows = db.execute("SELECT id, username, email FROM users WHERE username = :username", {"username": username}).fetchone()
    session["user_id"] = rows["id"]
    session["username"] = rows["username"]
    session["email"] = rows["email"]
    flash("You're now registered!")
    return redirect("/")


@app.route("/check", methods=["GET"])
def check():
    """Check if username or email is taken"""

    email = request.args.get("email")
    username = request.args.get("username")
    email = request.args.get("email")
    verify_username = db.execute("SELECT username FROM users WHERE username = :username", {"username": username}).fetchone()
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
