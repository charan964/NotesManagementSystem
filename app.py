from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# DATABASE CONNECTION
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
# REGISTER (NO OTP)
# ==========================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        confirm = request.form.get("confirm_password").strip()

        if password != confirm:
            flash("Passwords do not match!", "danger")
            return redirect("/register")

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # Check username duplicate
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            flash("Username already exists!", "danger")
            return redirect("/register")

        # Check email duplicate
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("Email already registered!", "danger")
            return redirect("/register")

        hashed = generate_password_hash(password)

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users(username, email, password, verified)
            VALUES(%s, %s, %s, 1)
        """, (username, email, hashed))

        conn.commit()
        cur.close()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect("/login")

    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
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
        title = request.form.get("title").strip()
        content = request.form.get("content").strip()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notes(title, content, user_id, created_at)
            VALUES(%s, %s, %s, NOW())
        """, (title, content, session["user_id"]))

        conn.commit()
        cur.close()
        conn.close()

        flash("Note added successfully!", "success")
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

    cur.close()
    conn.close()

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

    cur.close()
    conn.close()

    if not note:
        flash("Note not found!", "danger")
        return redirect("/viewall")

    return render_template("viewnote.html", note=note)


# ==========================================
# UPDATE NOTE
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

    if request.method == "POST":
        new_title = request.form.get("title").strip()
        new_content = request.form.get("content").strip()

        cur2 = conn.cursor()
        cur2.execute("""
            UPDATE notes SET title=%s, content=%s WHERE id=%s AND user_id=%s
        """, (new_title, new_content, id, session["user_id"]))

        conn.commit()
        cur2.close()
        conn.close()

        flash("Note updated!", "success")
        return redirect("/viewall")

    cur.close()
    conn.close()

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

    cur.close()
    conn.close()

    flash("Note deleted.", "info")
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
        query = request.form.get("query").strip()

        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT * FROM notes
            WHERE user_id=%s AND (title LIKE %s OR content LIKE %s)
        """, (session["user_id"], f"%{query}%", f"%{query}%"))

        results = cur.fetchall()

        cur.close()
        conn.close()

    return render_template("search.html", results=results)


# ==========================================
# ABOUT
# ==========================================
@app.route("/about")
def about():
    return render_template("about.html")


# ==========================================
# CONTACT
# ==========================================
@app.route("/contact")
def contact():
    return render_template("contact.html")


# ==========================================
# RUN APP
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)
