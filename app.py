from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ===============================
# FLASK CONFIG
# ===============================
app = Flask(__name__)
app.secret_key = "MYSECRETKEY123"


# ===============================
# MYSQL CONFIG (LOCAL)
# ===============================
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "root"
app.config["MYSQL_DB"] = "notes_db"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


# ===============================
# HOME PAGE
# ===============================
@app.route("/")
def index():
    return render_template("index.html")


# ===============================
# REGISTER
# ===============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        pwd = request.form["password"]

        cur = mysql.connection.cursor()

        # Check if username exists
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            flash("Username already exists. Try another.", "danger")
            cur.close()
            return redirect("/register")

        # Check if email exists
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("Email already registered. Use another email.", "danger")
            cur.close()
            return redirect("/register")

        # Store user
        hashed_pwd = generate_password_hash(pwd)

        cur.execute(
            "INSERT INTO users(username, email, password) VALUES(%s, %s, %s)",
            (username, email, hashed_pwd),
        )
        mysql.connection.commit()
        cur.close()

        flash("Account created successfully! Please login.", "success")
        return redirect("/login")

    return render_template("register.html")


# ===============================
# LOGIN
# ===============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        pwd = request.form["password"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user["password"], pwd):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ===============================
# DASHBOARD
# ===============================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# ===============================
# ADD NOTE
# ===============================
@app.route("/addnote", methods=["GET", "POST"])
def addnote():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO notes(title, content, user_id, created_at) VALUES(%s, %s, %s, NOW())",
            (title, content, session["user_id"]),
        )
        mysql.connection.commit()
        cur.close()

        flash("Note added successfully!", "success")
        return redirect("/viewall")

    return render_template("add_note.html")


# ===============================
# VIEW ALL NOTES
# ===============================
@app.route("/viewall")
def viewall():
    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC",
        (session["user_id"],),
    )
    notes = cur.fetchall()
    cur.close()

    return render_template("view_notes.html", notes=notes)


# ===============================
# VIEW ONE NOTE
# ===============================
@app.route("/viewnote/<int:id>")
def viewnote(id):
    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM notes WHERE id=%s AND user_id=%s",
        (id, session["user_id"]),
    )
    note = cur.fetchone()
    cur.close()

    return render_template("viewnote.html", note=note)


# ===============================
# UPDATE NOTE
# ===============================
@app.route("/updatenote/<int:id>", methods=["GET", "POST"])
def updatenote(id):
    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT * FROM notes WHERE id=%s AND user_id=%s",
        (id, session["user_id"]),
    )
    note = cur.fetchone()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        cur.execute(
            "UPDATE notes SET title=%s, content=%s WHERE id=%s",
            (title, content, id),
        )
        mysql.connection.commit()
        cur.close()

        flash("Note updated successfully!", "success")
        return redirect("/viewall")

    return render_template("update_note.html", note=note)


# ===============================
# DELETE NOTE
# ===============================
@app.route("/deletenote/<int:id>")
def deletenote(id):
    if "user_id" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()
    cur.execute(
        "DELETE FROM notes WHERE id=%s AND user_id=%s",
        (id, session["user_id"]),
    )
    mysql.connection.commit()
    cur.close()

    flash("Note deleted!", "info")
    return redirect("/viewall")


# ===============================
# SEARCH NOTES
# ===============================
@app.route("/search", methods=["GET", "POST"])
def search():
    if "user_id" not in session:
        return redirect("/login")

    results = []

    if request.method == "POST":
        query = request.form.get("query", "")

        cur = mysql.connection.cursor()
        cur.execute(
            """
            SELECT * FROM notes
            WHERE user_id=%s AND (title LIKE %s OR content LIKE %s)
            """,
            (session["user_id"], f"%{query}%", f"%{query}%"),
        )
        results = cur.fetchall()
        cur.close()

    return render_template("search.html", results=results)


# ===============================
# SEND RESET PASSWORD EMAIL
# ===============================
@app.route("/resetpassword", methods=["GET", "POST"])
def resetpassword():
    if request.method == "POST":
        email = request.form["email"]

        sender = "charantejamamidi001@gmail.com"
        password = "bucm sdoy tpko ggyh"  # Your Gmail App Password
        reset_link = "http://127.0.0.1:5000/newpassword"

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = email
        msg["Subject"] = "Reset Your Password"

        msg.attach(
            MIMEText(
                f"<h3>Password Reset</h3><p>Click the link below:</p><a href='{reset_link}'>Reset Password</a>",
                "html",
            )
        )

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, email, msg.as_string())
            server.quit()

            flash("Reset link sent to your email!", "success")

        except Exception as e:
            flash("Email sending failed: " + str(e), "danger")

    return render_template("reset_password.html")


# ===============================
# UPDATE PASSWORD
# ===============================
@app.route("/newpassword", methods=["GET", "POST"])
def newpassword():
    if request.method == "POST":
        email = request.form["email"]
        pwd = request.form["password"]

        hashed_pwd = generate_password_hash(pwd)

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (hashed_pwd, email),
        )
        mysql.connection.commit()
        cur.close()

        flash("Password updated successfully!", "success")
        return redirect("/login")

    return render_template("newpassword.html")


# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
