class Student:
    def __init__(self,id, username, email, uni):
        self.id = id
        self.username = username
        self.email = email
        self.uni = uni

    def change_email(self, old, new):
        print(old, new)
        print(self.email)
        print(old == self.email)
        if old != self.email:
            return apology("wrong email")
        if db.execute("SELECT email FROM users WHERE email = :email", {"email": new}).fetchone():
            return apology("email already taken")
        try:
            db.execute("UPDATE users SET email = :new_email WHERE id = :id",
                       {"new_email": new, "id": session["user_id"]})
            db.commit()
            self.email = new
            session["email"] = new
        except Exception as x:
            print(x)
            return apology("something went wrong")
        return redirect("/")

    def __str__(self):
    return f"{self.id}\n{self.username}\n{self.email}\n{self.uni}"