# Jira Autopilot — Autonomous Logging Design

**Date:** 2026-02-18
**Status:** Approved
**Plugin rename:** `jira-auto-issue` → `jira-autopilot`

## Overview

Transform the jira-auto-issue plugin into **jira-autopilot** — a fully autonomous Jira work tracker that detects context switches, classifies issue types, manages parent relationships, and logs time with rich descriptions, all with configurable autonomy levels.

## Core Architecture

### Approach: Python module (Approach B)

All business logic moves from inline `python3 -c` blocks into a single `hooks-handlers/jira_core.py` module. Shell scripts become thin 5-line wrappers that call `python3 jira_core.py <command>`.

### CLI subcommands

```
python3 jira_core.py session-start   <root>
python3 jira_core.py log-activity    <root> <tool_json>
python3 jira_core.py drain-buffer    <root>
python3 jira_core.py session-end     <root>
python3 jira_core.py classify-issue  <summary>
python3 jira_core.py suggest-parent  <root> <summary>
python3 jira_core.py build-worklog   <root> <issue_key> [conversation_context]
python3 jira_core.py debug-log       <root> <message>
```

### Config files (renamed)

| File | Purpose | Committed |
|------|---------|-----------|
| `.claude/jira-autopilot.json` | Project config | Yes |
| `.claude/jira-autopilot.local.json` | Project credentials | No (gitignored) |
| `~/.claude/jira-autopilot.global.json` | Global credentials + prefs | N/A |
| `.claude/jira-session.json` | Runtime session state | No (gitignored) |
| `~/.claude/jira-autopilot-debug.log` | Debug log | N/A |

### Extended session state schema

```json
{
  "sessionId": "20260218-1234",
  "autonomyLevel": "C",
  "disabled": false,
  "activeIssues": {
    "PROJ-1": {
      "summary": "Auth middleware refactor",
      "startTime": 1234567890,
      "totalSeconds": 0,
      "paused": false,
      "assignee": "accountId",
      "autoApproveWorklogs": false
    }
  },
  "currentIssue": "PROJ-1",
  "lastParentKey": "PROJ-0",
  "workChunks": [
    {
      "id": "chunk-1",
      "issueKey": "PROJ-1",
      "startTime": 1234567890,
      "endTime": 1234568790,
      "activities": [],
      "filesChanged": [],
      "idleGaps": [],
      "needsAttribution": false,
      "summary": ""
    }
  ],
  "pendingWorklogs": [
    {
      "issueKey": "PROJ-1",
      "seconds": 900,
      "summary": "Refactored auth middleware",
      "status": "pending"
    }
  ],
  "activityBuffer": []
}
```

### Extended project config

```json
{
  "projectKey": "PROJ",
  "cloudId": "uuid",
  "enabled": true,
  "autonomyLevel": "C",
  "accuracy": 5,
  "debugLog": true,
  "branchPattern": "^(?:feature|fix|hotfix|chore|docs)/({key}-\\d+)",
  "commitPattern": "{key}-\\d+:",
  "timeRounding": 15,
  "idleThreshold": 15,
  "defaultComponent": null,
  "defaultLabels": ["jira-autopilot"],
  "defaultFixVersion": null,
  "componentMap": {},
  "autoCreate": false
}
```

---

## Task 1: Automatic Context Switch + Idle Detection

### Per-issue time attribution

Each activity logged by PostToolUse gets stamped with `currentIssue` at the time of call. When the user runs `/jira-start PROJ-2`, `currentIssue` switches and the previous issue's timer pauses automatically.

### Automatic detection (no manual switch required)

**Hook-side heuristics** (in `jira_core.py drain-buffer`):
- **Idle detection**: gap between consecutive activities > `idleThreshold`. Idle periods are excised from time and stored as `idleGaps`. Neither issue is charged.
- **File pattern shift**: activities cluster around different directory trees → mark chunk boundary as potential context switch.
- **Branch change**: `git rev-parse --abbrev-ref HEAD` changes between activities.

When detected, chunk is marked `needsAttribution: true` and Stop hook outputs:
```
[jira-autopilot] Context switch detected at 14:23.
  Before: 3 edits to src/auth/ → attributed to PROJ-1
  After: 2 edits to src/payments/ → unattributed
```

**Claude-side** (conversational monitoring):
Claude watches conversation for topic shifts and proactively suggests switching issues. Implemented via system-level instruction in PreToolUse hook output.

**Ambiguous resolution**: Claude presents options — log to current issue, create new issue, log to another existing issue, or discard.

### Accuracy parameter interaction

| Accuracy | Idle threshold | Context switch sensitivity | Min task duration |
|----------|---------------|--------------------------|-------------------|
| 1-3 (low) | 30 min | Ignore minor shifts | 30 min, combine small tasks |
| 4-7 (medium) | 15 min | Major file/dir changes | 10 min |
| 8-10 (high) | 5 min | Any file cluster change | 2 min |

---

## Task 2: Autonomous Mode

### Autonomy levels

| Level | Issue creation | Worklog posting | User interaction |
|-------|---------------|----------------|-----------------|
| **C** (default) | Show summary, require approval | Show log, require approval | Full control |
| **B** | Show summary, auto-proceed after 10s | Show log, auto-post | Informational |
| **A** | Create silently, print one-liner | Post silently, print one-liner | Fully silent |

Issue type classification follows autonomy level: in A/B auto-classify silently, in C show and let user approve/change.

### Default behavior (autonomy C)

1. PostToolUse logs activity silently (async)
2. Stop drains buffer, detects context switches, presents attribution choices
3. Before commit: Claude proposes creating an issue if none exists, shows summary, user approves
4. SessionEnd builds worklogs, user approves/edits/redirects/rejects

### Disable tracking scopes

| Scope | Storage | Effect |
|-------|---------|--------|
| Session | `jira-session.json` → `disabled: true` | Silent tracking, no Jira calls |
| Day | `local.json` → `disabledUntil: <epoch>` | Silent tracking |
| Folder | `jira-autopilot.json` → `enabled: false` | Full stop |
| Global | `global.json` → `enabled: false` | Full stop |

---

## Task 3: Parent Issue Selection

### Selection flow

1. **Default**: use `lastParentKey` from current session
2. **Contextual search**: query Jira for open Epics/Stories matching keywords from new issue summary
3. **Recent history**: pull from session archives
4. **Present combined list**:

```
Parent for "Fix Stripe webhook timeout":
  Suggested (by context):
    1. PROJ-10: Payment Integration Epic (recommended)
    2. PROJ-15: Q1 Backend Reliability Story
  Recent:
    3. PROJ-8: Auth Refactor Epic (last used 2h ago)
  Other:
    4. Enter a key/URL
    5. Create new parent
    6. No parent
```

In autonomy A/B: auto-select contextual best match or `lastParentKey`.
In autonomy C: show full selection list.

State: `lastParentKey` in session, `recentParents` (last 10) in local config.

---

## Task 4: Worklog Descriptions + Approval Flow

### Summary generation

1. Activity buffer gives raw facts: files edited, commands run, test results
2. Claude enriches into 1-3 readable lines using conversation context

### Approval flow (at Stop/SessionEnd)

```
[jira-autopilot] Worklog for PROJ-1 (45m):
  "Refactored auth middleware to support SSO tokens"

  1. Approve
  2. Approve + go silent for this issue
  3. Edit summary
  4. Log to different issue
  5. Reject
```

| Choice | Behavior |
|--------|----------|
| 1. Approve | Post worklog with summary, assign to current user |
| 2. Approve + silent | Post, set `autoApproveWorklogs: true` for this issue |
| 3. Edit | User types replacement, then posts |
| 4. Different issue | Show active/recent issues, enter key. Reattribute worklog |
| 5. Reject | Ask: keep for later (→ `pendingWorklogs` as deferred) or drop entirely |

### Autonomy interaction

| Level | Behavior |
|-------|----------|
| C | Full approval flow |
| B | Show summary, auto-approve after 10s |
| A | Post silently, print one-liner |

---

## Task 5: Bug → Story Linking

When an issue is classified as Bug, trigger story linking:

```
This looks like a Bug. Bugs should be linked to a Story.
  1. Create new Story
  2. PROJ-22: Payment error handling (suggested)
  3. PROJ-18: Auth hardening (recent)
  4. PROJ-14: Q1 stability (recent)
  5. Enter story key/URL
  6. Skip — no Story
```

Same search/ranking engine as parent selection. Link type: `relates to` (configurable).
In autonomy A/B: auto-link to best match. In C: show selection.

---

## Task 6: Task vs Bug Auto-Classification

### Bug signals (2+ match → Bug)
- Summary contains: "fix", "bug", "broken", "crash", "error", "fail", "regression", "not working"
- Triggered by error log, failing test, or stack trace in conversation
- Only editing existing code, no new files created

### Task signals (default)
- Summary contains: "add", "create", "implement", "build", "setup", "configure", "refactor", "update", "migrate"
- Creating new files or adding new functions

### Output
```json
{
  "type": "Bug",
  "confidence": 0.85,
  "signals": ["summary contains 'fix'", "no new files created"]
}
```

Follows autonomy level: A/B auto-classify silently, C show and let user approve/change.

---

## Task 7: Debug Logging

### Log location
`~/.claude/jira-autopilot-debug.log`

### Format
```
[2026-02-18 14:23:05] [session-start] root=/Users/boris/Source/myapp sessionId=20260218-1234
[2026-02-18 14:23:06] [log-activity] tool=Edit file=src/auth.ts issueKey=PROJ-1
[2026-02-18 14:25:12] [idle-detected] gap=22min threshold=15min
[2026-02-18 14:25:12] [context-switch] signal=file_pattern from=src/auth/* to=src/payments/*
[2026-02-18 14:30:00] [drain-buffer] chunks=2 attributed=1 needs_attribution=1
[2026-02-18 14:30:01] [classify-issue] summary="Fix webhook" type=Bug confidence=0.85
[2026-02-18 14:30:02] [jira-api] POST /issue response=201 key=PROJ-5
[2026-02-18 14:30:03] [worklog-post] PROJ-1 seconds=900 status=approved
```

### Config
- `jira-autopilot.json` → `"debugLog": true` (enabled for development)
- Default for users: `false`
- Log rotation: truncate at 1MB, keep 1 backup

---

## Additional Issue Fields

| Field | Source | Behavior |
|-------|--------|----------|
| assignee | Cached `accountId` from `/myself` | Always set to current user |
| component | Config `defaultComponent` or `componentMap` auto-detect from file paths | Suggest if path matches |
| labels | Config `defaultLabels` + `jira-autopilot` | Always tag with `jira-autopilot` |
| fix version | Config `defaultFixVersion` or latest unreleased from Jira | Query versions API, suggest latest |
| story points | Not auto-set | Only if user provides |
| remaining estimate | `originalEstimate - timeSpent` | Updated on each worklog post |

### Component auto-detection

```json
"componentMap": {
  "src/auth/": "Authentication",
  "src/payments/": "Payments",
  "src/api/": "Backend API"
}
```

---

## Future Tasks (not in this phase)

| Feature | Approach |
|---------|----------|
| Claude vs human worklogs | Tag worklog comments with `[jira-autopilot]` prefix, filterable in dashboards |
| Estimation management | New `/jira-autopilot:jira-estimate` command |
| Version & backlog management | New `/jira-autopilot:jira-backlog` command |
| Issues for teammates | Extend creation flow with assignee picker via Jira user search |

---

## Accuracy Parameter Reference

| Setting | Low (1-3) | Medium (4-7) | High (8-10) |
|---------|-----------|-------------|-------------|
| Time rounding | 30 min | 15 min | 1 min |
| Min task duration | 30 min (combine below) | 10 min | 2 min |
| Context switch sensitivity | Ignore minor | Major file/dir | Any cluster change |
| Idle threshold | 30 min | 15 min | 5 min |
| Issues per day | ~3-4 | ~5-8 | 10+ |
| Combining | Group small under common issue | Group sub-5-min only | Never combine |
