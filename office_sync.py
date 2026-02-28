#!/usr/bin/env python3
import subprocess
import time
import os

WORKSPACE_DIR = "/home/jason/.openclaw/workspace/star-office-ui"
SET_STATE_CMD = ["python3", os.path.join(WORKSPACE_DIR, "set_state.py"), "executing", "Assistant is thinking..."]
SET_EDIT_CMD = ["python3", os.path.join(WORKSPACE_DIR, "set_state.py"), "editing", "Assistant is editing code..."]

# Keywords that indicate actual agent activity instead of background maintenance
ACTIVITY_KEYWORDS = [
    "agent", "prompt", "completion", "tool", "plugin", "reply", "message", "lane task", "execute"
]
EDIT_KEYWORDS = [
    "write_to_file", "replace_file_content", "multi_replace_file_content", "edit_file", "write file"
]

def main():
    while True:
        try:
            print("Starting log tail...")
            process = subprocess.Popen(
                ["openclaw", "logs", "--follow", "--limit", "0", "--plain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            for line in iter(process.stdout.readline, ""):
                line = line.lower()
                if "cron" in line or "heartbeat" in line:
                    continue

                if any(kw in line for kw in EDIT_KEYWORDS):
                    subprocess.run(SET_EDIT_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif any(kw in line for kw in ACTIVITY_KEYWORDS):
                    subprocess.run(SET_STATE_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
