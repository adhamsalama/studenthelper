from flask import flash, json, jsonify, redirect, render_template, request, session, Blueprint
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, send_email
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
from datetime import datetime, timedelta


auth = Blueprint('auth', __name__)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


week_days = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


@auth.route("/login", methods=["GET", "POST"])
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


@auth.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@auth.route("/register", methods=["GET", "POST"])
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


@auth.route("/check", methods=["GET"])
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

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    auth.errorhandler(code)(errorhandler)
    