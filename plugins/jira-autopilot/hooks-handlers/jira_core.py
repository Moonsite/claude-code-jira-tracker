#!/usr/bin/env python3
"""jira-autopilot core module — all business logic for hooks and commands."""

import json
import os
import re
import sys
import time
import math
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── Constants ──────────────────────────────────────────────────────────────

CONFIG_NAME = "jira-autopilot.json"
LOCAL_CONFIG_NAME = "jira-autopilot.local.json"
GLOBAL_CONFIG_PATH = Path.home() / ".claude" / "jira-autopilot.global.json"
SESSION_NAME = "jira-session.json"
DEBUG_LOG_PATH = Path.home() / ".claude" / "jira-autopilot-debug.log"
MAX_LOG_SIZE = 1_000_000  # 1MB

READ_ONLY_TOOLS = frozenset([
    "Read", "Glob", "Grep", "LS", "WebSearch", "WebFetch",
    "TodoRead", "NotebookRead", "AskUserQuestion",
])

BUG_SIGNALS = [
    "fix", "bug", "broken", "crash", "error", "fail",
    "regression", "not working", "issue with",
]
TASK_SIGNALS = [
    "add", "create", "implement", "build", "setup",
    "configure", "refactor", "update", "migrate",
]


# ── Config Loading ─────────────────────────────────────────────────────────

def load_config(root: str) -> dict:
    path = os.path.join(root, ".claude", CONFIG_NAME)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def load_local_config(root: str) -> dict:
    path = os.path.join(root, ".claude", LOCAL_CONFIG_NAME)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def load_global_config() -> dict:
    if GLOBAL_CONFIG_PATH.exists():
        with open(GLOBAL_CONFIG_PATH) as f:
            return json.load(f)
    return {}


def load_session(root: str) -> dict:
    path = os.path.join(root, ".claude", SESSION_NAME)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_session(root: str, data: dict):
    path = os.path.join(root, ".claude", SESSION_NAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_cred(root: str, field: str) -> str:
    """Load credential field with fallback: project-local -> global."""
    val = load_local_config(root).get(field, "")
    if not val:
        val = load_global_config().get(field, "")
    return val or ""


# ── Debug Logging ──────────────────────────────────────────────────────────

def debug_log(message: str, category: str = "general", enabled: bool = True,
              log_path: str = None, **kwargs):
    if not enabled:
        return
    path = Path(log_path) if log_path else DEBUG_LOG_PATH
    # Rotate if too large
    if path.exists() and path.stat().st_size > MAX_LOG_SIZE:
        backup = path.with_suffix(".log.1")
        if backup.exists():
            backup.unlink()
        path.rename(backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    line = f"[{ts}] [{category}] {message}"
    if extra:
        line += f" {extra}"
    with open(path, "a") as f:
        f.write(line + "\n")


# ── CLI Dispatcher ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: jira_core.py <command> [args...]", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    commands = {
        "session-start": cmd_session_start,
        "log-activity": cmd_log_activity,
        "drain-buffer": cmd_drain_buffer,
        "session-end": cmd_session_end,
        "classify-issue": cmd_classify_issue,
        "suggest-parent": cmd_suggest_parent,
        "build-worklog": cmd_build_worklog,
        "debug-log": cmd_debug_log,
    }
    fn = commands.get(cmd)
    if not fn:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    fn(args)


def cmd_debug_log(args):
    root = args[0] if args else "."
    msg = args[1] if len(args) > 1 else "test"
    cfg = load_config(root)
    debug_log(msg, enabled=cfg.get("debugLog", False))


# Stubs — implemented in subsequent tasks
def cmd_session_start(args): pass
def cmd_log_activity(args): pass
def cmd_drain_buffer(args): pass
def cmd_session_end(args): pass
def cmd_classify_issue(args): pass
def cmd_suggest_parent(args): pass
def cmd_build_worklog(args): pass


if __name__ == "__main__":
    main()
