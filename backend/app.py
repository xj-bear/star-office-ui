#!/usr/bin/env python3
"""Star Office UI - Backend State Service"""

from flask import Flask, jsonify, send_from_directory, request
import werkzeug.utils
from datetime import datetime
import json
import os
from PIL import Image

# Paths
ROOT_DIR = "/home/jason/.openclaw/workspace/star-office-ui"
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")  # Explicitly use static folder
STATE_FILE = os.path.join(ROOT_DIR, "state.json")
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

# Ensure static dir exists
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
# Manual route for /static files: prefer frontend/static/, fallback to frontend/ root (skin PNGs)
@app.route('/static/<path:filename>')
def custom_static(filename):
    static_path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(static_path):
        return send_from_directory(STATIC_DIR, filename)
    # Fallback: serve from frontend root (e.g. skin spritesheets like lobster.png)
    return send_from_directory(FRONTEND_DIR, filename)

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

    # Auto-idle: 只有在 active_agents 内的记录超时后才清除
    try:
        now_dt = datetime.now()
        active = state.get("active_agents", {})
        still_active = {}
        for aid, info in active.items():
            try:
                dt_str = info.get("updated_at", "2000-01-01").replace("Z", "+00:00")
                adt = datetime.fromisoformat(dt_str)
                if adt.tzinfo:
                    from datetime import timezone
                    age = (datetime.now(timezone.utc) - adt.astimezone(timezone.utc)).total_seconds()
                else:
                    age = (now_dt - adt).total_seconds()
                # 300秒（5 分钟）无任何新信号才从 active 列表移除
                if age <= 300:
                    still_active[aid] = info
                else:
                    print(f"[AUTO-IDLE] {aid} 超时未更新 ({age:.0f}s)，移出 active")
            except Exception:
                still_active[aid] = info  # 解析失败时保留

        # 只有当実际有变化时才更新 state（减少不必要的写入）
        if len(still_active) != len(active):
            state["active_agents"] = still_active
            active = still_active
            # 如果所有 agent 都清除，则设全局状态为 idle
            if not still_active:
                state["state"] = "idle"
                state["detail"] = "待命中"
                state["agent_id"] = "main"
                state["updated_at"] = now_dt.isoformat()
                try:
                    save_state(state)
                except Exception:
                    pass

        # 如果有 active agent，展示最新的那个
        if active:
            latest = max(active.items(), key=lambda x: x[1].get("updated_at", ""))
            state["state"] = latest[1].get("state", "executing")
            state["detail"] = latest[1].get("detail", "工作中...")
            state["agent_id"] = latest[0]
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


OPENCLAW_CONFIG = "/home/jason/.openclaw/openclaw.json"

def get_agents_list():
    try:
        with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
            oc_config = json.load(f)
            return [agent["id"] for agent in oc_config.get("agents", {}).get("list", [])]
    except Exception:
        return ["main"]

@app.route("/agents", methods=["GET"])
def api_get_agents():
    return jsonify(get_agents_list())

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

        # Resize image to fit within 1200×900 to prevent display scaling issues
        MAX_W, MAX_H = 1200, 900
        try:
            img = Image.open(file)
            img.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
            img.save(filepath)
        except Exception:
            # Fallback: save as-is if Pillow fails
            file.seek(0)
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
