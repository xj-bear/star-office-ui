#!/usr/bin/env python3
"""
office_sync.py - OpenClaw Agent 实时行为监控引擎 (v3)

核心设计原则：
1. 同时监控所有日志文件，彻底解决日志轮转漂移
2. 三重 Agent 身份识别策略（runId → sessionId → diagnostic lane）
3. 严格状态机：只有 'embedded run done' 才触发 idle
"""
import subprocess
import time
import os
import json
import re
import select
import threading

WORKSPACE_DIR = "/home/jason/.openclaw/workspace/star-office-ui"
OPENCLAW_CONFIG = "/home/jason/.openclaw/openclaw.json"
OPENCLAW_AGENTS_DIR = os.path.expanduser("~/.openclaw/agents")
LOG_DIR = "/tmp/openclaw"

# ── Load agent list ──
AGENT_IDS = []
try:
    with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
        oc = json.load(f)
        AGENT_IDS = [a["id"] for a in oc.get("agents", {}).get("list", [])]
except Exception:
    AGENT_IDS = ["main"]

print(f"[INIT] 已注册 Agents: {AGENT_IDS}")

# ── Session → Agent 缓存 ──
SESSION_AGENT_CACHE = {}


def build_session_cache():
    """启动时扫描文件系统，构建 sessionId → agentId 映射缓存"""
    count = 0
    for agent in AGENT_IDS:
        sessions_dir = os.path.join(OPENCLAW_AGENTS_DIR, agent, "sessions")
        if not os.path.isdir(sessions_dir):
            continue
        for f in os.listdir(sessions_dir):
            # 匹配 xxxx.jsonl 或 xxxx.jsonl.deleted.xxx
            if ".jsonl" in f:
                sid = f.split(".")[0]
                SESSION_AGENT_CACHE[sid] = agent
                count += 1
    print(f"[INIT] 已缓存 {count} 个 session → agent 映射")


def refresh_session_cache_for(session_id):
    """动态刷新：遇到未知 sessionId 时重新扫描"""
    for agent in AGENT_IDS:
        session_path = os.path.join(
            OPENCLAW_AGENTS_DIR, agent, "sessions", f"{session_id}.jsonl"
        )
        if os.path.exists(session_path):
            SESSION_AGENT_CACHE[session_id] = agent
            print(f"[CACHE] 新发现: session {session_id[:12]}... → {agent}")
            return agent
    return None


# ── Agent 识别三重策略 ──
def identify_agent(run_id, session_id, raw_content):
    """
    三重策略识别 Agent：
    1. runId 字符串解析 (子代理通告格式)
    2. sessionId 文件系统反查
    3. 字符串匹配兜底
    """
    # 策略1: runId 解析 (如 announce:v1:agent:coder:subagent:xxx)
    if run_id:
        m = re.search(r"agent:([a-zA-Z0-9_-]+):", run_id)
        if m:
            agent = m.group(1)
            if agent in AGENT_IDS:
                return agent

    # 策略2: sessionId 文件系统反查 (精准绑定)
    if session_id:
        if session_id in SESSION_AGENT_CACHE:
            return SESSION_AGENT_CACHE[session_id]
        # 动态刷新
        found = refresh_session_cache_for(session_id)
        if found:
            return found

    # 策略3: 字符串匹配兜底
    lower = raw_content.lower()
    for agent_id in AGENT_IDS:
        if agent_id == "main":
            continue
        if agent_id.lower() in lower:
            return agent_id

    return "main"


def extract_fields(msg):
    """从日志消息中提取结构化字段"""
    fields = {}
    for match in re.finditer(r"(\w+)=([^\s]+)", msg):
        fields[match.group(1)] = match.group(2)
    return fields


def set_state(state, detail, agent_id="main"):
    """调用 set_state.py 更新状态"""
    cmd = [
        "python3", os.path.join(WORKSPACE_DIR, "set_state.py"),
        state, detail, agent_id
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ── 日志信号处理 ──
def process_log_line(line):
    """处理单行日志，提取信号并更新状态"""
    line = line.strip()
    if not line.startswith("{"):
        return

    try:
        log_data = json.loads(line)
    except Exception:
        return

    meta = log_data.get("_meta", {})
    name_raw = str(meta.get("name", ""))

    # 解析子系统
    subsystem = name_raw
    if name_raw.startswith("{"):
        try:
            subsystem = json.loads(name_raw).get("subsystem", name_raw)
        except Exception:
            pass

    # ── 信号源1: agent/embedded (核心工作信号) ──
    if subsystem == "agent/embedded":
        msg = str(log_data.get("1", "")).lower()
        content_f0 = str(log_data.get("0", "")).lower()
        full_msg = msg + " " + content_f0

        # 只处理 embedded run 相关信号
        if "embedded run" not in full_msg:
            return

        fields = extract_fields(msg)
        run_id = fields.get("runid", fields.get("runId", ""))
        session_id = fields.get("sessionid", fields.get("sessionId", ""))
        tool_name = fields.get("tool", "")

        raw = str(log_data)
        agent_id = identify_agent(run_id, session_id, raw)

        # ── 严格状态机 ──
        if "embedded run done" in full_msg:
            # ★ 唯一的 idle 触发点 ★
            duration = fields.get("durationms", fields.get("durationMs", "?"))
            print(f"DONE  [{agent_id}] 任务完成 (耗时 {duration}ms)")
            set_state("idle", "任务完成，休息中...", agent_id)

        elif "embedded run start" in full_msg and "tool" not in full_msg and "prompt" not in full_msg and "agent" not in full_msg:
            channel = fields.get("messagechannel", fields.get("messageChannel", "?"))
            print(f"START [{agent_id}] 新任务 (来源: {channel})")
            set_state("executing", f"接到新任务 ({channel})...", agent_id)

        elif "embedded run prompt start" in full_msg:
            print(f"THINK [{agent_id}] 正在思考...")
            set_state("researching", "正在思考分析...", agent_id)

        elif "embedded run tool start" in full_msg:
            detail = f"正在使用工具: {tool_name}" if tool_name else "正在执行工具..."
            state_val = "editing" if any(kw in tool_name for kw in ["edit", "write", "replace", "multi_replace"]) else "executing"
            print(f"TOOL  [{agent_id}] {detail}")
            set_state(state_val, detail, agent_id)

        elif "embedded run tool end" in full_msg:
            # 工具用完 → 还在继续工作，不切 idle！
            print(f"WAIT  [{agent_id}] 工具执行完毕，继续推进")
            set_state("executing", "整理返回结果...", agent_id)

        elif "embedded run prompt end" in full_msg:
            # 一轮思考完成 → 可能还有后续轮次，不切 idle！
            print(f"ROUND [{agent_id}] 一轮思考完成")
            set_state("executing", "思考完成，继续处理...", agent_id)

        elif "embedded run agent" in full_msg:
            # agent start/end 是内部循环，不影响外部状态
            pass

    # ── 信号源2: diagnostic (辅助 Agent 身份确认) ──
    elif subsystem == "diagnostic":
        msg = str(log_data.get("1", ""))

        # lane 事件携带 Agent 名称: lane=session:agent:<name>:main
        if "lane" in msg:
            lane_match = re.search(r"lane=session:agent:([a-zA-Z0-9_-]+):", msg)
            if lane_match:
                agent_name = lane_match.group(1)
                if agent_name in AGENT_IDS:
                    # ★ lane enqueue = 子代理开始工作 ★
                    if "lane enqueue" in msg:
                        print(f"LANE  [{agent_name}] 任务入队 → 前往工位")
                        set_state("executing", "接到任务，启动中...", agent_name)
                    # ★ lane task done = 子代理完成工作 ★
                    elif "lane task done" in msg:
                        duration_match = re.search(r"durationMs=(\d+)", msg)
                        dur = duration_match.group(1) if duration_match else "?"
                        print(f"LANE  [{agent_name}] Lane 完成 ({dur}ms) → 回到休息区")
                        set_state("idle", f"任务完成 (耗时 {dur}ms)", agent_name)


def watch_all_logs():
    """
    同时监控 /tmp/openclaw 下所有 .log 文件。
    使用 tail -F 跟踪所有文件，解决日志轮转问题。
    """
    while True:
        try:
            # 找到所有日志文件
            if not os.path.exists(LOG_DIR):
                print("[WATCH] 日志目录不存在，等待...")
                time.sleep(5)
                continue

            log_files = [
                os.path.join(LOG_DIR, f)
                for f in os.listdir(LOG_DIR)
                if f.startswith("openclaw-") and f.endswith(".log")
            ]

            if not log_files:
                print("[WATCH] 未找到日志文件，等待...")
                time.sleep(5)
                continue

            # 同时 tail 所有日志文件
            print(f"[WATCH] 开始监控 {len(log_files)} 个日志文件:")
            for f in sorted(log_files):
                print(f"  → {os.path.basename(f)}")

            process = subprocess.Popen(
                ["tail", "-F", "-n", "0"] + sorted(log_files),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            for line in iter(process.stdout.readline, ""):
                # tail -F 多文件模式会输出 "==> filename <==" 标记，跳过
                if line.startswith("==>") and "<==" in line:
                    continue
                process_log_line(line)

        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


def main():
    # 启动时构建 session 缓存
    build_session_cache()

    # 开始监控
    watch_all_logs()


if __name__ == "__main__":
    main()
