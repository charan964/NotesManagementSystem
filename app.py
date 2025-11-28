from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==========================================
# DB CONNECTION
# ==========================================
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="notes_db",
        buffered=True
    )

# ==========================================
# FLASK APP
# ==========================================
app = Flask(__name__)
app.secret_key = "MY_SUPER_SECRET_KEY"


# ==========================================
# HOME PAGE
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")


# ==========================================
# REGISTER (SEND OTP)
# ==========================================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # Check existing username
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            flash("Username already exists!", "danger")
            return redirect("/register")

        # Check existing email
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("Email already registered!", "danger")
            return redirect("/register")

        # Store temporarily
        session["temp_username"] = username
        session["temp_email"] = email

        # Generate OTP
        otp = random.randint(100000, 999999)
        session["reg_otp"] = otp

        # Send OTP
        sender = "charantejamamidi001@gmail.com"
        password = "bucm sdoy tpko ggyh"  # Gmail App Password

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = email
        msg["Subject"] = "Email Verification - Notes App"
        msg.attach(MIMEText(f"<h3>Your OTP: <b>{otp}</b></h3>", "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, email, msg.as_string())
            server.quit()

            flash("OTP sent to your email!", "success")
            return redirect("/verify_otp")

        except Exception as e:
            flash("Email error: " + str(e), "danger")

    return render_template("register.html")


# ==========================================
# VERIFY OTP
# ==========================================
@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":
        otp_entered = request.form["otp"]

        if str(session.get("reg_otp")) == otp_entered:
            return redirect("/set_password")

        flash("Incorrect OTP!", "danger")
        return redirect("/verify_otp")

    return render_template("verify.html")


# ==========================================
# SET PASSWORD
# ==========================================
@app.route("/set_password", methods=["GET", "POST"])
def set_password():

    if request.method == "POST":
        password = request.form["password"]
        hashed_pwd = generate_password_hash(password)

        uname = session.get("temp_username")
        email = session.get("temp_email")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users(username, email, password, verified)
            VALUES (%s, %s, %s, 1)
        """, (uname, email, hashed_pwd))

        conn.commit()
        cur.close()

        # clear temp
        session.pop("temp_username", None)
        session.pop("temp_email", None)
        session.pop("reg_otp", None)

        flash("Registration successful! Please login.", "success")
        return redirect("/login")

    return render_template("set_password.html")


# ==========================================
# LOGIN
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        pwd = request.form["password"]

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        if user and check_password_hash(user["password"], pwd):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")

        flash("Invalid username or password!", "danger")

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ==========================================
# DASHBOARD
# ==========================================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# ==========================================
# ADD NOTE
# ==========================================
@app.route("/addnote", methods=["GET", "POST"])
def addnote():

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notes(title, content, user_id, created_at)
            VALUES(%s, %s, %s, NOW())
        """, (title, content, session["user_id"]))

        conn.commit()
        cur.close()

        flash("Note added!", "success")
        return redirect("/viewall")

    return render_template("add_note.html")


# ==========================================
# VIEW ALL NOTES
# ==========================================
@app.route("/viewall")
def viewall():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC", (session["user_id"],))
    notes = cur.fetchall()

    return render_template("view_notes.html", notes=notes)


# ==========================================
# VIEW SINGLE NOTE
# ==========================================
@app.route("/viewnote/<int:id>")
def viewnote(id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s", (id, session["user_id"]))
    note = cur.fetchone()

    return render_template("viewnote.html", note=note)


# ==========================================
# UPDATE NOTE (FULLY FIXED)
# ==========================================
@app.route("/updatenote/<int:id>", methods=["GET", "POST"])
def updatenote(id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Fetch note
    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s", (id, session["user_id"]))
    note = cur.fetchone()

    if not note:
        flash("Note not found!", "danger")
        return redirect("/viewall")

    # Update note on POST
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        cur2 = conn.cursor()
        cur2.execute("UPDATE notes SET title=%s, content=%s WHERE id=%s",
                     (title, content, id))
        conn.commit()

        flash("Note updated successfully!", "success")
        return redirect("/viewall")

    # Render update page
    return render_template("update_note.html", note=note)



# ==========================================
# DELETE NOTE
# ==========================================
@app.route("/deletenote/<int:id>")
def deletenote(id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM notes WHERE id=%s AND user_id=%s", (id, session["user_id"]))
    conn.commit()

    flash("Note deleted!", "info")
    return redirect("/viewall")


# ==========================================
# SEARCH NOTES
# ==========================================
@app.route("/search", methods=["GET", "POST"])
def search():

    if "user_id" not in session:
        return redirect("/login")

    results = []

    if request.method == "POST":
        query = request.form["query"]

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT * FROM notes 
            WHERE user_id=%s AND (title LIKE %s OR content LIKE %s)
        """, (session["user_id"], f"%{query}%", f"%{query}%"))

        results = cur.fetchall()

    return render_template("search.html", results=results)


# ==========================================
# ABOUT PAGE
# ==========================================
@app.route("/about")
def about():
    return render_template("about.html")


# ==========================================
# CONTACT PAGE
# ==========================================
@app.route("/contact")
def contact():
    return render_template("contact.html")


# ==========================================
# FORGOT PASSWORD
# ==========================================
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":
        email = request.form["email"]

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if not user:
            flash("Email not found!", "danger")
            return redirect("/forgot_password")

        otp = random.randint(100000, 999999)

        session["reset_email"] = email
        session["reset_otp"] = otp

        sender = "charantejamamidi001@gmail.com"
        password = "bucm sdoy tpko ggyh"

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = email
        msg["Subject"] = "Password Reset OTP"
        msg.attach(MIMEText(f"<h3>Your OTP: <b>{otp}</b></h3>", "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, email, msg.as_string())
            server.quit()

            flash("OTP sent to your email!", "success")
            return redirect("/reset_verify")

        except Exception as e:
            flash(str(e), "danger")

    return render_template("forgot_password.html")


# ==========================================
# VERIFY RESET OTP
# ==========================================
@app.route("/reset_verify", methods=["GET", "POST"])
def reset_verify():

    if request.method == "POST":
        otp = request.form["otp"]

        if str(session.get("reset_otp")) == otp:
            return redirect("/reset_new_password")

        flash("Incorrect OTP!", "danger")
        return redirect("/reset_verify")

    return render_template("reset_verify.html")


# ==========================================
# RESET NEW PASSWORD
# ==========================================
@app.route("/reset_new_password", methods=["GET", "POST"])
def reset_new_password():

    if request.method == "POST":
        new_pwd = request.form["password"]
        hashed = generate_password_hash(new_pwd)

        email = session.get("reset_email")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))
        conn.commit()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)

        flash("Password reset successfully!", "success")
        return redirect("/login")

    return render_template("reset_new_password.html")


# ==========================================
# RUN APP
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)
