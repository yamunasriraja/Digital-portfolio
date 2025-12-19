import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- APP CONFIG ----------------
app = Flask(__name__)
app.secret_key = "super-secret-key"

DB_NAME = "study_portal.db"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB HELPERS ----------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'student'
    )
    """)

    # BATCHES (department based)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        department TEXT
    )
    """)

    # SUBJECTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        degree TEXT,
        year INTEGER,
        semester INTEGER,
        name TEXT
    )
    """)

    # MATERIALS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER,
        title TEXT,
        file_path TEXT
    )
    """)

    # DEFAULT ADMIN
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
            ("admin","admin@gmail.com",generate_password_hash("admin123"),"admin")
        )

    conn.commit()
    conn.close()

# ---------------- AUTH ----------------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_post():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (data["username"],))
    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user["password"], data["password"]):
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        return jsonify({"status":"success","redirect":url_for("main")})

    return jsonify({"status":"error"})

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username,email,password) VALUES (?,?,?)",
        (data["username"],data["email"],generate_password_hash(data["password"]))
    )
    conn.commit()
    conn.close()
    return jsonify({"status":"success","redirect":url_for("main")})

# ---------------- MAIN FLOW ----------------
@app.route("/main")
def main():
    return render_template("main.html")

@app.route("/department")
def department():
    return render_template("dept.html")

@app.route("/save-department", methods=["POST"])
def save_department():
    session["department"] = request.get_json()["department"]
    return "",204

@app.route("/home")
def home():
    return render_template("home.html", department=session.get("department"))

# ---------------- STUDY MATERIAL FLOW ----------------
@app.route("/study-material")
def study_material():
    dept = session.get("department")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM batches WHERE department=?", (dept,))
    batches = cur.fetchall()
    conn.close()
    return render_template("batch.html", batches=batches)

@app.route("/course/<int:batch_id>", methods=["GET","POST"])
def course(batch_id):
    if request.method == "POST":
        return redirect(url_for(
            "subjects",
            batch_id=batch_id,
            degree=request.form["degree"],
            year=request.form["year"],
            sem=request.form["semester"]
        ))
    return render_template("course.html", batch_id=batch_id)

@app.route("/subjects/<int:batch_id>/<degree>/<year>/<sem>")
def subjects(batch_id, degree, year, sem):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM subjects
        WHERE batch_id=? AND degree=? AND year=? AND semester=?
    """, (batch_id, degree, year, sem))
    subjects = cur.fetchall()
    conn.close()

    return render_template(
        "subject.html",
        subjects=subjects,
        batch_id=batch_id,
        degree=degree,
        year=year,
        sem=sem
    )

# -------- DELETE SUBJECT (ADMIN ONLY) --------
@app.route("/delete_subject/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
    conn.commit()
    conn.close()

    return redirect(request.referrer)

@app.route("/materials/<int:subject_id>")
def materials(subject_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subjects WHERE id=?", (subject_id,))
    subject = cur.fetchone()
    cur.execute("SELECT * FROM materials WHERE subject_id=?", (subject_id,))
    mats = cur.fetchall()
    conn.close()
    return render_template(
        "material.html",
        notes=mats,
        subject=subject,
        role=session.get("role")
    )


# -------- DELETE MATERIAL (ADMIN ONLY) --------
@app.route("/delete_material/<int:mat_id>", methods=["POST"])
def delete_material(mat_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    conn = get_db()
    cur = conn.cursor()

    # get file path
    cur.execute("SELECT file_path FROM materials WHERE id=?", (mat_id,))
    mat = cur.fetchone()

    if mat:
        file_path = mat["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)

        cur.execute("DELETE FROM materials WHERE id=?", (mat_id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer)


# ---------------- FILE DOWNLOAD ----------------
@app.route("/download/<int:mat_id>")
def download(mat_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM materials WHERE id=?", (mat_id,))
    mat = cur.fetchone()
    conn.close()
    if mat:
        return send_from_directory(
            UPLOAD_FOLDER,
            os.path.basename(mat["file_path"]),
            as_attachment=True
        )
    return "Not Found",404

#---------------------------
# -------- EDIT SUBJECT (ADMIN ONLY) --------
@app.route("/edit_subject/<int:subject_id>", methods=["POST"])
def edit_subject(subject_id):
    if session.get("role") != "admin":
        return "Unauthorized", 403

    data = request.get_json()
    new_name = data.get("name", "").strip()
    if not new_name:
        return "Invalid name", 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE subjects SET name=? WHERE id=?",
        (new_name, subject_id)
    )
    conn.commit()
    conn.close()

    return "Updated", 200

# ---------------- ADMIN ONLY ----------------
def admin_only():
    return session.get("role") == "admin"

@app.route("/add_batch", methods=["POST"])
def add_batch():
    if not admin_only(): return "Unauthorized",403
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO batches (name,department) VALUES (?,?)",
        (request.form["name"],request.form["department"])
    )
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route("/add_subject", methods=["POST"])
def add_subject():
    if not admin_only(): return "Unauthorized",403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO subjects (batch_id,degree,year,semester,name)
        VALUES (?,?,?,?,?)
    """,(
        request.form["batch_id"],
        request.form["degree"],
        request.form["year"],
        request.form["semester"],
        request.form["name"]
    ))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route("/upload/<int:subject_id>", methods=["POST"])
def upload_material(subject_id):
    if not admin_only(): return "Unauthorized",403
    file = request.files["file"]
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO materials (subject_id,title,file_path) VALUES (?,?,?)",
        (subject_id,request.form["title"],path)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("materials", subject_id=subject_id))

# ---------------- RUN ----------------
init_db()

if __name__ == "__main__":
    app.run(debug=True)