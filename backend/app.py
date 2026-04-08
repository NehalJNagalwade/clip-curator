# app.py — Clip Curator Backend (Final Version)
# This is the main server file. All routes live here.

import os
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from database import (
    init_db, save_video, save_bookmark,
    get_all_bookmarks, get_user_bookmarks,
    search_bookmarks, delete_bookmark,
    create_user, verify_user
)

# Load .env file (reads GROQ_API_KEY)
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize database when server starts
init_db()

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.route("/auth/register", methods=["POST"])
def register():
    """Create a new user account"""
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
    """Verify login credentials"""
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
    """
    Main route — takes YouTube URL, returns full analysis.
    Frontend sends:  {"url": "https://youtube.com/watch?v=..."}
    Returns:         full analysis with topics, summaries, timestamps
    """
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "Please provide a YouTube URL"}), 400

    youtube_url = data['url'].strip()
    video_id = data.get('video_id', '')

    try:
        from processor import process_video
        result = process_video(youtube_url)

        # Save video to database automatically
        save_video(
            result['video_id'],
            result['title'],
            result['duration']
        )

        return jsonify({"success": True, **result})

    except Exception as e:
        print(f"Processing error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ── BOOKMARK ROUTES ───────────────────────────────────────────────────────────

@app.route("/bookmarks", methods=["GET"])
def get_bookmarks():
    """Get all bookmarks for a user"""
    username = request.args.get('username', 'guest')
    try:
        bookmarks = get_user_bookmarks(username)
        return jsonify({"success": True, "bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/bookmarks", methods=["POST"])
def add_bookmark():
    """Save a new bookmark"""
    data = request.get_json()
    required = [
        'username', 'video_id', 'video_title',
        'topic_title', 'start_time', 'end_time',
        'start_formatted', 'end_formatted',
        'summary', 'youtube_link'
    ]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    try:
        bookmark_id = save_bookmark(
            data['username'],
            data['video_id'],
            data['video_title'],
            data['topic_title'],
            data['start_time'],
            data['end_time'],
            data['start_formatted'],
            data['end_formatted'],
            data['summary'],
            data['youtube_link']
        )
        return jsonify({"success": True, "bookmark_id": bookmark_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/bookmarks/search", methods=["GET"])
def search():
    """Search bookmarks by keyword"""
    query = request.args.get('q', '')
    username = request.args.get('username', 'guest')
    if not query:
        return jsonify({"error": "Provide search query ?q=..."}), 400
    try:
        results = search_bookmarks(username, query)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/bookmarks/<int:bookmark_id>", methods=["DELETE"])
def remove_bookmark(bookmark_id):
    """Delete a bookmark"""
    try:
        deleted = delete_bookmark(bookmark_id)
        if deleted:
            return jsonify({"success": True})
        return jsonify({"error": "Bookmark not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ── CLIP DOWNLOAD ROUTE ───────────────────────────────────────────────────────

@app.route("/clip", methods=["POST"])
def create_clip_route():
    """
    Creates and returns an MP4 clip.
    Only works for videos under 10 minutes.
    """
    data = request.get_json()
    required = ['video_id', 'start_time', 'end_time', 'duration']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing: {field}"}), 400

    # Block long videos
    if float(data['duration']) > 600:
        return jsonify({
            "error": "Clip download only available for videos under 10 minutes."
        }), 400

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

if __name__ == "__main__":
    app.run(debug=True, port=5000)