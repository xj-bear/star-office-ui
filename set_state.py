#!/usr/bin/env python3
"""状态更新工具 - 支持多Agent并行追踪"""

import json
import os
import sys
from datetime import datetime

STATE_FILE = "/home/jason/.openclaw/workspace/star-office-ui/state.json"
IDLE_TIMEOUT = 30  # seconds: agent marked idle if no activity for this long

VALID_STATES = ["idle", "writing", "researching", "executing", "editing", "syncing", "error"]

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "state": "idle",
        "detail": "待命中...",
        "agent_id": "main",
        "active_agents": {},
        "progress": 0,
        "updated_at": datetime.now().isoformat()
    }

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def cleanup_idle_agents(state):
    """Remove agents that haven't been active for IDLE_TIMEOUT seconds."""
    now = datetime.now()
    active = state.get("active_agents", {})
    still_active = {}
    for aid, info in active.items():
        try:
            last = datetime.fromisoformat(info.get("updated_at", "2000-01-01"))
            if (now - last).total_seconds() < IDLE_TIMEOUT:
                still_active[aid] = info
        except:
            pass
    state["active_agents"] = still_active

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python set_state.py <state> [detail] [agent_id]")
        print(f"状态选项: {', '.join(VALID_STATES)}")
        sys.exit(1)
    
    state_name = sys.argv[1]
    detail = sys.argv[2] if len(sys.argv) > 2 else ""
    agent_id = sys.argv[3] if len(sys.argv) > 3 else "main"
    
    if state_name not in VALID_STATES:
        print(f"无效状态: {state_name}")
        sys.exit(1)
    
    state = load_state()
    
    # Ensure active_agents dict exists
    if "active_agents" not in state:
        state["active_agents"] = {}
    
    now = datetime.now().isoformat()
    
    if state_name != "idle":
        # Mark this agent as active
        state["active_agents"][agent_id] = {
            "state": state_name,
            "detail": detail,
            "updated_at": now
        }
    else:
        # Remove this agent from active list
        state["active_agents"].pop(agent_id, None)
    
    # Cleanup stale agents
    cleanup_idle_agents(state)
    
    # Set global state: if any agent is active, show that; otherwise idle
    if state["active_agents"]:
        # Pick the most recent active agent as the "global" state
        latest = max(state["active_agents"].items(), key=lambda x: x[1]["updated_at"])
        state["state"] = latest[1]["state"]
        state["detail"] = latest[1]["detail"]
        state["agent_id"] = latest[0]
    else:
        state["state"] = "idle"
        state["detail"] = "待命中（自动回到休息区）"
        state["agent_id"] = "main"
    
    state["updated_at"] = now
    save_state(state)
    
    active_list = list(state["active_agents"].keys())
    print(f"状态已更新: {state_name} - {detail} (agent: {agent_id}, active: {active_list})")
