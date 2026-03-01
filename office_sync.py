#!/usr/bin/env python3
import subprocess
import time
import os

WORKSPACE_DIR = "/home/jason/.openclaw/workspace/star-office-ui"
SET_STATE_CMD = ["python3", os.path.join(WORKSPACE_DIR, "set_state.py"), "executing", "Assistant is thinking..."]
SET_EDIT_CMD = ["python3", os.path.join(WORKSPACE_DIR, "set_state.py"), "editing", "Assistant is editing code..."]

import json

# Keywords that indicate actual agent activity instead of background maintenance
ACTIVITY_KEYWORDS = [
    "agent", "prompt", "completion", "tool", "plugin", "reply", "message", "lane task", "execute", "thinking", "researching", "browser", "searching", "lane enqueue", "call"
]
EDIT_KEYWORDS = [
    "write_to_file", "replace_file_content", "multi_replace_file_content", "edit_file", "write file", "replaced by", "multi_replace"
]

def find_latest_log():
    log_dir = "/tmp/openclaw"
    if not os.path.exists(log_dir):
        return None
    files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith("openclaw-") and f.endswith(".log")]
    if not files:
        return None
    # Sort by modification time
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
            # Use tail -F to handle log rotation/creation
            process = subprocess.Popen(
                ["tail", "-F", "-n", "0", log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            for line in iter(process.stdout.readline, ""):
                line_to_check = line.lower()
                
                # Try JSON parse
                if line.strip().startswith('{'):
                    try:
                        log_data = json.loads(line)
                        # Concatenate fields 0, 1 and also check subsystem/logLevel
                        content = str(log_data.get("0", "")) + " " + str(log_data.get("1", ""))
                        # Also check meta info
                        meta = log_data.get("_meta", {})
                        subsystem = str(meta.get("name", ""))
                        line_to_check = (content + " " + subsystem).lower()
                    except:
                        pass

                if "cron" in line_to_check or "heartbeat" in line_to_check:
                    continue

                if any(kw in line_to_check for kw in EDIT_KEYWORDS):
                    print(f"Detected EDIT activity: {line_to_check[:100]}")
                    subprocess.run(SET_EDIT_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif any(kw in line_to_check for kw in ACTIVITY_KEYWORDS):
                    print(f"Detected ACTIVITY: {line_to_check[:100]}")
                    subprocess.run(SET_STATE_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
