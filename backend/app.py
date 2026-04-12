# app.py — Clip Curator Backend (Complete Final Version)

import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from database import (
    init_db, save_video, save_bookmark,
    get_user_bookmarks, search_bookmarks,
    delete_bookmark, create_user, verify_user
)

load_dotenv()

app = Flask(__name__)
CORS(app)
init_db()

REPORTS_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'reports')
os.makedirs(REPORTS_FOLDER, exist_ok=True)

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password required"}), 400
    username = data['username'].strip().lower()
    password = data['password'].strip()
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    success = create_user(username, password)
    if success:
        return jsonify({"success": True, "message": "Account created!"})
    else:
        return jsonify({"error": "Username already exists"}), 409

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password required"}), 400
    username = data['username'].strip().lower()
    password = data['password'].strip()
    if verify_user(username, password):
        return jsonify({"success": True, "username": username})
    else:
        return jsonify({"error": "Incorrect username or password"}), 401

# ── MAIN PROCESSING ROUTE ─────────────────────────────────────────────────────

@app.route("/process", methods=["POST"])
def process():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Please provide a YouTube URL"}), 400
    youtube_url = data['url'].strip()
    try:
        from processor import process_video
        result = process_video(youtube_url)
        save_video(result['video_id'], result['title'], result['duration'])
        return jsonify({"success": True, **result})
    except Exception as e:
        print(f"Processing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ── BOOKMARK ROUTES ───────────────────────────────────────────────────────────

@app.route("/bookmarks", methods=["GET"])
def get_bookmarks():
    username = request.args.get('username', 'guest')
    try:
        bookmarks = get_user_bookmarks(username)
        return jsonify({"success": True, "bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/bookmarks", methods=["POST"])
def add_bookmark():
    data = request.get_json()
    required = [
        'username', 'video_id', 'video_title', 'topic_title',
        'start_time', 'end_time', 'start_formatted', 'end_formatted',
        'summary', 'youtube_link'
    ]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    try:
        bookmark_id = save_bookmark(
            data['username'], data['video_id'], data['video_title'],
            data['topic_title'], data['start_time'], data['end_time'],
            data['start_formatted'], data['end_formatted'],
            data['summary'], data['youtube_link']
        )
        return jsonify({"success": True, "bookmark_id": bookmark_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/bookmarks/search", methods=["GET"])
def search():
    query = request.args.get('q', '')
    username = request.args.get('username', 'guest')
    if not query:
        return jsonify({"error": "Provide search query"}), 400
    try:
        results = search_bookmarks(username, query)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/bookmarks/<int:bookmark_id>", methods=["DELETE"])
def remove_bookmark(bookmark_id):
    try:
        deleted = delete_bookmark(bookmark_id)
        if deleted:
            return jsonify({"success": True})
        return jsonify({"error": "Bookmark not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── CLIP ROUTE ────────────────────────────────────────────────────────────────

@app.route("/clip", methods=["POST"])
def create_clip_route():
    data = request.get_json()
    required = ['video_id', 'start_time', 'end_time']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing: {field}"}), 400
    try:
        from clipper import create_clip
        clip_path = create_clip(
            data['video_id'],
            float(data['start_time']),
            float(data['end_time'])
        )
        return send_file(
            clip_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"clip_{data['video_id']}_{int(data['start_time'])}.mp4"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── REPORT ROUTE ──────────────────────────────────────────────────────────────

@app.route("/report", methods=["POST"])
def generate_report_route():
    """
    Generates a PDF report for a video.
    Frontend sends the full video analysis data.
    Returns the PDF file for download.
    """
    data = request.get_json()
    if not data or 'video_id' not in data:
        return jsonify({"error": "Video data required"}), 400

    try:
        from report_generator import generate_report
        video_id = data.get('video_id', 'unknown')
        output_path = os.path.join(REPORTS_FOLDER, f"report_{video_id}.pdf")
        generate_report(data, output_path)
        return send_file(
            output_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"ClipCurator_Report_{video_id}.pdf"
        )
    except Exception as e:
        print(f"Report error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)