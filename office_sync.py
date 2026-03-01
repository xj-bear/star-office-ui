#!/usr/bin/env python3
"""
office_sync.py - 监听 OpenClaw 日志，精准识别真实的 Agent 工作状态

关键改进：只检测来自 'agent/embedded' 子系统的日志，
忽略 diagnostic/cron/plugins 等后台调度噪音。
"""
import subprocess
import time
import os
import json

WORKSPACE_DIR = "/home/jason/.openclaw/workspace/star-office-ui"
OPENCLAW_CONFIG = "/home/jason/.openclaw/openclaw.json"

# Load agent list at startup
AGENT_IDS = []
try:
    with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
        oc = json.load(f)
        AGENT_IDS = [a["id"] for a in oc.get("agents", {}).get("list", [])]
except Exception:
    AGENT_IDS = ["main"]

print(f"Known agents: {AGENT_IDS}")

# ── Only these subsystems represent real AI work ──────────────────────────
# 'agent/embedded' → LLM prompt/tool execution
# 'tools' write errors also real-ish activity
WORK_SUBSYSTEMS = {"agent/embedded"}

# Within agent/embedded logs, only these message patterns count
# (excludes 'workspace bootstrap' which happens passively)
WORK_MESSAGES = [
    "embedded run prompt start",
    "embedded run agent start",
    "embedded run tool start",
    "embedded run tool end",
    "embedded run agent end",
    "embedded run prompt end",
]

EDIT_MESSAGES = [
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "edit_file",
]


def detect_agent(lane_str):
    """Extract agent ID from lane string like 'session:agent:coder:subagent:xxx'."""
    if lane_str:
        parts = lane_str.split(":")
        # lane format: session:agent:<agent_id>:...
        if len(parts) >= 3 and parts[0] == "session" and parts[1] == "agent":
            agent = parts[2]
            if agent in AGENT_IDS:
                return agent
    # Fallback: check raw content for agent name keywords
    return "main"


def detect_agent_from_content(raw_content):
    """Fallback: try to find agent name in raw log content."""
    lower = raw_content.lower()
    for agent_id in AGENT_IDS:
        if agent_id == "main":
            continue
        if agent_id.lower() in lower:
            return agent_id
    return "main"


def set_state(state, detail, agent_id="main"):
    cmd = [
        "python3", os.path.join(WORKSPACE_DIR, "set_state.py"),
        state, detail, agent_id
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_latest_log():
    log_dir = "/tmp/openclaw"
    if not os.path.exists(log_dir):
        return None
    files = [os.path.join(log_dir, f) for f in os.listdir(log_dir)
             if f.startswith("openclaw-") and f.endswith(".log")]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def main():
    while True:
        try:
            log_file = find_latest_log()
            if not log_file:
                print("No log file found, waiting...")
                time.sleep(5)
                continue

            print(f"Watching {log_file} ...")
            process = subprocess.Popen(
                ["tail", "-F", "-n", "0", log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                if not line.startswith('{'):
                    continue

                try:
                    log_data = json.loads(line)
                except Exception:
                    continue

                meta = log_data.get("_meta", {})
                subsystem_raw = str(meta.get("name", ""))

                # Extract subsystem from JSON string like '{"subsystem":"agent/embedded"}'
                subsystem = subsystem_raw
                if subsystem_raw.startswith('{'):
                    try:
                        subsystem = json.loads(subsystem_raw).get("subsystem", subsystem_raw)
                    except Exception:
                        pass

                # ── Filter 1: Only care about real work subsystems ──
                if subsystem not in WORK_SUBSYSTEMS:
                    continue

                # ── Filter 2: Ignore bootstrap / passive logs ──
                msg = str(log_data.get("1", "")).lower()
                content_f0 = str(log_data.get("0", "")).lower()
                full_msg = msg + " " + content_f0

                # Detect if this is an edit operation
                is_edit = any(kw in full_msg for kw in EDIT_MESSAGES)
                is_work = any(pattern in full_msg for pattern in WORK_MESSAGES)

                if not is_edit and not is_work:
                    continue  # Skip bootstrap, workspace files, etc.

                # ── Detect which agent ──
                # Try lane field first
                lane = ""
                for v in log_data.values():
                    if isinstance(v, str) and v.startswith("session:agent:"):
                        lane = v
                        break
                    if isinstance(v, dict):
                        for vv in v.values():
                            if isinstance(vv, str) and vv.startswith("session:agent:"):
                                lane = vv
                                break

                agent_id = detect_agent(lane)
                if agent_id == "main":
                    # Try content matching as fallback
                    raw = str(log_data)
                    agent_id = detect_agent_from_content(raw)

                if is_edit:
                    print(f"EDIT  [{agent_id}]: {full_msg[:80]}")
                    set_state("editing", "正在修改代码...", agent_id)
                else:
                    print(f"WORK  [{agent_id}]: {full_msg[:80]}")
                    set_state("executing", "正在思考执行...", agent_id)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
