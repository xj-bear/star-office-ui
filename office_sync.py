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

# Within agent/embedded logs
WORK_MESSAGES = [
    "embedded run start",
    "embedded run prompt start",
    "embedded run tool start",
    "embedded run tool end",
    "embedded run prompt end",
    "embedded run done",
]


import re

def extract_run_info(msg):
    """提取日志中的 runId, tool, 等信息"""
    run_id_match = re.search(r"runId=([^\s]+)", msg)
    tool_match = re.search(r"tool=([^\s]+)", msg)
    
    run_id = run_id_match.group(1) if run_id_match else ""
    tool = tool_match.group(1) if tool_match else ""
    
    return run_id, tool

def identify_agent_by_runid(run_id, raw_content):
    """
    通过 runId 提取真实 Agent
    示例: announce:v1:agent:coder:subagent:xxx -> coder
    默认返回: main
    """
    m = re.search(r"agent:([a-zA-Z0-9_-]+):", run_id)
    if m:
        agent = m.group(1)
        if agent in AGENT_IDS:
            return agent
            
    # Fallback to string matching as last resort
    lower = raw_content.lower()
    for agent_id in AGENT_IDS:
        if agent_id == "main": continue
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
    # Return the most recently modified log, as OpenClaw might still be writing to 
    # yesterday's log file if it hasn't restarted/rolled over.
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
                # Also check if the metadata 'name' indicates a session/agent
                name = str(meta.get("name", ""))
                is_agent_session = "agent" in name or name.startswith("session:agent:")
                
                if subsystem not in WORK_SUBSYSTEMS or not is_agent_session:
                    continue

                # ── Filter 2: Ignore bootstrap / passive logs ──
                msg = str(log_data.get("1", "")).lower()
                content_f0 = str(log_data.get("0", "")).lower()
                full_msg = msg + " " + content_f0

                # 这里就是真实的 AI 活动信号
                raw = str(log_data)
                
                run_id, tool_name = extract_run_info(full_msg)
                agent_id = identify_agent_by_runid(run_id, raw)

                # 客观状态映射机
                if "embedded run done" in full_msg:
                    print(f"IDLE  [{agent_id}]: {full_msg[:80]}")
                    set_state("idle", "任务完成，休息中...", agent_id)
                elif "embedded run tool start" in full_msg:
                    detail = f"正在使用工具: {tool_name}" if tool_name else "正在执行工具..."
                    state_val = "editing" if "edit" in tool_name or "write" in tool_name else "executing"
                    print(f"TOOL  [{agent_id}]: {detail}")
                    set_state(state_val, detail, agent_id)
                elif "embedded run prompt start" in full_msg:
                    print(f"THINK [{agent_id}]: 正在思考...")
                    set_state("researching", "正在思考分析...", agent_id)
                elif "embedded run start" in full_msg:
                    print(f"START [{agent_id}]: 接到新任务")
                    set_state("executing", "接到新任务，启动中...", agent_id)
                elif "embedded run tool end" in full_msg:
                    # 工具用完了还在思考，不要切到 idle！
                    print(f"WAIT  [{agent_id}]: 工具返回结果，继续推进")
                    set_state("executing", "整理返回结果...", agent_id)
                else:
                    # 保底工作状态
                    set_state("executing", "处理中...", agent_id)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
