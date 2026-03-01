#!/usr/bin/env python3
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

# Keywords that indicate actual agent activity
ACTIVITY_KEYWORDS = [
    "agent", "prompt", "completion", "tool", "plugin", "reply", "message",
    "lane task", "execute", "thinking", "researching", "browser", "searching",
    "lane enqueue", "call"
]
EDIT_KEYWORDS = [
    "write_to_file", "replace_file_content", "multi_replace_file_content",
    "edit_file", "write file", "replaced by", "multi_replace"
]

def detect_agent(line_content):
    """Try to extract agent ID from log content by matching known agent names."""
    lower = line_content.lower()
    for agent_id in AGENT_IDS:
        if agent_id == "main":
            continue  # Skip 'main' as it matches too broadly
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
                
            print(f"Starting tail on {log_file}...")
            process = subprocess.Popen(
                ["tail", "-F", "-n", "0", log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            for line in iter(process.stdout.readline, ""):
                line_to_check = line.lower()
                raw_content = line
                
                # Try JSON parse
                if line.strip().startswith('{'):
                    try:
                        log_data = json.loads(line)
                        content = str(log_data.get("0", "")) + " " + str(log_data.get("1", ""))
                        meta = log_data.get("_meta", {})
                        subsystem = str(meta.get("name", ""))
                        parents = str(meta.get("parentNames", ""))
                        raw_content = content + " " + subsystem + " " + parents
                        line_to_check = raw_content.lower()
                    except:
                        pass

                if "cron" in line_to_check or "heartbeat" in line_to_check:
                    continue

                # Detect which agent this log belongs to
                agent_id = detect_agent(raw_content)

                if any(kw in line_to_check for kw in EDIT_KEYWORDS):
                    print(f"EDIT by [{agent_id}]: {line_to_check[:80]}")
                    set_state("editing", "Assistant is editing code...", agent_id)
                elif any(kw in line_to_check for kw in ACTIVITY_KEYWORDS):
                    print(f"ACTIVITY by [{agent_id}]: {line_to_check[:80]}")
                    set_state("executing", "Assistant is thinking...", agent_id)
                    
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
