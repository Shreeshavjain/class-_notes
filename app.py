import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, session
from werkzeug.utils import secure_filename
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

SUBJECTS_FILE = DATA_DIR / "subjects.json"

# default subjects file if missing
if not SUBJECTS_FILE.exists():
    with open(SUBJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"subjects": []}, f, indent=2)

def load_data():
    with open(SUBJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(SUBJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

ALLOWED_EXT = {"pdf", "ppt", "pptx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret")  # fallback only if env var missing

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "shreesha v jain")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "9880037254")

# ---------- Routes ----------

@app.route("/")
def index():
    data = load_data()
    subjects = data.get("subjects", [])
    return render_template("index.html", subjects=subjects, site_name="Class Notes")

@app.route("/subject/<subject_name>")
def subject_page(subject_name):
    safe_name = secure_filename(subject_name)
    folder = UPLOAD_DIR / safe_name
    files = []
    if folder.exists():
        for f in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if f.is_file():
                files.append({"name": f.name, "url": f"/uploads/{safe_name}/{f.name}", "ext": f.suffix.lower().lstrip(".")})
    is_admin = session.get('is_admin', False)
    return render_template("subject.html", subject=subject_name, files=files, site_name="Class Notes", is_admin=is_admin)

@app.route("/uploads/<subject>/<filename>")
def uploaded_file(subject, filename):
    return send_from_directory(UPLOAD_DIR / secure_filename(subject), filename, as_attachment=False)

@app.route("/download/<subject>/<filename>")
def download_file(subject, filename):
    return send_from_directory(UPLOAD_DIR / secure_filename(subject), filename, as_attachment=True)

# ---------- Admin: session-based login ----------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("admin_login.html", site_name="Class Notes Hub")

@app.route("/admin/logout")
def admin_logout():
    session.pop('is_admin', None)
    flash("Logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin")
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for("admin_login"))
    data = load_data()
    subjects = data.get("subjects", [])
    return render_template("admin_dashboard.html", subjects=subjects, site_name="Class Notes Hub")

@app.route("/admin/add_subject", methods=["GET", "POST"])
def add_subject():
    if not session.get('is_admin'):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        name = request.form.get("subject_name", "").strip()
        if not name:
            flash("Subject name cannot be empty", "warning")
            return redirect(url_for("add_subject"))
        data = load_data()
        if name in data["subjects"]:
            flash("Subject already exists", "warning")
            return redirect(url_for("add_subject"))
        data["subjects"].append(name)
        save_data(data)
        # create folder
        (UPLOAD_DIR / secure_filename(name)).mkdir(parents=True, exist_ok=True)
        flash(f"Subject '{name}' added", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("add_subject.html", site_name="Class Notes Hub")

@app.route("/admin/delete_subject/<subject>", methods=["POST"])
def delete_subject(subject):
    if not session.get('is_admin'):
        return redirect(url_for("admin_login"))
    data = load_data()
    if subject in data["subjects"]:
        data["subjects"].remove(subject)
        save_data(data)
        # optionally delete folder and files (we'll remove folder and its files)
        folder = UPLOAD_DIR / secure_filename(subject)
        if folder.exists() and folder.is_dir():
            for f in folder.iterdir():
                if f.is_file():
                    f.unlink()
            folder.rmdir()
        flash(f"Subject '{subject}' deleted", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/upload", methods=["GET", "POST"])
def admin_upload():
    if not session.get('is_admin'):
        return redirect(url_for("admin_login"))
    data = load_data()
    subjects = data.get("subjects", [])
    if request.method == "POST":
        subj = request.form.get("subject")
        file = request.files.get("file")
        if not subj or subj not in subjects:
            flash("Choose a valid subject", "warning")
            return redirect(url_for("admin_upload"))
        if not file or file.filename == "":
            flash("No file selected", "warning")
            return redirect(url_for("admin_upload"))
        if not allowed_file(file.filename):
            flash("File type not allowed. Use PDF, PPT, PPTX", "warning")
            return redirect(url_for("admin_upload"))
        filename = secure_filename(file.filename)
        target_folder = UPLOAD_DIR / secure_filename(subj)
        target_folder.mkdir(parents=True, exist_ok=True)
        save_path = target_folder / filename
        file.save(save_path)
        flash(f"Uploaded {filename} to {subj}", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_upload.html", subjects=subjects, site_name="Class Notes Hub")

@app.route("/admin/rename_subject/<old_name>", methods=["GET","POST"])
def rename_subject(old_name):
    if not session.get('is_admin'):
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        new_name = request.form.get("new_name", "").strip()
        if not new_name:
            flash("New name cannot be empty", "warning")
            return redirect(url_for("admin_dashboard"))
        data = load_data()
        if new_name in data["subjects"]:
            flash("A subject with that name already exists", "warning")
            return redirect(url_for("admin_dashboard"))
        # replace in list
        for i, s in enumerate(data["subjects"]):
            if s == old_name:
                data["subjects"][i] = new_name
                break
        save_data(data)
        # rename folder
        old_folder = UPLOAD_DIR / secure_filename(old_name)
        new_folder = UPLOAD_DIR / secure_filename(new_name)
        if old_folder.exists():
            old_folder.rename(new_folder)
        flash(f"Renamed '{old_name}' to '{new_name}'", "success")
        return redirect(url_for("admin_dashboard"))
    # GET -> show a simple form
    return render_template("admin_manage_subjects.html", edit_name=old_name, site_name="Class Notes Hub")

@app.route("/admin/delete_file/<subject>/<filename>", methods=["POST"])
def delete_file(subject, filename):
    if not session.get('is_admin'):
        abort(403)
    folder = UPLOAD_DIR / secure_filename(subject)
    file_path = folder / filename
    if file_path.exists() and file_path.is_file():
        file_path.unlink()
        flash(f"Deleted file '{filename}' from '{subject}'", "info")
    else:
        flash("File not found", "warning")
    return redirect(url_for("subject_page", subject_name=subject))

# ---------- run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False) 