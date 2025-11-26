from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import uuid

from config import get_connection   # <-- DB connection (mysql.connector)

app = Flask(__name__)
app.secret_key = "MY_SUPER_SECRET_KEY"   # change this


# ===============================
# HOME PAGE
# ===============================
@app.route('/')
def index():
    return render_template("index.html")


# ===============================
# REGISTER (WITH EMAIL VERIFICATION)
# ===============================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        pwd = request.form['password']

        if not username or not email or not pwd:
            flash("All fields are required.", "danger")
            return redirect('/register')

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # Check username exists
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            flash("Username already exists. Try another.", "danger")
            cur.close()
            conn.close()
            return redirect('/register')

        # Check email exists
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("Email already registered. Use a different email.", "danger")
            cur.close()
            conn.close()
            return redirect('/register')

        # Create user with verified = 0 and a token
        hashed_pwd = generate_password_hash(pwd)
        token = str(uuid.uuid4())

        cur.execute("""
            INSERT INTO users(username, email, password, verified, verification_token)
            VALUES(%s, %s, %s, %s, %s)
        """, (username, email, hashed_pwd, 0, token))
        conn.commit()
        cur.close()
        conn.close()

        # -----------------------------
        # SEND VERIFICATION EMAIL
        # -----------------------------
        sender = "charantejamamidi001@gmail.com"
        app_password = "bucm sdoy tpko ggyh"   # Gmail App Password

        # For local:
        verify_link = f"http://127.0.0.1:5000/verify/{token}"
        # For PythonAnywhere, later use:
        # verify_link = f"https://charan123.pythonanywhere.com/verify/{token}"

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = email
        msg['Subject'] = "Verify Your NotesApp Account"

        html = f"""
        <h2>NotesApp Email Verification</h2>
        <p>Hi <b>{username}</b>,</p>
        <p>Click the link below to verify your email and activate your account:</p>
        <p><a href="{verify_link}">{verify_link}</a></p>
        """

        msg.attach(MIMEText(html, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, email, msg.as_string())
            server.quit()

            flash("Verification email sent! Check your inbox.", "success")

        except Exception as e:
            flash(f"Error sending email: {e}", "danger")

        return redirect('/login')

    return render_template("register.html")


# ===============================
# VERIFY EMAIL
# ===============================
@app.route('/verify/<token>')
def verify(token):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE verification_token=%s", (token,))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        # Invalid or already used token
        return render_template("verify.html", status="invalid")

    # Mark user as verified and clear token
    cur.execute("""
        UPDATE users
        SET verified=1, verification_token=NULL
        WHERE id=%s
    """, (user['id'],))
    conn.commit()
    cur.close()
    conn.close()

    return render_template("verify.html", status="success", username=user['username'])


# ===============================
# LOGIN (BLOCK UNVERIFIED USERS)
# ===============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        pwd = request.form['password']

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            flash("Invalid username or password.", "danger")
            return redirect('/login')

        if not check_password_hash(user['password'], pwd):
            flash("Invalid username or password.", "danger")
            return redirect('/login')

        if not user['verified']:
            flash("Please verify your email before logging in.", "warning")
            return redirect('/login')

        # All good → create session
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect('/dashboard')

    return render_template("login.html")


# ===============================
# LOGOUT
# ===============================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ===============================
# DASHBOARD
# ===============================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("dashboard.html")


# ===============================
# ADD NOTE
# ===============================
@app.route('/addnote', methods=['GET', 'POST'])
def addnote():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            INSERT INTO notes(title, content, user_id, created_at)
            VALUES(%s, %s, %s, NOW())
        """, (title, content, session['user_id']))

        conn.commit()
        cur.close()
        conn.close()

        flash("Note added successfully!", "success")
        return redirect('/viewall')

    return render_template("add_note.html")


# ===============================
# VIEW ALL NOTES
# ===============================
@app.route('/viewall')
def viewall():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC", (session['user_id'],))
    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("view_notes.html", notes=notes)


# ===============================
# VIEW SINGLE NOTE
# ===============================
@app.route('/viewnote/<int:id>')
def viewnote(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s", (id, session['user_id']))
    note = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("viewnote.html", note=note)


# ===============================
# UPDATE NOTE
# ===============================
@app.route('/updatenote/<int:id>', methods=['GET', 'POST'])
def updatenote(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s", (id, session['user_id']))
    note = cur.fetchone()

    if not note:
        cur.close()
        conn.close()
        flash("Note not found.", "danger")
        return redirect('/viewall')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cur.execute("UPDATE notes SET title=%s, content=%s WHERE id=%s",
                    (title, content, id))
        conn.commit()
        cur.close()
        conn.close()

        flash("Note updated successfully!", "success")
        return redirect('/viewall')

    cur.close()
    conn.close()
    return render_template("update_note.html", note=note)


# ===============================
# DELETE NOTE
# ===============================
@app.route('/deletenote/<int:id>')
def deletenote(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("DELETE FROM notes WHERE id=%s AND user_id=%s", (id, session['user_id']))
    conn.commit()

    cur.close()
    conn.close()

    flash("Note deleted!", "info")
    return redirect('/viewall')


# ===============================
# SEARCH NOTES
# ===============================
@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'user_id' not in session:
        return redirect('/login')

    results = []

    if request.method == 'POST':
        query = request.form.get('query', '')

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT * FROM notes
            WHERE user_id=%s AND (title LIKE %s OR content LIKE %s)
        """, (session['user_id'], f"%{query}%", f"%{query}%"))

        results = cur.fetchall()

        cur.close()
        conn.close()

    return render_template("search.html", results=results)


# ===============================
# RESET PASSWORD (SEND EMAIL)
# ===============================
@app.route('/resetpassword', methods=['GET', 'POST'])
def resetpassword():
    if request.method == 'POST':
        email = request.form['email']

        # you can improve this later with token-based reset
        sender = "charantejamamidi001@gmail.com"
        app_password = "bucm sdoy tpko ggyh"
        reset_link = "http://127.0.0.1:5000/newpassword"

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = email
        msg['Subject'] = "Reset Your NotesApp Password"

        html = f"""
        <h3>Password Reset</h3>
        <p>Click the link below to set a new password:</p>
        <a href="{reset_link}">{reset_link}</a>
        """
        msg.attach(MIMEText(html, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, email, msg.as_string())
            server.quit()
            flash("Reset link sent to your email!", "success")
        except Exception as e:
            flash(str(e), "danger")

    return render_template("reset_password.html")


# ===============================
# NEW PASSWORD
# ===============================
@app.route('/newpassword', methods=['GET', 'POST'])
def newpassword():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']

        hashed = generate_password_hash(pwd)

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))
        conn.commit()

        cur.close()
        conn.close()

        flash("Password updated successfully!", "success")
        return redirect('/login')

    return render_template("newpassword.html")


# ===============================
# RUN APP
# ===============================
if __name__ == "__main__":
    app.run(debug=True)
