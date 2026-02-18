# Jira Autopilot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the plugin to jira-autopilot and implement 7 features: automatic context switching, autonomous logging, parent selection, worklog descriptions, bug-story linking, issue type classification, and debug logging.

**Architecture:** Shell hook scripts become thin wrappers calling `python3 jira_core.py <command>`. All business logic (state management, idle detection, context switch heuristics, classification, Jira API) lives in one Python module. Slash command markdown files are updated for new features and renamed config paths.

**Tech Stack:** Python 3 (stdlib only — json, re, time, os, urllib, subprocess), Bash hooks, Jira REST API v3

---

## Phase 0: Plugin Rename (jira-auto-issue → jira-autopilot)

### Task 0.1: Rename plugin directory and manifests

**Files:**
- Move: `plugins/jira-auto-issue/` → `plugins/jira-autopilot/`
- Modify: `plugins/jira-autopilot/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Step 1: Move the plugin directory**

```bash
git mv plugins/jira-auto-issue plugins/jira-autopilot
```

**Step 2: Update plugin.json**

In `plugins/jira-autopilot/.claude-plugin/plugin.json`:
```json
{
  "name": "jira-autopilot",
  "version": "3.0.0",
  "description": "Autonomous Jira work tracking, issue creation, and time logging for Claude Code sessions",
  "author": { "name": "Boris Sigalov" }
}
```

**Step 3: Update marketplace.json**

In `.claude-plugin/marketplace.json`, change:
- `"name": "jira-auto-issue"` → `"name": "jira-autopilot"`
- `"source": "./plugins/jira-auto-issue"` → `"source": "./plugins/jira-autopilot"`
- Update description, version, keywords (add "autopilot", "autonomous")

**Step 4: Update CLAUDE.md**

Replace all occurrences of `jira-auto-issue` with `jira-autopilot` and `jira-tracker` config references with `jira-autopilot`.

**Step 5: Update README.md**

Replace all occurrences of `jira-auto-issue` with `jira-autopilot`.

**Step 6: Rename config files in hooks/commands**

All references to `jira-tracker.json`, `jira-tracker.local.json`, `jira-tracker.global.json` → `jira-autopilot.json`, `jira-autopilot.local.json`, `jira-autopilot.global.json`. Files to update:
- `plugins/jira-autopilot/hooks-handlers/helpers.sh` — `GLOBAL_CONFIG`, `session_file`, `is_enabled`, `load_cred_field`
- `plugins/jira-autopilot/hooks-handlers/jira-rest.sh` — `jira_load_creds`
- `plugins/jira-autopilot/hooks-handlers/session-start-check.sh` — CONFIG path
- `plugins/jira-autopilot/hooks-handlers/session-end.sh` — config path
- `plugins/jira-autopilot/hooks-handlers/stop.sh` — any config refs
- `plugins/jira-autopilot/hooks-handlers/pre-tool-use.sh` — output prefix `[jira-autopilot]`
- `plugins/jira-autopilot/hooks-handlers/post-tool-use.sh` — no config refs but update if needed
- All command `.md` files — update paths and output prefixes

**Step 7: Update .gitignore**

Replace `jira-tracker.local.json` with `jira-autopilot.local.json`. Add `jira-tracker.local.json` to keep ignoring old file.

**Step 8: Commit**

```bash
git add -A && git commit -m "Rename plugin from jira-auto-issue to jira-autopilot"
```

---

## Phase 1: Core Module — jira_core.py

### Task 1.1: Create jira_core.py with CLI dispatcher and debug logging (Task 7)

**Files:**
- Create: `plugins/jira-autopilot/hooks-handlers/jira_core.py`
- Create: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`

**Step 1: Write test for debug logging**

```python
# tests/test_jira_core.py
import tempfile, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from jira_core import debug_log, load_config

def test_debug_log_writes_to_file():
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
        log_path = f.name
    try:
        debug_log("test message", log_path=log_path)
        with open(log_path) as f:
            content = f.read()
        assert "[test message]" in content or "test message" in content
    finally:
        os.unlink(log_path)

def test_debug_log_disabled():
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
        log_path = f.name
    try:
        debug_log("should not appear", enabled=False, log_path=log_path)
        with open(log_path) as f:
            content = f.read()
        assert content == ""
    finally:
        os.unlink(log_path)
```

**Step 2: Run test to verify it fails**

```bash
cd plugins/jira-autopilot/hooks-handlers && python3 -m pytest tests/test_jira_core.py -v
```

**Step 3: Implement jira_core.py skeleton with debug logging**

```python
#!/usr/bin/env python3
"""jira-autopilot core module — all business logic for hooks and commands."""

import json, os, re, sys, time, math, subprocess
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
    with open(path, 'w') as f:
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
        backup = path.with_suffix('.log.1')
        if backup.exists():
            backup.unlink()
        path.rename(backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    line = f"[{ts}] [{category}] {message}"
    if extra:
        line += f" {extra}"
    with open(path, 'a') as f:
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

# Stubs for other commands — implemented in subsequent tasks
def cmd_session_start(args): pass
def cmd_log_activity(args): pass
def cmd_drain_buffer(args): pass
def cmd_session_end(args): pass
def cmd_classify_issue(args): pass
def cmd_suggest_parent(args): pass
def cmd_build_worklog(args): pass

if __name__ == "__main__":
    main()
```

**Step 4: Run tests and verify passing**

```bash
cd plugins/jira-autopilot/hooks-handlers && python3 -m pytest tests/test_jira_core.py -v
```

**Step 5: Commit**

```bash
git add plugins/jira-autopilot/hooks-handlers/jira_core.py plugins/jira-autopilot/hooks-handlers/tests/
git commit -m "Add jira_core.py skeleton with CLI dispatcher and debug logging"
```

---

### Task 1.2: Implement session-start command

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_session_start`
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`
- Modify: `plugins/jira-autopilot/hooks-handlers/session-start-check.sh` — replace inline python with `python3 jira_core.py session-start`

**Step 1: Write test for session initialization**

```python
def test_session_start_creates_session(tmp_path):
    root = str(tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    # Write minimal config
    (claude_dir / CONFIG_NAME).write_text(json.dumps({
        "projectKey": "TEST", "enabled": True, "debugLog": False,
        "accuracy": 5, "autonomyLevel": "C"
    }))
    cmd_session_start([root])
    session = json.loads((claude_dir / SESSION_NAME).read_text())
    assert "sessionId" in session
    assert session["activeIssues"] == {}
    assert session["currentIssue"] is None
    assert session["autonomyLevel"] == "C"
```

**Step 2: Run test, verify fails**

**Step 3: Implement cmd_session_start**

Logic from current `session-start-check.sh` Python blocks, plus:
- Read `autonomyLevel` and `accuracy` from config into session
- Detect issue from git branch (reuse existing regex logic)
- Migrate old `current-task.json` if present
- Migration: also detect and rename old `jira-tracker.json` → `jira-autopilot.json`
- Debug log all decisions

**Step 4: Run tests, verify passing**

**Step 5: Update session-start-check.sh to thin wrapper**

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"
ROOT=$(find_project_root) || exit 0
python3 "$SCRIPT_DIR/jira_core.py" session-start "$ROOT"
```

**Step 6: Commit**

```bash
git commit -m "Implement session-start in jira_core.py, thin-wrap shell script"
```

---

### Task 1.3: Implement log-activity command (PostToolUse)

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_log_activity`
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`
- Modify: `plugins/jira-autopilot/hooks-handlers/post-tool-use.sh` — thin wrapper

**Step 1: Write test**

```python
def test_log_activity_stamps_current_issue(tmp_path):
    root = str(tmp_path)
    # Set up session with currentIssue = "TEST-1"
    session = {"sessionId": "test", "currentIssue": "TEST-1",
               "activeIssues": {"TEST-1": {"startTime": 1000, "totalSeconds": 0}},
               "activityBuffer": []}
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / SESSION_NAME).write_text(json.dumps(session))
    (claude_dir / CONFIG_NAME).write_text(json.dumps({"enabled": True, "debugLog": False}))

    tool_json = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "src/auth.ts"}})
    cmd_log_activity([root, tool_json])

    updated = json.loads((claude_dir / SESSION_NAME).read_text())
    assert len(updated["activityBuffer"]) == 1
    assert updated["activityBuffer"][0]["issueKey"] == "TEST-1"
    assert updated["activityBuffer"][0]["file"] == "src/auth.ts"
```

**Step 2: Run test, verify fails**

**Step 3: Implement — same logic as current post-tool-use.sh but:**
- Stamp every activity with `issueKey` = `currentIssue` at time of call
- Skip read-only tools (Read, Glob, Grep, etc.)
- Debug log each activity

**Step 4: Update post-tool-use.sh to thin wrapper**

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"
ROOT=$(find_project_root) || exit 0
INPUT=$(cat)
python3 "$SCRIPT_DIR/jira_core.py" log-activity "$ROOT" "$INPUT"
```

**Step 5: Run tests, commit**

---

### Task 1.4: Implement drain-buffer with idle detection and context switch (Task 1)

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_drain_buffer`
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`
- Modify: `plugins/jira-autopilot/hooks-handlers/stop.sh` — thin wrapper

**Step 1: Write tests**

```python
def test_drain_buffer_detects_idle(tmp_path):
    """Activities with >15min gap should split into chunks with idle marker."""
    root = str(tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / CONFIG_NAME).write_text(json.dumps({
        "enabled": True, "debugLog": False, "accuracy": 5, "idleThreshold": 15
    }))
    now = int(time.time())
    session = {
        "sessionId": "test", "currentIssue": "TEST-1",
        "activeIssues": {"TEST-1": {"startTime": now - 3600, "totalSeconds": 0}},
        "activityBuffer": [
            {"timestamp": now - 3600, "tool": "Edit", "file": "a.ts", "type": "file_edit", "issueKey": "TEST-1"},
            {"timestamp": now - 3500, "tool": "Edit", "file": "b.ts", "type": "file_edit", "issueKey": "TEST-1"},
            # 20 min gap — idle
            {"timestamp": now - 2300, "tool": "Edit", "file": "c.ts", "type": "file_edit", "issueKey": "TEST-1"},
        ],
        "workChunks": []
    }
    (claude_dir / SESSION_NAME).write_text(json.dumps(session))
    cmd_drain_buffer([root])
    updated = json.loads((claude_dir / SESSION_NAME).read_text())
    chunks = updated["workChunks"]
    assert len(chunks) >= 1
    # Verify idle gap is recorded
    has_idle = any(c.get("idleGaps") for c in chunks)
    assert has_idle

def test_drain_buffer_detects_context_switch(tmp_path):
    """Activities switching file directories should flag needs_attribution."""
    root = str(tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / CONFIG_NAME).write_text(json.dumps({
        "enabled": True, "debugLog": False, "accuracy": 7
    }))
    now = int(time.time())
    session = {
        "sessionId": "test", "currentIssue": "TEST-1",
        "activeIssues": {"TEST-1": {"startTime": now - 600, "totalSeconds": 0}},
        "activityBuffer": [
            {"timestamp": now - 600, "tool": "Edit", "file": "src/auth/login.ts", "type": "file_edit", "issueKey": "TEST-1"},
            {"timestamp": now - 500, "tool": "Edit", "file": "src/auth/token.ts", "type": "file_edit", "issueKey": "TEST-1"},
            {"timestamp": now - 400, "tool": "Edit", "file": "src/payments/stripe.ts", "type": "file_edit", "issueKey": "TEST-1"},
            {"timestamp": now - 300, "tool": "Edit", "file": "src/payments/webhook.ts", "type": "file_edit", "issueKey": "TEST-1"},
        ],
        "workChunks": []
    }
    (claude_dir / SESSION_NAME).write_text(json.dumps(session))
    result = cmd_drain_buffer([root])
    updated = json.loads((claude_dir / SESSION_NAME).read_text())
    # Should have at least one chunk flagged
    flagged = [c for c in updated["workChunks"] if c.get("needsAttribution")]
    assert len(flagged) > 0
```

**Step 2: Run tests, verify fails**

**Step 3: Implement drain-buffer**

Core logic:
1. Read activity buffer from session
2. Group consecutive activities, splitting on:
   - Idle gaps (timestamp delta > `idleThreshold` mins, scaled by accuracy)
   - File directory cluster changes (using `os.path.commonpath` heuristic)
   - Issue key changes (explicit switches)
3. For each group, create a work chunk with `idleGaps`, `needsAttribution`, `filesChanged`
4. Clear activity buffer
5. If `needsAttribution` chunks exist, output structured message to stdout for Claude
6. Debug log all decisions

**Step 4: Update stop.sh to thin wrapper**

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"
ROOT=$(find_project_root) || exit 0
python3 "$SCRIPT_DIR/jira_core.py" drain-buffer "$ROOT"
```

**Step 5: Run tests, commit**

---

### Task 1.5: Implement classify-issue (Task 6)

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_classify_issue`
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`

**Step 1: Write tests**

```python
def test_classify_bug():
    result = classify_issue("Fix login redirect crash")
    assert result["type"] == "Bug"
    assert result["confidence"] > 0.5

def test_classify_task():
    result = classify_issue("Add payment processing module")
    assert result["type"] == "Task"

def test_classify_ambiguous_defaults_to_task():
    result = classify_issue("Update dependencies")
    assert result["type"] == "Task"
```

**Step 2: Run tests, verify fails**

**Step 3: Implement classify_issue function**

```python
BUG_SIGNALS = ["fix", "bug", "broken", "crash", "error", "fail", "regression", "not working", "issue with"]
TASK_SIGNALS = ["add", "create", "implement", "build", "setup", "configure", "refactor", "update", "migrate"]

def classify_issue(summary: str, context: dict = None) -> dict:
    lower = summary.lower()
    bug_score = sum(1 for s in BUG_SIGNALS if s in lower)
    task_score = sum(1 for s in TASK_SIGNALS if s in lower)
    # Context signals (file creation vs editing only)
    if context:
        if context.get("new_files_created", 0) == 0 and context.get("files_edited", 0) > 0:
            bug_score += 1
        if context.get("new_files_created", 0) > 0:
            task_score += 1
    if bug_score >= 2 or (bug_score > task_score and bug_score >= 1):
        confidence = min(0.5 + bug_score * 0.15, 0.95)
        return {"type": "Bug", "confidence": confidence,
                "signals": [s for s in BUG_SIGNALS if s in lower]}
    confidence = min(0.5 + task_score * 0.15, 0.95)
    return {"type": "Task", "confidence": confidence,
            "signals": [s for s in TASK_SIGNALS if s in lower]}
```

**Step 4: Implement cmd_classify_issue (CLI wrapper)**

Reads summary from args, prints JSON result.

**Step 5: Run tests, commit**

---

### Task 1.6: Implement build-worklog (Task 4)

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_build_worklog`
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`

**Step 1: Write test**

```python
def test_build_worklog_summary(tmp_path):
    root = str(tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / CONFIG_NAME).write_text(json.dumps({"debugLog": False, "accuracy": 5}))
    session = {
        "currentIssue": "TEST-1",
        "activeIssues": {"TEST-1": {"startTime": 1000, "totalSeconds": 600}},
        "workChunks": [{
            "id": "chunk-1", "issueKey": "TEST-1",
            "startTime": 1000, "endTime": 1600,
            "filesChanged": ["src/auth.ts", "src/middleware.ts"],
            "activities": [
                {"tool": "Edit", "type": "file_edit"},
                {"tool": "Edit", "type": "file_edit"},
                {"tool": "Bash", "type": "bash", "command": "npm test"},
            ]
        }]
    }
    (claude_dir / SESSION_NAME).write_text(json.dumps(session))
    result = build_worklog(root, "TEST-1")
    assert "auth.ts" in result["summary"] or "middleware.ts" in result["summary"]
    assert result["seconds"] > 0
```

**Step 2: Run tests, verify fails**

**Step 3: Implement build_worklog function**

Gathers work chunks for the issue, builds a raw summary from files + activity counts. Returns:
```json
{
  "issueKey": "TEST-1",
  "seconds": 900,
  "summary": "Edited auth.ts, middleware.ts. Ran tests (npm test). 3 tool calls.",
  "rawFacts": {"files": [...], "commands": [...], "activityCount": 3}
}
```

The `rawFacts` field allows Claude to enrich with conversation context before posting.

**Step 4: Run tests, commit**

---

### Task 1.7: Implement session-end command

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_session_end`
- Modify: `plugins/jira-autopilot/hooks-handlers/session-end.sh` — thin wrapper
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`

**Step 1: Write test**

```python
def test_session_end_builds_pending_worklogs(tmp_path):
    root = str(tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / CONFIG_NAME).write_text(json.dumps({
        "debugLog": False, "accuracy": 5, "timeRounding": 15, "autonomyLevel": "C"
    }))
    now = int(time.time())
    session = {
        "sessionId": "test", "currentIssue": "TEST-1", "autonomyLevel": "C",
        "activeIssues": {"TEST-1": {"startTime": now - 1800, "totalSeconds": 0, "paused": False}},
        "workChunks": [{"id": "c1", "issueKey": "TEST-1", "startTime": now - 1800,
                        "endTime": now, "filesChanged": ["a.ts"], "activities": [{}]*5}],
        "activityBuffer": [], "pendingWorklogs": []
    }
    (claude_dir / SESSION_NAME).write_text(json.dumps(session))
    result = cmd_session_end([root])
    updated = json.loads((claude_dir / SESSION_NAME).read_text())
    # In autonomy C, worklogs should be pending (not auto-posted)
    assert len(updated.get("pendingWorklogs", [])) > 0
```

**Step 2: Run test, verify fails**

**Step 3: Implement cmd_session_end**

Logic:
1. For each active issue, calculate total time (minus idle gaps)
2. Round per config `timeRounding` (scaled by accuracy)
3. Build worklog summary via `build_worklog()`
4. Based on `autonomyLevel`:
   - **C**: add to `pendingWorklogs` with status `pending`, output for Claude to present approval flow
   - **B**: output summary, auto-approve after countdown
   - **A**: post directly via Jira REST, print one-liner
5. Archive session to `~/.claude/jira-sessions/`
6. Debug log everything

**Step 4: Update session-end.sh to thin wrapper**

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"
ROOT=$(find_project_root) || exit 0
python3 "$SCRIPT_DIR/jira_core.py" session-end "$ROOT"
```

**Step 5: Run tests, commit**

---

### Task 1.8: Implement suggest-parent (Task 3)

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — `cmd_suggest_parent`
- Modify: `plugins/jira-autopilot/hooks-handlers/tests/test_jira_core.py`

**Step 1: Write test**

```python
def test_suggest_parent_returns_recent(tmp_path):
    root = str(tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    local = {"recentParents": ["TEST-10", "TEST-8"]}
    (claude_dir / LOCAL_CONFIG_NAME).write_text(json.dumps(local))
    (claude_dir / CONFIG_NAME).write_text(json.dumps({"projectKey": "TEST", "debugLog": False}))
    session = {"lastParentKey": "TEST-10"}
    (claude_dir / SESSION_NAME).write_text(json.dumps(session))
    result = suggest_parent(root, "Fix auth bug")
    assert "TEST-10" in [r["key"] for r in result.get("recent", [])]
```

**Step 2: Run test, verify fails**

**Step 3: Implement suggest_parent function**

Returns:
```json
{
  "sessionDefault": "TEST-10",
  "contextual": [],
  "recent": [{"key": "TEST-10"}, {"key": "TEST-8"}]
}
```

The `contextual` array is populated by Jira API search (Epic/Story with matching keywords). This requires credentials, so the function gracefully returns empty `contextual` if no creds available (Claude fills via MCP instead).

**Step 4: Run tests, commit**

---

## Phase 2: Update Slash Commands

### Task 2.1: Update jira-setup.md for new config paths and features

**Files:**
- Modify: `plugins/jira-autopilot/commands/jira-setup.md`

**Step 1: Update all config paths** from `jira-tracker.*` to `jira-autopilot.*`

**Step 2: Add new config fields** to the "Show defaults" step:
- `accuracy`: 5 (1-10)
- `autonomyLevel`: "C" (C/B/A)
- `debugLog`: true (currently enabled for development)
- `idleThreshold`: 15

**Step 3: Add autonomy level explanation** in setup flow — explain C/B/A modes, let user choose

**Step 4: Add accuracy slider** — explain low/medium/high with examples, let user pick

**Step 5: Cache user accountId** — after connectivity test, extract accountId from `/myself` response and store in local config as `"accountId": "<id>"`

**Step 6: Commit**

---

### Task 2.2: Update jira-start.md for parent selection, type classification, and auto-assign

**Files:**
- Modify: `plugins/jira-autopilot/commands/jira-start.md`

**Step 1: Add parent selection flow** — before creating issue:
- Run `python3 jira_core.py suggest-parent <root> <summary>` to get candidates
- Present combined list (contextual + recent)
- In autonomy A/B, auto-select

**Step 2: Add type classification** — before creating issue:
- Run `python3 jira_core.py classify-issue <summary>` to get type suggestion
- In autonomy C, show and let user approve/change
- In autonomy A/B, use auto-classified type

**Step 3: Add auto-assign** — set assignee to cached accountId from local config

**Step 4: Add default fields** — labels (`jira-autopilot`), component (from `componentMap`), fix version

**Step 5: Add bug-story linking** (Task 5) — if type is Bug:
- Run suggest-parent but filter for Stories only
- Present story selection (create/choose/skip)

**Step 6: Update config path refs** to `jira-autopilot.*`

**Step 7: Commit**

---

### Task 2.3: Update jira-stop.md for worklog approval flow (Task 4)

**Files:**
- Modify: `plugins/jira-autopilot/commands/jira-stop.md`

**Step 1: Replace simple time logging** with approval flow:
- Build worklog via `python3 jira_core.py build-worklog <root> <key>`
- Claude enriches `rawFacts` into 1-3 line summary using conversation context
- Present 5 options (approve / approve+silent / edit / different issue / reject)

**Step 2: Add reject sub-flow** — keep for later or drop

**Step 3: Add redirect sub-flow** — show active issues, recent, enter key

**Step 4: Update config paths**

**Step 5: Commit**

---

### Task 2.4: Update remaining command files

**Files:**
- Modify: `plugins/jira-autopilot/commands/jira-status.md` — update paths, add accuracy/autonomy display
- Modify: `plugins/jira-autopilot/commands/jira-approve.md` — update paths
- Modify: `plugins/jira-autopilot/commands/jira-summary.md` — update paths

**Step 1: Update all config path references**

**Step 2: Add accuracy and autonomy info to jira-status output**

**Step 3: Commit**

---

## Phase 3: Update Hook Wrappers

### Task 3.1: Update pre-tool-use.sh

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/pre-tool-use.sh`

**Step 1: Update config paths** and output prefix to `[jira-autopilot]`

**Step 2: Add context-switch awareness instruction** — when outputting the commit message suggestion, also include a note for Claude about watching for topic shifts in conversation

**Step 3: Commit**

---

### Task 3.2: Update helpers.sh

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/helpers.sh`

**Step 1: Update all config file name references** from `jira-tracker` to `jira-autopilot`

**Step 2: Add backward compatibility** — if old `jira-tracker.json` exists but `jira-autopilot.json` doesn't, auto-migrate (rename files)

**Step 3: Keep `detect_project_key_from_git` and `load_cred_field`** — these are still used by thin shell wrappers

**Step 4: Commit**

---

### Task 3.3: Update hooks.json

**Files:**
- Modify: `plugins/jira-autopilot/hooks/hooks.json`

No path changes needed — `${CLAUDE_PLUGIN_ROOT}` resolves automatically after directory rename.

**Step 1: Verify all hook paths still resolve** after the Phase 0 rename

**Step 2: Commit if any changes needed**

---

## Phase 4: Jira REST API Additions

### Task 4.1: Add REST functions for parent search, story linking, and worklog with description

**Files:**
- Modify: `plugins/jira-autopilot/hooks-handlers/jira-rest.sh` — update config paths
- Modify: `plugins/jira-autopilot/hooks-handlers/jira_core.py` — add Jira API functions

**Step 1: Add to jira_core.py:**

```python
def jira_search_parents(root: str, summary: str) -> list:
    """Search for open Epics/Stories matching keywords from summary."""
    creds = _load_creds(root)
    keywords = " ".join(re.findall(r'\b[a-zA-Z]{3,}\b', summary)[:5])
    jql = f'project={creds["projectKey"]} AND issuetype in (Epic,Story) AND status != Done AND text ~ "{keywords}" ORDER BY updated DESC'
    # GET /rest/api/3/search?jql=...&maxResults=5
    ...

def jira_link_issues(root: str, inward_key: str, outward_key: str, link_type: str = "Relates"):
    """Create issue link between two issues."""
    # POST /rest/api/3/issueLink
    ...

def jira_log_time_with_comment(root: str, issue_key: str, seconds: int, comment: str):
    """Log work with a description comment."""
    # POST /rest/api/3/issue/{key}/worklog with comment field in ADF
    ...

def jira_get_versions(root: str) -> list:
    """Get unreleased versions for the project."""
    # GET /rest/api/3/project/{key}/versions
    ...

def jira_get_myself(root: str) -> dict:
    """Get current user info including accountId."""
    # GET /rest/api/3/myself
    ...
```

**Step 2: Update jira-rest.sh config paths**

**Step 3: Commit**

---

## Phase 5: Integration Testing

### Task 5.1: End-to-end test of the full hook lifecycle

**Files:**
- Create: `plugins/jira-autopilot/hooks-handlers/tests/test_integration.py`

**Step 1: Write integration test**

Simulates: session-start → log-activity × N (with idle gap and context switch) → drain-buffer → build-worklog → session-end. Verifies:
- Session state is correct at each step
- Idle gaps are detected and excluded from time
- Context switches are flagged
- Worklogs have correct seconds and summary
- Debug log contains all events

**Step 2: Run full test suite**

```bash
cd plugins/jira-autopilot/hooks-handlers && python3 -m pytest tests/ -v
```

**Step 3: Commit**

---

### Task 5.2: Manual smoke test

**Step 1: Reinstall plugin** — `/plugin` from the jira-tracker repo

**Step 2: Run `/jira-autopilot:jira-setup`** — verify new config paths, accuracy slider, autonomy selection

**Step 3: Run `/jira-autopilot:jira-start`** — verify parent selection, type classification, auto-assign

**Step 4: Make some edits, trigger stop** — verify context switch detection, worklog approval flow

**Step 5: Run `/jira-autopilot:jira-stop`** — verify 5-option approval flow works

---

## Execution Order Summary

| Phase | Tasks | Dependencies |
|-------|-------|-------------|
| **0** | 0.1 (rename) | None — must be first |
| **1** | 1.1-1.8 (jira_core.py) | 0.1 |
| **2** | 2.1-2.4 (commands) | 1.1-1.8 |
| **3** | 3.1-3.3 (hooks) | 0.1, 1.1 |
| **4** | 4.1 (REST API) | 1.1 |
| **5** | 5.1-5.2 (testing) | All above |

Phases 2, 3, and 4 can run in parallel after Phase 1.
