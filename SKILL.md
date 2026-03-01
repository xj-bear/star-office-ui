---
name: star-office-ui
description: 为你的 AI 助手创建一个“像素办公室”可视化界面，手机可通过 Cloudflare Tunnel 公网访问！
metadata:
  {
    "openclaw": { "emoji": "🏢", "title": "Star 像素办公室", "color": "#ff6b35" }
  }
---

# Star Office UI Skill

## 效果预览
- 俯视像素办公室背景（可自己画/AI 生成/找素材）
- 像素小人代表助手：会根据 `state` 在不同区域移动，并带眨眼/气泡/打字机等动态
- 手机可通过 Cloudflare Tunnel quick tunnel 公网访问

## 前置条件
- 有一台能跑 Python 的服务器（或本地电脑）
- 一张  1200×900 的 PNG 办公室背景图（俯视像素风最佳）
- 有 Python 3 + Flask
- 有 Phaser CDN（前端直接用，无需安装）

## 快速开始

### 1. 准备目录
```bash
mkdir -p star-office-ui/backend star-office-ui/frontend
```

### 2. 准备背景图
把你的办公室背景图放到 `star-office-ui/frontend/office_bg.png`

### 3. 写后端 Flask app
创建 `star-office-ui/backend/app.py`：
```python
#!/usr/bin/env python3
from flask import Flask, jsonify, send_from_directory
from datetime import datetime
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
STATE_FILE = os.path.join(ROOT_DIR, "state.json")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")

DEFAULT_STATE = {
    "state": "idle",
    "detail": "等待任务中...",
    "progress": 0,
    "updated_at": datetime.now().isoformat()
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_STATE)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

if not os.path.exists(STATE_FILE):
    save_state(DEFAULT_STATE)

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/status")
def get_status():
    return jsonify(load_state())

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

if __name__ == "__main__":
    print("Listening on http://0.0.0.0:18791")
    app.run(host="0.0.0.0", port=18791, debug=False)
```

### 4. 写前端 Phaser UI
创建 `star-office-ui/frontend/index.html`（参考完整示例）：
- 用 `this.load.image('office_bg', '/static/office_bg.png')` 加载背景图
- 用 `this.add.image(400, 300, 'office_bg')` 放背景
- 状态区域映射：自己定义 workdesk/breakroom 的坐标
- 加动态效果：眨眼/气泡/打字机/小踱步等

### 5. 写状态更新脚本
创建 `star-office-ui/set_state.py`：
```python
#!/usr/bin/env python3
import json, os, sys
from datetime import datetime
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
VALID_STATES = ["idle", "writing", "researching", "executing", "syncing", "error"]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"state": "idle", "detail": "等待任务中...", "progress": 0, "updated_at": datetime.now().isoformat()}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python set_state.py <state> [detail]")
        sys.exit(1)
    s = sys.argv[1]
    if s not in VALID_STATES:
        print(f"有效状态: {', '.join(VALID_STATES)}")
        sys.exit(1)
    state = load_state()
    state["state"] = s
    state["detail"] = sys.argv[2] if len(sys.argv) > 2 else ""
    state["updated_at"] = datetime.now().isoformat()
    save_state(state)
    print(f"状态已更新: {s} - {state['detail']}")
```

### 6. 启动后端
```bash
cd star-office-ui/backend
pip install flask
python app.py
```

### 7. 开通 Cloudflare Tunnel（公网访问）
- 下载 cloudflared：https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/#1-download-and-install-cloudflared
- 启动 quick tunnel：
  ```bash
  cloudflared tunnel --url http://127.0.0.1:18791
  ```
- 它会给你一个 `https://xxx.trycloudflare.com` 地址，手机就能打开了

## 状态约定（可按需调整）
- `idle / syncing / error` → 休息区（breakroom）
- `writing / researching / executing` → 办公桌（workdesk）

## 安全注意事项
- quick tunnel URL 可能会变，不保证 uptime（适合 demo）
- 对外分享时：任何访问者都能看到 `state/detail`（detail 里不要写隐私）
- 如需更强隐私：给 `/status` 加 token / 只返回模糊状态 / 不写 detail

## 动态效果（好实现版，开箱即用）
- 同区域随机小踱步
- 偶尔眨眼
- 偶尔冒气泡（按状态随机短句）
- 状态栏打字机效果
- 走路轻微上下颠

## 完整示例仓库（可选）
可直接复制这个项目的完整文件：`/root/.openclaw/workspace/star-office-ui/`（包含完整的前端 + 后端 + 状态脚本）
