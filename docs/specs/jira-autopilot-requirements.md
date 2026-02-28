# Jira Autopilot — Requirements Specification

| Field | Value |
|-------|-------|
| Author | Boris Sigalov |
| Date | 28/02/2026 |
| Version | 1.0 |
| Status | Initial release |

## Change Tracking

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 28/02/2026 | Boris Sigalov | Initial specification |

---

# 1. General

## 1.1 Purpose

This document is the complete requirements specification for **jira-autopilot** — a Claude Code plugin that provides autonomous Jira work tracking, issue creation, and time logging. It is designed to be sufficient for an AI agent to implement the plugin from scratch without access to the original source code.

**Scope:** Plugin manifest, slash commands, hook handlers, REST API client, core business logic, state management, and CLI interface.

**Out of scope:** The Claude Code plugin framework itself, the Atlassian MCP server, and the user's Jira Cloud instance configuration.

## 1.2 Glossary

| Term | Definition |
|------|-----------|
| Claude Code | Anthropic's CLI tool for AI-assisted software engineering |
| Plugin | A Claude Code extension that registers hooks, commands, and skills |
| Hook | A shell script triggered by Claude Code lifecycle events (SessionStart, PostToolUse, etc.) |
| Slash command | A user-invocable command (e.g. `/jira-start`) defined as a markdown file |
| Skill | A reusable workflow that can be invoked programmatically or via `/skill-name` |
| Session | A single Claude Code conversation, from start to end |
| Work chunk | A contiguous block of tool activity attributed to an issue (or unattributed) |
| Worklog | A Jira time entry posted to an issue via the REST API |
| Autonomy level | How much the plugin does without asking — C (Cautious), B (Balanced), A (Autonomous) |
| Accuracy | A 1-10 scale controlling time rounding, idle thresholds, and issue granularity |
| ADF | Atlassian Document Format — JSON structure for rich text in Jira REST API |
| MCP | Model Context Protocol — allows Claude to call external tools (e.g. Atlassian) |

## 1.3 External Systems

| System | Interface | Direction | Critical | Notes |
|--------|-----------|-----------|----------|-------|
| Jira Cloud REST API v3 | HTTPS REST | Read + Write | Yes | Issue CRUD, worklogs, comments, project search |
| Atlassian MCP Server | MCP tool calls | Read + Write | No | Optional — commands try MCP first, fall back to REST |
| Anthropic API | HTTPS REST | Read | No | Optional — for AI-enriched worklog summaries (Claude Haiku) |
| Git | Local CLI | Read | No | Branch detection, commit history scanning, project key detection |

## 1.4 Architecture

### Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Plugin manifest | JSON | Claude Code plugin registration format |
| Slash commands | Markdown + YAML frontmatter | Declarative command definitions |
| Hook handlers | Bash shell scripts | Entry points triggered by Claude Code events |
| Core logic | Python 3 (stdlib only) | All business logic — no external dependencies |
| HTTP client | `urllib.request` | REST API calls to Jira and Anthropic |
| JSON parsing | `json` module | State file management |
| Legacy REST client | Bash + curl | `jira-rest.sh` — fallback for shell-only contexts |

**Design constraint:** No npm, pip, or any external package dependencies. Only Python 3 stdlib and standard macOS CLI tools.

### File Structure

```
plugins/jira-autopilot/
├── .claude-plugin/
│   └── plugin.json                    # Plugin manifest (name, version)
├── hooks/
│   └── hooks.json                     # Hook registrations
├── hooks-handlers/
│   ├── jira_core.py                   # Core business logic (~2000 lines)
│   ├── helpers.sh                     # Bash utility functions
│   ├── jira-rest.sh                   # Legacy curl-based REST client
│   ├── jira-status.sh                 # Status display formatter
│   ├── session-start-check.sh         # SessionStart hook
│   ├── post-tool-use.sh               # PostToolUse hook (async)
│   ├── pre-tool-use.sh                # PreToolUse hook
│   ├── stop.sh                        # Stop hook
│   ├── session-end.sh                 # SessionEnd hook
│   ├── user-prompt-submit.sh          # UserPromptSubmit hook
│   └── tests/
│       ├── conftest.py                # Test fixtures
│       └── test_jira_core.py          # Unit tests
├── commands/
│   ├── jira-setup.md                  # /jira-setup command
│   ├── jira-start.md                  # /jira-start command
│   ├── jira-stop.md                   # /jira-stop command
│   ├── jira-status.md                 # /jira-status command
│   ├── jira-approve.md                # /jira-approve command
│   └── jira-summary.md               # /jira-summary command
├── skills/
│   └── bump-release/
│       └── SKILL.md                   # Release workflow skill
└── statusline-command.sh              # Statusline integration
```

### State Files (per project)

```
<project-root>/.claude/
├── jira-autopilot.json                # Project config (committed)
├── jira-autopilot.local.json          # Credentials (gitignored)
├── jira-session.json                  # Runtime session state (gitignored)
└── jira-sessions/                     # Archived sessions (gitignored)
    └── <sessionId>.json
```

### Global State

```
~/.claude/
├── jira-autopilot.global.json         # Global credentials + defaults
├── jira-autopilot-debug.log           # Debug log (rotated at 1MB)
└── jira-autopilot-api.log             # API call log (rotated at 1MB)
```

---

# 2. Configuration

## 2.1 Project Config — `.claude/jira-autopilot.json`

Committed to the repository. Contains non-sensitive project settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `projectKey` | string | `""` | Jira project key (e.g. `"PROJ"`). Empty string = monitoring mode (no issue attribution). |
| `cloudId` | string | `""` | Jira Cloud ID for API calls |
| `enabled` | boolean | `true` | Master on/off switch |
| `autonomyLevel` | string | `"C"` | `"C"` (Cautious), `"B"` (Balanced), or `"A"` (Autonomous) |
| `accuracy` | integer | `5` | 1-10. Controls rounding, idle threshold, and issue granularity. |
| `debugLog` | boolean | `true` | Enable debug logging to `~/.claude/jira-autopilot-debug.log` |
| `branchPattern` | string | `"^(?:feature\|fix\|hotfix\|chore\|docs)/({key}-\\d+)"` | Regex for extracting issue key from branch name. `{key}` is replaced with `projectKey` at runtime. |
| `commitPattern` | string | `"{key}-\\d+:"` | Regex for detecting issue key in commit messages |
| `timeRounding` | integer | `15` | Minutes to round worklogs up to |
| `idleThreshold` | integer | `15` | Minutes of inactivity before splitting work chunks |
| `autoCreate` | boolean | `false` | Auto-create Jira issues when work intent is detected. `true` for autonomy A/B. |
| `logLanguage` | string | `"English"` | Language for worklog descriptions. Options: `"English"`, `"Hebrew"`, `"Russian"`, or any language name. |
| `defaultLabels` | string[] | `["jira-autopilot"]` | Labels applied to all created issues |
| `defaultComponent` | string\|null | `null` | Default Jira component |
| `defaultFixVersion` | string\|null | `null` | Default Jira fix version |
| `componentMap` | object | `{}` | Mapping of file path patterns to Jira component names |
| `worklogInterval` | integer | `15` | Minutes between periodic worklog flushes |

## 2.2 Local Config — `.claude/jira-autopilot.local.json`

Gitignored. Contains credentials and user-specific data.

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Atlassian account email |
| `apiToken` | string | Atlassian API token |
| `baseUrl` | string | Jira instance URL (e.g. `"https://company.atlassian.net"`) |
| `accountId` | string | Jira account ID (cached from `/myself` endpoint) |
| `anthropicApiKey` | string | Optional. Anthropic API key for AI-enriched worklog summaries. |
| `recentParents` | string[] | Last 10 parent issue keys used (for auto-suggesting parents) |

## 2.3 Global Config — `~/.claude/jira-autopilot.global.json`

Same fields as local config, plus:

| Field | Type | Description |
|-------|------|-------------|
| `cloudId` | string | For auto-setup in new projects |
| `logLanguage` | string | Global default worklog language |

**Credential resolution order:** project-local → global.

## 2.4 Accuracy Scaling Rules

| Accuracy Range | Time Rounding | Idle Threshold | Issue Granularity |
|----------------|---------------|----------------|-------------------|
| Low (1-3) | `timeRounding * 2` | `idleThreshold * 2` | ~3-4 issues/day, combines small tasks |
| Medium (4-7) | `timeRounding` | `idleThreshold` | ~5-8 issues/day |
| High (8-10) | `max(timeRounding/15, 1)` min | `max(idleThreshold/3, 5)` min | 10+ issues/day, never combines tasks |

## 2.5 Autonomy Level Behaviors

| Behavior | C (Cautious) | B (Balanced) | A (Autonomous) |
|----------|-------------|-------------|----------------|
| Issue creation | Ask before creating | Show summary, auto-proceed | Silent, one-line confirmation |
| Worklog posting | 5-option approval flow | Show then auto-approve | Silent post |
| Auto-create on intent | Suggest `/jira-start` | Auto-create (with notice) | Auto-create (silent) |
| Periodic worklogs | Save as `"pending"` | Save as `"approved"` (auto-post) | Save as `"approved"` (auto-post) |

**Autonomy resolution:** Session state overrides config. Numeric mapping: 10=A, 6-9=B, 1-5=C. Default: C.

---

# 3. Session State

## 3.1 Session Structure — `.claude/jira-session.json`

```json
{
  "sessionId": "20260228-123456",
  "autonomyLevel": "C",
  "accuracy": 5,
  "disabled": false,
  "activeIssues": {
    "KEY-42": {
      "summary": "Fix login crash",
      "startTime": 1740700000,
      "totalSeconds": 0,
      "paused": false,
      "autoApproveWorklogs": false
    }
  },
  "currentIssue": "KEY-42",
  "lastParentKey": "KEY-10",
  "workChunks": [],
  "pendingWorklogs": [],
  "pendingIssues": [],
  "activityBuffer": [],
  "activeTasks": {},
  "taskSubjects": {},
  "activePlanning": null,
  "lastWorklogTime": 1740700000
}
```

## 3.2 Work Chunk Structure

```json
{
  "id": "chunk-1740700000-0",
  "issueKey": "KEY-42",
  "startTime": 1740700000,
  "endTime": 1740700600,
  "activities": [
    {
      "timestamp": 1740700100,
      "tool": "Edit",
      "type": "file_edit",
      "issueKey": "KEY-42",
      "file": "src/auth.ts",
      "command": ""
    }
  ],
  "filesChanged": ["src/auth.ts"],
  "idleGaps": [
    {"startTime": 1740700200, "endTime": 1740700400, "seconds": 200}
  ],
  "needsAttribution": false
}
```

**Activity types:** `file_edit`, `file_write`, `bash`, `agent`, `other`

## 3.3 Pending Worklog Structure

```json
{
  "issueKey": "KEY-42",
  "seconds": 900,
  "summary": "Implemented auth flow",
  "rawFacts": {
    "files": ["src/auth.ts", "src/login.tsx"],
    "commands": ["npm test"],
    "activityCount": 5
  },
  "status": "pending"
}
```

**Statuses:** `pending`, `approved`, `posted`, `failed`, `deferred`, `unattributed`, `dropped`, `skipped`

## 3.4 Pending Issue Structure

```json
{
  "suggestedSummary": "Fix authentication bug",
  "status": "awaiting_approval"
}
```

**Statuses:** `awaiting_approval`, `approved`, `linked`, `skipped`

## 3.5 Active Task Structure (Claude task tracking)

```json
{
  "taskId": {
    "subject": "Build payment feature",
    "startTime": 1740700000,
    "jiraKey": null
  }
}
```

## 3.6 Active Planning Structure

```json
{
  "startTime": 1740700000,
  "issueKey": "KEY-42",
  "subject": "Planning: superpowers:brainstorming"
}
```

## 3.7 Session Archival

At session end, the full session state is archived to `.claude/jira-sessions/<sessionId>.json`. The archive preserves all data for cross-session reporting via `/jira-summary`.

## 3.8 Atomic State Writes

Session state must be written atomically using `tempfile.mkstemp()` + `os.replace()` to prevent corruption from concurrent async hooks writing simultaneously.

---

# 4. Hook Lifecycle

## 4.1 Hook Registration — `hooks/hooks.json`

| Hook Event | Script | Async | Timeout |
|------------|--------|-------|---------|
| `SessionStart` | `session-start-check.sh` | No | default |
| `PostToolUse` | `post-tool-use.sh` | **Yes** | default |
| `PreToolUse` | `pre-tool-use.sh` | No | default |
| `Stop` | `stop.sh` | No | default |
| `SessionEnd` | `session-end.sh` | No | default |
| `UserPromptSubmit` | `user-prompt-submit.sh` | No | 10s |

All scripts use `${CLAUDE_PLUGIN_ROOT}` for path resolution.

## 4.2 SessionStart Hook

**Script:** `session-start-check.sh`
**Calls:** `jira_core.py session-start <root>`

**Behavior:**

1. Migrate old config file names (`jira-tracker.*` → `jira-autopilot.*`)
2. If no project config exists:
   a. Try `_auto_setup_from_global()` — creates config from global credentials
   b. Auto-setup detects project key from git history, **validates against real Jira projects**, creates config with validated key or empty key
3. If `enabled: false` → return silently
4. **Existing session with active issues:**
   - Preserve session state
   - Prune stale issues (>24h old, zero `totalSeconds`, zero work chunks)
   - Sync `autonomyLevel` and `accuracy` from config
   - Ensure required fields exist (`activeTasks`, `activePlanning`, `lastWorklogTime`)
   - Sanitize commands in session state (redact credentials)
   - Assign `sessionId` if missing
5. **New session:**
   - Create full session structure with all required fields
   - Detect issue from git branch via `branchPattern` regex
   - If branch issue detected: add to `activeIssues`, set as `currentIssue`, retroactively claim null work chunks
   - If autonomy A + `autoCreate` and no branch issue: attempt auto-create from recent git commit messages
6. Display status via `jira-status.sh`

## 4.3 PostToolUse Hook (Async)

**Script:** `post-tool-use.sh`
**Calls:** `jira_core.py log-activity <root>` with tool JSON on stdin

**Input JSON from Claude Code:**
```json
{
  "tool_name": "Edit",
  "tool_input": {"file_path": "/src/auth.ts", "old_string": "...", "new_string": "..."},
  "tool_response": "File updated"
}
```

**Behavior:**

1. Parse tool name and input
2. **Skip read-only tools:** `Read`, `Glob`, `Grep`, `LS`, `WebSearch`, `WebFetch`, `TodoRead`, `NotebookRead`, `AskUserQuestion`, `TaskList`, `TaskGet`, `ToolSearch`, `Skill`, `Task`, `ListMcpResourcesTool`, `BashOutput`
3. **Skip `.claude/` file writes** — internal state, not user work
4. **Planning skill detection:** If `tool_name == "Skill"` and skill name contains `plan`, `brainstorm`, `spec`, `explore`, or `research` → handle as planning event, do not log to activity buffer
5. **Planning mode events:** `EnterPlanMode` starts planning, `ExitPlanMode` or first file-write tool (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`) ends planning
6. **Task events:** `TaskCreate` caches subject, `TaskUpdate` to `in_progress` starts tracking, `TaskUpdate` to `completed` logs time (if >= 60s)
7. **Normal activity:** Create activity record:
   - `timestamp`: current epoch seconds
   - `tool`: tool name
   - `type`: classify as `file_edit`/`file_write`/`bash`/`agent`/`other`
   - `issueKey`: current active issue key (or null)
   - `file`: extracted file path (from `file_path`, `path`, `pattern`, etc.)
   - `command`: sanitized bash command (if applicable)
8. **Credential sanitization:** Redact Atlassian API tokens (`ATATT3x...`), Bearer/Basic auth headers, `-u user:token` patterns, `printf` credential patterns, JSON `"apiToken"` values

## 4.4 PreToolUse Hook

**Script:** `pre-tool-use.sh`

**Behavior:** Only acts on `Bash` tool with `git commit` commands.

1. If no current issue → exit
2. If issue key already in commit message → exit
3. Emit `systemMessage` instructing Claude to include `"<KEY>: <description>"` in the commit message, or to run `/jira-start` if work is unrelated

## 4.5 Stop Hook

**Script:** `stop.sh`
**Calls:** `jira_core.py drain-buffer <root>`

**Critical rule:** ALWAYS exit 0. Never block Claude's stop event.

**Buffer drain behavior:**

1. If empty buffer: still call periodic worklog flush, return
2. Sort activities by timestamp
3. Split into groups on:
   - Idle gaps exceeding `idleThreshold` (scaled by accuracy)
   - Issue key changes between consecutive activities
   - Directory cluster shifts (context switch detection)
4. Convert groups to work chunks with:
   - Calculated idle gaps
   - `needsAttribution: true` flag on context switches
   - File lists aggregated from activities
5. Clear activity buffer
6. Call periodic worklog flush

**Periodic worklog flush:**

1. Check `worklogInterval` (default 15 min) against `lastWorklogTime`
2. For each active issue with work chunks: build worklog, optionally enrich via AI, create pending entry
3. For unattributed null chunks: if autonomy A + autoCreate → attempt auto-create issue; otherwise save as `"unattributed"` pending
4. For autonomy A/B: auto-post approved worklogs immediately
5. For autonomy C: save as `"pending"` for later approval
6. Clear processed chunks, update `lastWorklogTime`

**Context switch detection:**

- `_get_dir_cluster(file_path, depth=2)` → extracts first 2 directory components (e.g. `src/auth`)
- Compare top-2 directory clusters between previous and current activity groups
- High accuracy (8-10): any cluster change flags a switch
- Medium: complete shift required
- Low (1-3): complete shift + minimum 3 activities each side

## 4.6 SessionEnd Hook

**Script:** `session-end.sh`
**Calls:** `jira_core.py session-end <root>`, then `jira_core.py post-worklogs <root>`

**Session end behavior:**

1. Flush active planning session (log planning time if >= 60s)
2. Drain remaining activity buffer
3. For each active issue: build worklog, enrich summary, create pending worklog entry
4. Prune ghost issues (paused, zero seconds, no work chunks)
5. Rescue unattributed null chunks:
   - Autonomy A + autoCreate: attempt auto-create issue
   - B/C: save as `"unattributed"` pending
6. Archive full session to `.claude/jira-sessions/<sessionId>.json`
7. Clear processed work chunks (prevent double-posting)
8. Reset `startTime` watermark for each active issue to `now`

**Worklog posting:**

1. Post all entries with `status: "approved"` to Jira
2. Skip `"pending"`, `"deferred"`, `"unattributed"` entries
3. Mark posted as `"posted"` or `"failed"`
4. Rebuild missing summary from `rawFacts` if empty

## 4.7 UserPromptSubmit Hook

**Script:** `user-prompt-submit.sh`
**Timeout:** 10 seconds

**Two detection paths:**

**Time-logging intent:** Matches patterns: `1h`, `30m`, `2h30m`, `log time`, `log.*hour`, `spent.*minute`, `worklog`. Emits `systemMessage` redirecting to `/jira-stop` instead of direct MCP worklog calls.

**Task/fix intent:** Matches implementation signals (`implement`, `add feature`, `build`, `create`, `refactor`, `migrate`, etc.) and bug signals (`fix`, `bug`, `broken`, `crash`, `error`, `regression`, etc.).

- **Autonomy A/B:** Call `jira_core.py auto-create-issue`. If duplicate → show notice (B) or silence (A). If new issue created → emit `systemMessage` with branch instruction.
- **Autonomy C (or no creds/low confidence):**
  - No active issue: "Work is being captured. Run /jira-start to link."
  - Active issue exists: "New task detected while KEY active. Run /jira-start to create sub-issue."

---

# 5. Slash Commands

## 5.1 `/jira-setup` — Configure Jira Tracking

**Allowed tools:** Bash, Write, Edit, Read, AskUserQuestion, Glob

**14-step guided setup flow:**

### Step 1: Check for saved global credentials

- If `~/.claude/jira-autopilot.global.json` exists with `baseUrl`, `email`, `apiToken`:
  - Show saved email and URL (NOT the token)
  - Ask: "Found saved Jira credentials for **user@company.com** at **https://company.atlassian.net**. Use these?"
  - If yes → skip steps 2-3, reuse saved values
- If no → continue to steps 2-3

### Step 2: Ask for Jira base URL

- Plain text input (NOT AskUserQuestion)
- Validate HTTPS
- Auto-fetch Cloud ID via `GET <baseUrl>/_edge/tenant_info` → extract `cloudId`
- If fetch fails → ask manually

### Step 3: Ask for credentials

- Email address
- API token (link to `https://id.atlassian.com/manage-profile/security/api-tokens`)

### Step 4: Test connectivity

- `GET <baseUrl>/rest/api/3/myself` with Basic auth
- Extract `accountId` and `displayName`
- Show: "Connected as **displayName**"
- Must succeed before proceeding

### Step 5: Select project key from Jira

- Call `jira_core.py get-projects <root>` → JSON array of `{key, name}`
- Also detect keys from git history (`git log --oneline -100` + `git branch -a`, pattern `[A-Z][A-Z0-9]+-\d+`)
- Present real Jira projects as AskUserQuestion options:
  - Sort: git-detected matches first
  - Format: "KEY — Project Name"
  - Include "Skip for now" option → sets `projectKey: ""`
  - User can type "Other" for a custom key
- If API returns no projects → fall back to text input with "Skip for now" option

### Step 6: Autonomy level

- **C (Cautious)** — default. Ask before every action.
- **B (Balanced)** — Show summaries, auto-proceed. `autoCreate: true`.
- **A (Autonomous)** — Act silently. `autoCreate: true`. Auto-create at confidence >= 0.65.

### Step 7: Accuracy (1-10)

Default: 5. Controls time rounding, idle threshold, and issue granularity per scaling table in section 2.4.

### Step 8: Worklog language

Options: English (default), Hebrew, Russian, or custom. Saved to `logLanguage`. Option to save as global default.

### Step 9: Additional settings

Show defaults for: branch pattern, commit pattern, time rounding, idle threshold, debug logging, auto-create. User can override.

### Step 10: Write config files

- `.claude/jira-autopilot.json` (project config)
- `.claude/jira-autopilot.local.json` (credentials)

### Step 11: Offer global save

Save credentials to `~/.claude/jira-autopilot.global.json` for reuse across projects.

### Step 12: Update `.gitignore`

Ensure these lines exist:
```
.claude/current-task.json
.claude/jira-session.json
.claude/jira-sessions/
.claude/jira-autopilot.local.json
.claude/jira-autopilot.declined
```

### Step 13: Remove declined marker

Delete `.claude/jira-autopilot.declined` if it exists.

### Step 14: Confirm

Show saved configuration summary: project key, connected user, autonomy, accuracy, debug status.

**Re-configuration:** If config exists, show current values and ask what to change.

## 5.2 `/jira-start` — Start Tracking a Task

**Allowed tools:** Bash, Write, Read, ToolSearch, MCP Atlassian tools
**Argument:** Issue key (e.g. `PROJ-42`) or summary text

### Pre-check

If a task is already active: ask to Switch (pause current) or Stop current first.

### Parse argument

- Matches `<PROJECT_KEY>-\d+` → link to existing issue
- Otherwise → create new issue

### Link to Existing Issue

1. Fetch issue via `jira_core.py get-issue <root> <key>` (REST, with MCP fallback)
2. Record `startTime` as current epoch seconds
3. Update session: add to `activeIssues` with `{summary, startTime, totalSeconds: 0, paused: false, autoApproveWorklogs: false}`, set `currentIssue`
4. Create/switch to feature branch: `git checkout -b feature/<KEY>-<slug>`. Never implement on `main`/`master`/`develop`.
5. Display confirmation with branch name

### Create New Issue

**Step 0 — Language:** Read `logLanguage`, translate summary if needed.

**Step 1 — Classify:** Call `jira_core.py classify-issue`. Returns `{type, confidence, signals}`.
- Autonomy C: present options (Task/Bug/Story)
- Autonomy B/A: auto-use classified type

**Step 2 — Parent selection:** Call `jira_core.py suggest-parent`. Returns `{sessionDefault, contextual, recent}`.
- Autonomy C: present parent options with "Create new parent", "No parent"
- Autonomy B/A: auto-select `sessionDefault` or best contextual match

**Step 3 — Bug-Story linking:** If type is Bug, offer to link to a Story (type "Relates").
- Autonomy C: present options
- Autonomy B/A: auto-link or skip

**Step 4 — Fields:**
- Assignee: cached `accountId`
- Labels: always include `jira-autopilot` + `defaultLabels`
- Component: from `componentMap` (match file paths) or `defaultComponent`
- Fix Version: from config or Jira API

**Step 5 — Create:** Call `jira_core.py create-issue`. Returns `{key, id}`.

**Step 6 — Post-creation:** Create Bug-Story link if applicable. Follow Link-to-Existing flow. Update `recentParents` (keep last 10).

## 5.3 `/jira-stop` — Stop Tracking and Log Time

**Allowed tools:** Bash, Read, Write, ToolSearch, MCP worklog tool

### Flow

1. Read session + config. If no active task → inform user.
2. **Build worklog:** `jira_core.py build-worklog <root> <key>`. Returns `{issueKey, seconds, summary, rawFacts, logLanguage}`.
3. **Enrich summary:** Write human-readable description in `logLanguage`. 2-4 sentences + optional file list. No raw commands/hashes.
4. **Calculate display time:** Round up to `timeRounding` increment. Show actual vs. rounded.
5. **Approval flow by autonomy:**

   **Autonomy C — 5-option approval:**
   1. Approve → post worklog
   2. Approve + go silent → sets `autoApproveWorklogs: true` for that issue, then post
   3. Edit summary → re-post with modified text
   4. Log to different issue → show issue selection, re-attribute
   5. Reject → "Keep for later" (`status: deferred`) or "Drop entirely" (`status: dropped`)

   **Autonomy B:** Show summary, then auto-approve.

   **Autonomy A:** Silent post, one-line confirmation.

6. **Post worklog:** `jira_core.py add-worklog` (REST first, MCP fallback).
7. **Post work summary comment** to Jira issue if work chunks exist.
8. **Update session:** Remove from `activeIssues`, set `currentIssue` to null or next active.
9. Display final summary.
10. **PR/branch cleanup:** If on feature branch:
    - C: 3 options (Open PR, Keep working, Switch to main)
    - B/A: Auto-suggest opening PR if unpushed commits exist

## 5.4 `/jira-status` — Show Active Tasks

**Allowed tools:** Bash

Displays formatted output:
- Project key, autonomy level, accuracy, language, debug status
- Current issue
- Active issues tree with elapsed time (live: `totalSeconds + (now - startTime)`)
- Work chunks by issue (count + tool call count)
- Pending worklogs count
- Activity buffer size
- Usage tips

## 5.5 `/jira-approve` — Review Pending Items

**Allowed tools:** Bash, Write, Read, ToolSearch, MCP Atlassian tools

Reviews three categories:

**Pending Issues** (`status: awaiting_approval`):
- Show: suggested summary, files changed, activity count
- Actions: Approve (create Jira issue), Link (to existing), Skip (discard)

**Pending/Deferred Worklogs** (`status: pending` or `deferred`):
- Enrich raw file-list summaries into human-readable text in `logLanguage`
- Show: issue, time, summary
- Actions: Approve (post via REST), Edit, Redirect to different issue, Drop

**Unattributed Work** (`status: unattributed`, `issueKey` is null):
- Show: time, files, activities
- Actions: Create new issue, Log to existing, Drop

## 5.6 `/jira-summary` — Today's Work Summary

**Allowed tools:** Bash, Read, ToolSearch, MCP comment tool

1. Read current session + archived sessions from `.claude/jira-sessions/` (filter today's date)
2. Aggregate: issues worked, time per issue, files per issue, activities per issue, pending/unattributed
3. Display formatted table with totals and per-issue detail tree
4. Optionally post as comment to each Jira issue (MCP first, REST fallback)

---

# 6. Core Business Logic

## 6.1 Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `MAX_WORKLOG_SECONDS` | 14400 (4 hours) | Sanity cap for a single worklog entry |
| `STALE_ISSUE_SECONDS` | 86400 (24 hours) | Threshold for pruning stale issues at session start |
| `MAX_LOG_SIZE` | 1,000,000 (1MB) | Log file rotation threshold |
| `READ_ONLY_TOOLS` | 16 tool names | Tools excluded from activity logging |
| `PLANNING_SKILL_PATTERNS` | `plan`, `brainstorm`, `spec`, `explore`, `research` | Skill name substrings that trigger planning mode |
| `PLANNING_IMPL_TOOLS` | `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | Tools that end planning mode |
| `BUG_SIGNALS` | `fix`, `bug`, `broken`, `crash`, `error`, `fail`, `regression`, `not working`, `issue with` | Keywords for bug classification |
| `TASK_SIGNALS` | `implement`, `add`, `create`, `build`, `refactor`, `update`, `improve`, `migrate`, `setup`, `configure` | Keywords for task classification |

## 6.2 Issue Classification

**Function:** `classify_issue(summary, context=None)`

**Algorithm:**
1. Count bug signals and task signals from lowercase summary
2. Context boosts (optional):
   - `new_files_created == 0 && files_edited > 0` → +1 bug score
   - `new_files_created > 0` → +1 task score
3. Classification:
   - Bug: bug_score >= 2, OR (bug_score > task_score AND bug_score >= 1)
   - Task: everything else
4. Confidence: `min(0.5 + score * 0.15, 0.95)`

**Returns:** `{type: "Bug"|"Task", confidence: float, signals: string[]}`

## 6.3 Summary Extraction

**Function:** `extract_summary_from_prompt(prompt)`

1. Take first sentence (split on `.!?\n`)
2. Strip noise words: `please`, `can you`, `could you`, `i need to`, `i want to`, `help me`, `let's`, `let me`
3. Capitalize first letter
4. Truncate to 80 characters

## 6.4 Duplicate Detection

**Function:** `_is_duplicate_issue(session, summary)`

1. Tokenize summary and each active issue summary (split on whitespace, lowercase)
2. Jaccard similarity: `|intersection| / |union|`
3. Return existing key if overlap >= 0.60, else None

## 6.5 Auto-Create Issue

**Function:** `_attempt_auto_create(root, summary, session, cfg)`

**Preconditions:**
- Autonomy B or A
- `autoCreate: true`
- Credentials available

**Algorithm:**
1. Clean summary via `extract_summary_from_prompt()`
2. Check for duplicates → return `{duplicate: existingKey}` if found
3. Classify issue → require confidence >= 0.65
4. Infer parent: `lastParentKey` → `currentIssue` → None
5. Create via `POST /rest/api/3/issue`
6. Update session: add to `activeIssues`, set `currentIssue`
7. Retroactively claim null chunks via `_claim_null_chunks()`

**Returns:** `{key, summary, type, parent, duplicate}`

## 6.6 Null Chunk Claiming

**Function:** `_claim_null_chunks(session, issue_key)`

Assigns all `issueKey: null` work chunks to the given issue. Calculates claimed time (`endTime - startTime - sum(idle gaps)`) and adds to `activeIssues[issue_key].totalSeconds`.

**Called from:** auto-create, branch detection at session start.

## 6.7 Worklog Building

**Function:** `build_worklog(root, issue_key)`

1. Collect work chunks matching `issue_key`. If sole active issue, also include `issueKey: null` chunks.
2. Aggregate: files (unique), commands (sanitized, unique), total activities, total seconds (endTime - startTime - idle gaps for each chunk)
3. Summary: file basenames (max 8, with `+N more` overflow). Fallback: `"Work on task"` / Hebrew equivalent.
4. Cap at `MAX_WORKLOG_SECONDS` (4h), set `capped: true` flag.

**Returns:** `{issueKey, seconds, summary, rawFacts: {files, commands, activityCount}, logLanguage, [capped]}`

## 6.8 Time Rounding

**Function:** `_round_seconds(seconds, rounding_minutes, accuracy)`

- High accuracy (8+): granularity = `max(rounding_minutes/15, 1)` minutes
- Low accuracy (1-3): granularity = `rounding_minutes * 2`
- Mid: granularity = `rounding_minutes`
- Always round UP: `ceil(seconds / granularity) * granularity`
- Minimum: one rounding increment (never zero)

## 6.9 Planning Time Tracking

- `_is_planning_skill(skill_name)` — returns true if name contains any planning pattern
- Planning starts on: `EnterPlanMode` tool or planning skill invocation
- Planning ends on: `ExitPlanMode` tool or first implementation tool (`Edit`/`Write`/`MultiEdit`/`NotebookEdit`)
- Planning time logged as worklog to: planning's `issueKey` → `currentIssue` → `lastParentKey`
- Minimum 60 seconds to be logged (micro-planning discarded)

## 6.10 Task Time Tracking

- `TaskCreate`: cache subject in `taskSubjects`
- `TaskUpdate` to `in_progress`: start tracking in `activeTasks`
- `TaskUpdate` to `completed`: stop tracking, log time if >= 60s as worklog to `currentIssue`
- Micro-tasks (< 60s) discarded

## 6.11 AI Enrichment

**Function:** `_enrich_summary_via_ai(raw_facts, language, api_key)`

- Model: `claude-haiku-4-5-20251001`
- Prompt: "Write a concise Jira worklog description (1-2 sentences, max 120 chars) in {language}"
- Input: file list, command list, activity count from `rawFacts`
- Timeout: 10 seconds
- Returns enriched text or empty string on failure

**Wrapper:** `_maybe_enrich_worklog_summary(root, raw_facts, fallback)` — checks for `anthropicApiKey` in credentials, returns AI text or fallback.

## 6.12 Worklog Posting

**Function:** `post_worklog_to_jira(base_url, email, api_token, issue_key, seconds, comment, language)`

- Endpoint: `POST /rest/api/3/issue/{key}/worklog`
- Auth: Basic (base64 `email:api_token`)
- Body: `{timeSpentSeconds, comment}` where comment is ADF format
- Fallback comment when empty: `"Work on task (Nm)"` / `"עבודה על המשימה (N דקות)"` for Hebrew
- Timeout: 15 seconds
- Returns: boolean (success/failure)

**ADF conversion (`_text_to_adf`):**
- Converts plain text to `{version: 1, type: "doc", content: [{type: "paragraph", content: [{type: "text", text: "..."}]}]}`
- Skips blank lines (prevents empty paragraph nodes)
- Empty input gets em-dash placeholder `"—"`

## 6.13 Project Fetching

**Function:** `jira_get_projects(root)`

- Endpoint: `GET /rest/api/3/project/search?maxResults=50&orderBy=key`
- Auth: Basic (same as worklog posting)
- Returns: `[{key: "PROJ", name: "My Project"}, ...]` or `[]` on failure
- Used by: auto-setup validation, `/jira-setup` command

---

# 7. CLI Interface

## 7.1 Command Dispatcher

Entry point: `python3 jira_core.py <command> [args...]`

| Command | Function | Arguments | Output |
|---------|----------|-----------|--------|
| `session-start` | `cmd_session_start` | `<root>` | JSON status or empty |
| `log-activity` | `cmd_log_activity` | `<root>` (stdin: tool JSON) | Empty |
| `drain-buffer` | `cmd_drain_buffer` | `<root>` | JSON context info |
| `session-end` | `cmd_session_end` | `<root>` | Empty |
| `post-worklogs` | `cmd_post_worklogs` | `<root>` | Empty |
| `classify-issue` | `cmd_classify_issue` | `<root> <summary>` | JSON `{type, confidence, signals}` |
| `auto-create-issue` | `cmd_auto_create_issue` | `<root> <prompt>` | JSON `{key, summary, type, parent, duplicate}` |
| `suggest-parent` | `cmd_suggest_parent` | `<root>` | JSON `{sessionDefault, contextual, recent}` |
| `build-worklog` | `cmd_build_worklog` | `<root> <issueKey>` | JSON worklog |
| `debug-log` | `cmd_debug_log` | `<root> [message]` | Empty |
| `create-issue` | `cmd_create_issue` | `<root> <json>` | JSON `{key, id}` |
| `get-issue` | `cmd_get_issue` | `<root> <key>` | JSON issue data |
| `add-worklog` | `cmd_add_worklog` | `<root> <key> <seconds> <comment>` | Success/failure |
| `get-projects` | `cmd_get_projects` | `<root>` | JSON `[{key, name}, ...]` |

---

# 8. REST API Endpoints Used

## 8.1 Jira Cloud REST API v3

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/rest/api/3/myself` | Test connectivity, get accountId |
| `GET` | `/rest/api/3/project/search` | Fetch accessible projects |
| `GET` | `/rest/api/3/issue/{key}` | Fetch issue details |
| `POST` | `/rest/api/3/issue` | Create issue |
| `POST` | `/rest/api/3/issue/{key}/worklog` | Add worklog entry |
| `POST` | `/rest/api/3/issue/{key}/comment` | Add issue comment |
| `GET` | `/rest/api/3/search?jql=...` | Search for parent issues (Epics/Stories) |
| `POST` | `/rest/api/3/issueLink` | Create issue link (Bug→Story) |
| `GET` | `/rest/api/3/project/{key}/versions` | Get unreleased fix versions |
| `GET` | `{baseUrl}/_edge/tenant_info` | Get Jira Cloud ID |

**Authentication:** Basic auth — `Authorization: Basic base64(email:apiToken)`

**Content-Type:** `application/json` for all requests

## 8.2 Anthropic API (Optional)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `https://api.anthropic.com/v1/messages` | AI-enriched worklog summaries |

**Authentication:** `x-api-key: <anthropicApiKey>`

**Model:** `claude-haiku-4-5-20251001`

---

# 9. Error Handling

| Scenario | Strategy |
|----------|----------|
| Corrupt session JSON | `load_session` catches `JSONDecodeError`/`ValueError`, returns `{}`, logs error |
| Concurrent hook writes | Atomic writes via `tempfile.mkstemp()` + `os.replace()` |
| Jira API failures | All REST calls wrapped in try/except for `HTTPError` and generic `Exception`. Log to API log. Return `False`/`[]`. |
| Missing credentials | Functions check required fields early, return silently or with error message |
| Git failures | `subprocess.run` with `timeout=5`, catch `SubprocessError`/`FileNotFoundError` |
| Hooks never block | `stop.sh` always exits 0. `session-end.sh` catches errors gracefully. |
| Worklog sanity cap | 4-hour maximum prevents inflated entries |
| Stale issue pruning | Issues > 24h with zero work auto-removed at session start |
| Ghost issue pruning | Paused issues with zero activity removed at session end |
| Credential sanitization | Tokens redacted from session state (retroactive + inline) via regex patterns |
| Log rotation | Both debug and API logs rotate at 1MB with single `.log.1` backup |
| Double-posting prevention | Work chunks cleared after building worklogs at session end |

---

# 10. Credential Security

1. **Never committed:** `jira-autopilot.local.json` is gitignored
2. **Never displayed:** API token shown only during initial setup entry
3. **Sanitized from state:** Regex patterns redact tokens from session data:
   - `ATATT3x[A-Za-z0-9_/+=.-]+` → `[REDACTED_TOKEN]`
   - `Bearer [A-Za-z0-9_/+=.-]+` → `Bearer [REDACTED]`
   - `Basic [A-Za-z0-9_/+=]+` → `Basic [REDACTED]`
   - `-u [^:]+:[^ ]+` → `-u [REDACTED]`
   - `"apiToken"\s*:\s*"[^"]+"` → `"apiToken": "[REDACTED]"`
4. **Gitignore enforced:** Setup step ensures `.claude/jira-autopilot.local.json` is listed

---

# 11. Testing Requirements

## 11.1 Test Structure

Tests use `pytest` with `tmp_path` fixtures for isolated file operations. Test fixtures redirect debug and API logs to temp directories via `conftest.py`.

## 11.2 Required Test Coverage

| Area | Key Behaviors to Test |
|------|----------------------|
| Config loading | Missing files return `{}`, credential fallback chain |
| Session start | New session creation, existing session preservation, stale issue cleanup, branch detection, migration |
| Activity logging | Issue stamping, read-only tool skipping, `.claude/` skip, credential sanitization, planning detection |
| Buffer drain | Idle gap splitting, context switch detection, issue key splitting, empty buffer handling |
| Issue classification | Bug signals, task signals, ambiguous inputs, context boosts |
| Worklog building | File summary generation, idle gap subtraction, sanity cap (4h), null chunk attribution |
| Session end | Pending worklogs, time rounding, archival, multiple issues, double-posting prevention |
| Worklog posting | HTTP success (201), HTTP error handling, missing credentials |
| Auto-create | Autonomy C rejection, autoCreate false, low confidence, duplicate detection, session update |
| Null chunk claiming | Assignment, time calculation with idle gaps, missing active issue |
| Planning tracking | Skill detection, enter/exit plan mode, micro-planning skip |
| Task tracking | Start/complete lifecycle, micro-task skip |
| Time rounding | Zero seconds, high/low/mid accuracy |
| Duplicate detection | High/low overlap thresholds, exact match, empty inputs |
| Project fetching | Success, missing credentials, HTTP error, network error |
| Auto-setup validation | Validated key used, phantom key becomes empty, API failure fallback |
| Atomic session writes | Roundtrip integrity, no temp file leaks |
| Log rotation | File rotation at 1MB threshold |

---

# 12. Statusline Integration

**Script:** `statusline-command.sh`

Reads JSON from stdin (Claude Code statusline protocol) and outputs colorized status showing:
- Current Jira issue key + elapsed time
- `[auto]` indicator for autonomy A
- Multi-issue count (if > 1 active)
- Pending worklogs count
- Plugin version
- Planning mode indicator
- When not configured: "Jira Autopilot not set" (red)
- When configured but no session: "KEY ready"

---

# 13. Legacy REST Client — `jira-rest.sh`

Bash + curl based client as fallback for shell-only contexts:

| Function | Endpoint | Notes |
|----------|----------|-------|
| `jira_load_creds` | — | Load creds with project→global fallback |
| `jira_test_connection` | `GET /myself` | Test connectivity |
| `jira_get_issue` | `GET /issue/{key}` | Fetch issue |
| `jira_create_issue` | `POST /issue` | Create (Task type only) |
| `jira_log_time` | `POST /issue/{key}/worklog` | Log time (no comment) |
| `jira_log_time_with_comment` | `POST /issue/{key}/worklog` | Log time with ADF comment |
| `jira_add_comment` | `POST /issue/{key}/comment` | Add comment |
| `jira_search_parents` | `GET /search?jql=...` | Search Epic/Story parents |
| `jira_link_issues` | `POST /issueLink` | Create issue link |
| `jira_get_versions` | `GET /project/{key}/versions` | Get unreleased versions |
| `jira_get_myself` | `GET /myself` | Get current user |
| `jira_get_cloud_id` | `GET {baseUrl}/_edge/tenant_info` | Get Cloud ID |

All use `_jira_curl` helper that appends HTTP status code to response for parsing.

---

# 14. Shell Helpers — `helpers.sh`

| Function | Purpose |
|----------|---------|
| `find_project_root` | Trust `$CLAUDE_PROJECT_DIR`, else walk up from CWD to find `.git` |
| `_migrate_config_names` | Rename `jira-tracker.*` → `jira-autopilot.*` files |
| `json_get` | Read JSON value via `python3 -c` |
| `json_get_nested` | Read nested JSON value |
| `session_update` | Atomic session state update |
| `is_enabled` | Check config exists and `enabled: true` |
| `extract_issue_from_branch` | Extract issue key from git branch |
| `session_file` | Returns `$ROOT/.claude/jira-session.json` path |
| `init_session` | Create fresh session file |
| `load_cred_field` | Load credential with project→global fallback |
| `detect_project_key_from_git` | Scan git log + branches for `[A-Z][A-Z0-9]+-\d+` patterns |

---

# 15. Implementation Notes

## 15.1 Design Principles

1. **No external dependencies** — Only Python 3 stdlib and standard macOS CLI tools
2. **MCP-first, REST-fallback** — Slash commands try Atlassian MCP tools first, fall back to `urllib`/`curl` REST
3. **REST-first in hooks** — `jira_core.py` uses `urllib.request` (no MCP context in hooks)
4. **Multi-issue tracking** — Session supports multiple active issues simultaneously
5. **Always-on monitoring** — Tool activity captured even without an active Jira issue
6. **Retroactive attribution** — Orphaned work chunks are claimed when issues are created or detected
7. **Atomic state writes** — Prevent corruption from concurrent async hooks
8. **Credential security** — Tokens never committed, sanitized from state, never displayed after setup
9. **Graceful degradation** — Every API failure returns a safe default, never crashes the session

## 15.2 Python Module Structure

Single file (`jira_core.py`, ~2000 lines) containing:
- Constants and configuration
- Config/session load/save functions
- Debug and API logging
- Issue classification and summary extraction
- Duplicate detection
- Auto-create logic with null chunk claiming
- Branch and project key detection (with Jira validation)
- Autonomy resolution
- Activity logging with credential sanitization
- Buffer drain with idle gap and context switch detection
- Worklog building and time rounding
- Planning and task time tracking
- AI enrichment (optional)
- Worklog posting with ADF conversion
- Session end with archival
- CLI command dispatcher

## 15.3 Hook Shell Script Pattern

Each hook script follows the same pattern:
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/helpers.sh"
ROOT="$(find_project_root)"
# ... hook-specific logic
python3 "$SCRIPT_DIR/jira_core.py" <command> "$ROOT" [args...]
```

Output is JSON with optional `systemMessage` field that Claude Code injects into the conversation.
