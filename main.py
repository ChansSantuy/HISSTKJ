from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from authentication import create_user, login
import json
import os
import base64
import datetime
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'secret_key'


QUIZ_DIR = Path("static/data/quezz")
USER_DIR = Path("static/data/data_user") 
ABSENSI_DIR = Path("static/data/absensi") 
ASSESSMENT_DIR = Path("static/data/assesment") 

# Membuat direktori jika belum ada
QUIZ_DIR.mkdir(parents=True, exist_ok=True)
USER_DIR.mkdir(parents=True, exist_ok=True)
ABSENSI_DIR.mkdir(parents=True, exist_ok=True)
ASSESSMENT_DIR.mkdir(parents=True, exist_ok=True)

# Simpan user online di memori (global)
listuseronline = set()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('auth'))
    
    username = session['username']
    user_dir = USER_DIR / username
    info_path = user_dir / "info.json"
    absensi_path = user_dir / "absenssion.json"
    achievement_path = user_dir / "achive.json" 

    # ==== INFO USER ====
    if not info_path.exists():
        return redirect(url_for('logout'))

    with open(info_path, "r", encoding="utf-8") as f:
        try:
            info = json.load(f)
        except json.JSONDecodeError:
            return redirect(url_for('logout'))

    # ==== ABSENSI USER ====
    absensi = []
    if absensi_path.exists():
        with open(absensi_path, "r", encoding="utf-8") as f:
            try:
                absensi = json.load(f)  
            except json.JSONDecodeError:
                absensi = []

    # ==== ACHIEVEMENTS USER ====
    achievements = {}
    if achievement_path.exists():
        with open(achievement_path, "r", encoding="utf-8") as f:
            try:
                achievements = json.load(f) 
            except json.JSONDecodeError:
                achievements = {"totalPoint": 0, "achievements": []}

    # === Simpan user ke list online ===
    listuseronline.add(username)

    # ==== RENDER SESUAI ROLE ====
    role = info.get("role", "siswa") 
    if role == "admin":
        all_users = [p for p in USER_DIR.iterdir() if p.is_dir()]
        user_list = []

        for u in all_users:
            if u.name == username:
                continue  # skip current user (admin sendiri)

            info_path = u / "info.json"
            if info_path.exists():
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        u_info = json.load(f)
                    if u_info.get("role") == "admin":
                        continue  # skip user admin lain
                except json.JSONDecodeError:
                    pass  

            user_list.append(u.name)

        # Dummy absensi awal
        users_data = [{"nama": u, "status": "-", "tanggal": "-"} for u in user_list]

        return render_template(
            "indexAdmin.html",
            user_list=user_list,
            users_data=json.dumps(users_data),
            online_users=list(listuseronline)
        )
    else:
        return render_template(
            "userTemplate/index.html", 
            user=info, 
            current_user=username, 
            absensi=absensi,
            achievements=achievements
        )


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        mode = request.form['mode']
        username = request.form['username']
        pin = request.form['pin']
        if mode == "Login":
            return login(username, pin)
        
    return render_template('auth.html')

@app.route('/create-user', methods=['POST'])
def create_user_route():
    return create_user()

@app.route('/logout')
def logout():
    username = session.get('username')
    if not username:
        return redirect(url_for('auth'))
    session.pop('username', None)
    return redirect(url_for('auth'))


@app.route("/assessments")
def get_assessments():
    base_path = os.path.join(app.root_path, "static","data", "assesment")
    assessments = []

    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)

        if os.path.isdir(folder_path):
            data_file = os.path.join(folder_path, "data.json")

            if os.path.exists(data_file):
                with open(data_file, "r", encoding="utf-8") as f:
                    try:
                        raw = json.load(f)

                        # hanya ambil field yang diperlukan untuk list
                        data = {
                            "id": folder,
                            "title": raw.get("title"),
                            "description": raw.get("description"),
                            "start_at": raw.get("start_at"),
                            "close_at": raw.get("close_at"),
                            "created_at": raw.get("created_at"),
                            "xp_total": raw.get("xp_total"),
                            "timming": raw.get("timming"),
                            "users": raw.get("users", [])
                        }

                        assessments.append(data)
                    except json.JSONDecodeError:
                        print(f"⚠️ File JSON tidak valid: {data_file}")

    return jsonify(assessments)

@app.route("/start_assessment/<assessment_id>", methods=["GET", "POST"])
def start_assessment(assessment_id):
    if request.method == "POST":
        data = request.get_json()
        username = data.get("username")

        # cek apakah user ada di USER_DIR
        user_dir = USER_DIR / username
        if not user_dir.exists():
            return jsonify({"status": "error", "message": "User not found"}), 404

        # cek apakah assessment ada
        assess_dir = ASSESSMENT_DIR / assessment_id
        data_path = assess_dir / "data.json"
        if not data_path.exists():
            return jsonify({"status": "error", "message": "Assessment not found"}), 404

        # load data.json
        with open(data_path, "r", encoding="utf-8") as f:
            data_json = json.load(f)

        # cek apakah username sudah pernah ikut assessment
        for user in data_json.get("users", []):
            if user.get("name") == username:
                # kalau sudah ada → redirect ke index
                return jsonify({"status": "redirect", "url": url_for("index")}), 200

        # kalau belum ada → boleh lanjut
        return jsonify({"status": "ok"}), 200

    # === METHOD GET ===
    if "username" not in session:
        return redirect(url_for("auth"))

    username = session["username"]

    # cek folder assessment
    assess_dir = ASSESSMENT_DIR / assessment_id
    if not assess_dir.exists():
        abort(404, description="Assessment not found")

    data_path = assess_dir / "data.json"
    question_path = assess_dir / "question.json"
    useronline_path = assess_dir / "useronline.json"

    if not data_path.exists() or not question_path.exists():
        abort(404, description="Assessment files missing")

    with open(data_path, "r", encoding="utf-8") as f:
        data_json = json.load(f)

    with open(question_path, "r", encoding="utf-8") as f:
        question_json = json.load(f)

    # === UPDATE useronline.json ===
    useronline = []
    if useronline_path.exists():
        with open(useronline_path, "r", encoding="utf-8") as f:
            try:
                useronline = json.load(f)
            except json.JSONDecodeError:
                useronline = []

    if username not in useronline:
        useronline.append(username)
        with open(useronline_path, "w", encoding="utf-8") as f:
            json.dump(useronline, f, indent=2, ensure_ascii=False)

    return render_template(
        "quizzindex.html",
        username=username,
        data=data_json,
        questions=question_json,
        assessment_id=assessment_id
    )


@app.route("/done_assessment", methods=["POST"])
def done_assessment():
    try:
        data = request.get_json(force=True)  # paksa baca JSON
        print("📩 Data diterima:", data)

        # pastikan data wajib ada
        required_fields = ["username", "assessment_id", "correct_answers", "wrong_answers", "exp_earned", "duration"]
        for f in required_fields:
            if f not in data:
                return jsonify({"error": f"Missing field: {f}"}), 400

        username = data["username"]
        assessment_id = data["assessment_id"]

        # jika file berbentuk langsung <assessment_id>.json
        assess_dir = ASSESSMENT_DIR / f"{assessment_id}"
        assessment_file = assess_dir / "data.json"

        if not assessment_file.exists():
            return jsonify({"error": f"Assessment '{assessment_id}' not found"}), 404

        # baca file assessment
        with open(assessment_file, "r", encoding="utf-8") as f:
            assessment_data = json.load(f)

        # data user baru
        new_user_result = {
            "name": username,
            "duration": data["duration"],
            "correct_answers": data["correct_answers"],
            "wrong_answers": data["wrong_answers"],
            "exp_earned": data["exp_earned"]
        }

        # append ke users
        assessment_data.setdefault("users", []).append(new_user_result)

        # simpan kembali assessment
        with open(assessment_file, "w", encoding="utf-8") as f:
            json.dump(assessment_data, f, indent=2, ensure_ascii=False)

        # ================== HAPUS USER DARI USERONLINE.JSON ==================
        useronline_path = assess_dir / "useronline.json"
        if useronline_path.exists():
            try:
                with open(useronline_path, "r", encoding="utf-8") as f:
                    useronline = json.load(f)
            except json.JSONDecodeError:
                useronline = []

            if username in useronline:
                useronline.remove(username)
                with open(useronline_path, "w", encoding="utf-8") as f:
                    json.dump(useronline, f, indent=2, ensure_ascii=False)

        # ================= UPDATE ACHIVE.JSON =================
        user_dir = USER_DIR / username
        user_dir.mkdir(parents=True, exist_ok=True)
        achive_path = user_dir / "achive.json"

        achive_data = {"totalPoint": 0, "achievements": []}
        if achive_path.exists():
            try:
                with open(achive_path, "r", encoding="utf-8") as f:
                    achive_data = json.load(f)
            except json.JSONDecodeError:
                achive_data = {"totalPoint": 0, "achievements": []}

        # tambah poin sesuai exp_earned
        exp = int(data.get("exp_earned", 0))
        achive_data["totalPoint"] = achive_data.get("totalPoint", 0) + exp
        
        if exp > 50:
            achive_data.setdefault("achievements", []).append({
                "type": "Asessment",
                "title": "Big Poin Asessment",
                "id": assessment_id,
                "desc": "mendapat point lebih besar dari 50",
                "point": exp,
                "timestamp": datetime.datetime.now().isoformat()
            })

        # simpan kembali achive.json
        with open(achive_path, "w", encoding="utf-8") as f:
            json.dump(achive_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "message": "Result saved successfully",
            "user": new_user_result,
            "totalPoint": achive_data["totalPoint"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/finalize_absensi", methods=["POST"])
def finalize_absensi():
    try:
        data = request.get_json()  # ini array dari FE
        if not data:
            return jsonify({"status": "error", "message": "Data kosong"}), 400

        for entry in data:
            username = entry.get("username")
            if not username:
                continue  # skip kalau gak ada username

            # Path user
            user_dir = USER_DIR / username
            user_dir.mkdir(parents=True, exist_ok=True)
            absensi_path = user_dir / "absenssion.json"
            achive_path = user_dir / "achive.json"

            # ====== ABSENSI ======
            absensi_data = []
            if absensi_path.exists():
                try:
                    with open(absensi_path, "r") as f:
                        absensi_data = json.load(f)
                except json.JSONDecodeError:
                    absensi_data = []

            # Tambahkan entry baru
# Tambahkan entry baru
            new_entry = {
              "tanggal": entry.get("tanggal"),
              "status": entry.get("status"),
              "alasan": entry.get("alasan"),
              "pembahasan": entry.get("pembahasan"),
              }
            absensi_data.append(new_entry)

            absensi_data.sort(key=lambda x: x.get("tanggal", ""), reverse=True)

            with open(absensi_path, "w", encoding="utf-8") as f:
                json.dump(absensi_data, f, indent=2, ensure_ascii=False)

            # ====== UPDATE ACHIVEMENT POINT ======
            achive_data = {"totalPoint": 0, "achievements": []}
            if achive_path.exists():
                try:
                    with open(achive_path, "r") as f:
                        achive_data = json.load(f)
                except json.JSONDecodeError:
                    achive_data = {"totalPoint": 0, "achievements": []}

            status = entry.get("status")
            if status == "Hadir":
                achive_data["totalPoint"] = achive_data.get("totalPoint", 0) + 10
            elif status == "Alpa":
                achive_data["totalPoint"] = achive_data.get("totalPoint", 0) - 20

            # Minimal jangan sampai minus
            if achive_data["totalPoint"] < 0:
                achive_data["totalPoint"] = 0

            # Simpan kembali achive.json
            with open(achive_path, "w", encoding="utf-8") as f:
                json.dump(achive_data, f, indent=2, ensure_ascii=False)

        return jsonify({"status": "success", "message": "Absensi & poin tersimpan"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/leaderboard_list", methods=["GET"])
def leaderboard_list():
    try:
        leaderboard = []

        for user_folder in USER_DIR.iterdir():
            if not user_folder.is_dir():
                continue

            # skip user tertentu
            if user_folder.name == "Chann_santuy":
                continue

            info_path = user_folder / "info.json"
            achive_path = user_folder / "achive.json"

            if not info_path.exists() or not achive_path.exists():
                continue

            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                with open(achive_path, "r", encoding="utf-8") as f:
                    achive = json.load(f)
            except json.JSONDecodeError:
                continue

            leaderboard.append({
                "name": info.get("nama", "Unknown"),
                "username": user_folder.name,  # ambil dari nama folder user
                "totalPoint": achive.get("totalPoint", 0)
            })

        # urutkan berdasarkan poin, descending
        leaderboard.sort(key=lambda x: x["totalPoint"], reverse=True)

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==== START ====
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
