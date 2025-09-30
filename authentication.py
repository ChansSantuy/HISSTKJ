import datetime
from flask import request, redirect, url_for, session, jsonify
import os
import re
import json
from pathlib import Path

USER_DIR = Path("static/data/data_user")

# === Helper Validation ===
def validate_pin(pin):
    if len(pin) < 4 or len(pin) > 12:
        return False
    return True

def validate_username(username):
    pattern = r'[^a-zA-Z0-9_.-]'
    if re.search(pattern, username):
        return False
    return True

def check_user_folder(username):
    folder_path = USER_DIR / username
    return folder_path.is_dir()

# === LOGIN HANDLER ===
def login(username, pin):
    if 'username' in session:
        return redirect(url_for('index'))

    username = request.form['username']
    pin = request.form['pin']

    # === Kondisi khusus newuser ===
    if username == "newuser" and pin == "06660":
        return jsonify({"create_user": True})

    # === Normal login ===
    if not check_user_folder(username):
        return jsonify({'message': 'Username tidak ada. Silakan buat akun baru.', 'error': True})

    try:
        with open(USER_DIR / username / "pin.txt", 'r') as file:
            stored_pin = file.read().strip()
    except FileNotFoundError:
        return jsonify({'message': 'Data user rusak atau belum lengkap.', 'error': True})

    if pin != stored_pin:
        return jsonify({'message': 'PIN salah!', 'error': True})

    session['username'] = username
    return jsonify({'message': 'Login berhasil', 'error': False})

# === CREATE USER HANDLER ===
# === CREATE USER HANDLER ===
def create_user():
    nama = request.form.get("nama")
    kelas = request.form.get("kelas")
    kelasMana = request.form.get("kelasMana")
    jurusan = request.form.get("jurusan")
    username = request.form.get("username")
    password = request.form.get("password")
    avatar = request.files.get("avatar")

    # Default avatar link kalau ada
    avatar_default_link = request.form.get("avatar_default")

    # Validasi sederhana
    if not validate_username(username):
        return jsonify({"error": True, "message": "Username mengandung karakter tidak valid"})
    if check_user_folder(username):
        return jsonify({"error": True, "message": "Username sudah digunakan"})
    if not validate_pin(password):
        return jsonify({"error": True, "message": "Password/PIN harus 4–12 karakter"})

    # Buat folder user
    user_path = USER_DIR / username
    (user_path / "avatar").mkdir(parents=True, exist_ok=True)

    # Simpan pin
    with open(user_path / "pin.txt", "w") as f:
        f.write(password)

    # Simpan info.json
    info = {
        "nama": nama,
        "kelas": f"{kelas} {jurusan} {kelasMana}".strip(),
        "role": "siswa",
        "joinedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(user_path / "info.json", "w") as f:
        json.dump(info, f, indent=2)

    # === Simpan avatar ===
    if avatar:  # kalau upload file
        avatar.save(user_path / "avatar" / "avatar.jpg")
    elif avatar_default_link:  # kalau pilih default
        with open(user_path / "avatar" / "default.json", "w") as f:
            json.dump({"link": avatar_default_link}, f, indent=2)
# isi default untuk achive.json
    achive_default = {
        "totalPoint": 50,
        "achievements": []
    }

# Buat file default kosong atau dengan isi khusus
    for fname in ["achive.json", "quizz.json", "message.json"]:
       with open(user_path / fname, "w") as f:
        if fname == "achive.json":
            json.dump(achive_default, f, indent=2)
        else:
            json.dump({}, f, indent=2)

    for fname in ["quizz.json", "message.json", "absenssion.json"]:
      with open(user_path / fname, "w") as f:
        json.dump([], f, indent=2)

    # Simpan session login
    session['username'] = username

    return jsonify({"error": False, "message": "User berhasil dibuat"})

