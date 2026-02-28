#!/usr/bin/env python3
"""Star Office UI - Backend State Service"""

from flask import Flask, jsonify, send_from_directory, request
import werkzeug.utils
from datetime import datetime
import json
import os

# Paths
ROOT_DIR = "/home/jason/.openclaw/workspace/star-office-ui"
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
STATIC_DIR = os.path.join(ROOT_DIR, "frontend")  # Using frontend as static
STATE_FILE = os.path.join(ROOT_DIR, "state.json")
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")

# Default state
DEFAULT_STATE = {
    "state": "idle",
    "detail": "等待任务中...",
    "progress": 0,
    "updated_at": datetime.now().isoformat()
}


def load_state():
    """Load state from file.

    Includes a simple auto-idle mechanism:
    - If the last update is older than ttl_seconds (default 25s)
      and the state is a "working" state, we fall back to idle.

    This avoids the UI getting stuck at the desk when no new updates arrive.
    """
    state = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = None

    if not isinstance(state, dict):
        state = dict(DEFAULT_STATE)

    # Auto-idle
    try:
        ttl = int(state.get("ttl_seconds", 25))
        updated_at = state.get("updated_at")
        s = state.get("state", "idle")
        working_states = {"writing", "researching", "executing"}
        if updated_at and s in working_states:
            # tolerate both with/without timezone
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            # Use UTC for aware datetimes; local time for naive.
            if dt.tzinfo:
                from datetime import timezone
                age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
            else:
                age = (datetime.now() - dt).total_seconds()
            if age > ttl:
                state["state"] = "idle"
                state["detail"] = "待命中（自动回到休息区）"
                state["progress"] = 0
                state["updated_at"] = datetime.now().isoformat()
                # persist the auto-idle so every client sees it consistently
                try:
                    save_state(state)
                except Exception:
                    pass
    except Exception:
        pass

    return state


def save_state(state: dict):
    """Save state to file"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# Initialize state
if not os.path.exists(STATE_FILE):
    save_state(DEFAULT_STATE)


@app.route("/", methods=["GET"])
def index():
    """Serve the pixel office UI"""
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/admin", methods=["GET"])
def admin():
    """Serve the admin dashboard UI"""
    return send_from_directory(FRONTEND_DIR, "admin.html")

@app.route("/api/config", methods=["GET", "POST"])
def manage_config():
    """Get or update UI configuration"""
    if request.method == "GET":
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        return jsonify({})
    
    if request.method == "POST":
        new_config = request.json
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(new_config, f, ensure_ascii=False, indent=2)
        return jsonify({"status": "success", "message": "Config updated"})

@app.route("/api/upload/image", methods=["POST"])
def upload_image():
    """Handle image uploads for backgrounds and avatars"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file:
        filename = werkzeug.utils.secure_filename(file.filename)
        # Using a timestamp prefix to avoid caching issues on the frontend
        timestamp = int(datetime.now().timestamp())
        new_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(STATIC_DIR, new_filename)
        file.save(filepath)
        return jsonify({
            "status": "success", 
            "url": f"/static/{new_filename}",
            "filename": new_filename
        })


@app.route("/status", methods=["GET"])
def get_status():
    """Get current state"""
    state = load_state()
    return jsonify(state)


@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    print("=" * 50)
    print("Star Office UI - Backend State Service")
    print("=" * 50)
    print(f"State file: {STATE_FILE}")
    print("Listening on: http://0.0.0.0:18888")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=18888, debug=False)
