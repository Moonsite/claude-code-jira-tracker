# Jira Autopilot — Manual Test Plan

**Date:** 2026-02-18
**Tester:** Human
**Prerequisite:** Install the plugin via `/plugin` in a repo with `.claude/jira-autopilot.json` configured.

---

## Test 1: Fresh Setup (`/jira-setup`)

**Goal:** Verify the full setup wizard works with new features.

**Steps:**
1. Remove existing config: `rm .claude/jira-autopilot.json .claude/jira-autopilot.local.json`
2. Open a new Claude Code session in this repo
3. Run `/jira-autopilot:jira-setup`

**What to check:**
- [ ] Auto-detect project key from git history — should find `CLAUDEPLUG` from recent commits and offer it as a choice
- [ ] URL prompt — should ask for URL as free text, NOT suggest "anthropic.atlassian.net" or any specific domain
- [ ] Global credentials — should detect `~/.claude/jira-autopilot.global.json` and offer to reuse saved creds
- [ ] Autonomy level — should explain C/B/A modes and let you pick (default C)
- [ ] Accuracy — should explain 1-10 scale with examples and let you pick (default 5)
- [ ] Debug log — should ask about enabling debug logging
- [ ] Idle threshold — should show default (15 min) and let you change
- [ ] accountId — after connectivity test, should cache your Jira accountId in local config
- [ ] Config files written correctly — check `.claude/jira-autopilot.json` has new fields: `autonomyLevel`, `accuracy`, `debugLog`, `idleThreshold`
- [ ] Offer to save globally — should ask to write `~/.claude/jira-autopilot.global.json`

---

## Test 2: Start Tracking — Existing Issue (`/jira-start`)

**Goal:** Verify linking to an existing Jira issue works.

**Prompt:**
```
/jira-autopilot:jira-start CLAUDEPLUG-1
```

**What to check:**
- [ ] Fetches issue summary from Jira
- [ ] Sets `currentIssue` to `CLAUDEPLUG-1` in session state
- [ ] Shows "Started tracking CLAUDEPLUG-1: <summary>. Timer running."
- [ ] Offers to create a feature branch if not on one

---

## Test 3: Start Tracking — New Issue with Classification (`/jira-start`)

**Goal:** Verify new issue creation with type classification, parent selection, and auto-assign.

**Prompt:**
```
/jira-autopilot:jira-start Fix login redirect when session expires
```

**What to check:**
- [ ] **Type classification** — should suggest "Bug" (contains "fix") and ask you to confirm/change (autonomy C)
- [ ] **Parent selection** — should show:
  - Suggested parents (Epics/Stories from Jira matching "login" or "session")
  - Recent parents (if any from session history)
  - Options: enter key, create new parent, no parent
- [ ] **Auto-assign** — issue should be assigned to you
- [ ] **Labels** — issue should have `jira-autopilot` label
- [ ] **Story linking** — since type is Bug, should ask to link to a Story

Try again with a Task-like summary:
```
/jira-autopilot:jira-start Add dark mode support
```
- [ ] Should classify as "Task" (contains "add")
- [ ] Should NOT trigger story linking flow

---

## Test 4: Context Switch Detection

**Goal:** Verify the plugin detects when you switch topics mid-session.

**Steps:**
1. Start an issue: `/jira-autopilot:jira-start CLAUDEPLUG-1`
2. Make a few edits in one area:
```
Edit the file plugins/jira-autopilot/hooks-handlers/helpers.sh — add a comment at the top
Edit the file plugins/jira-autopilot/hooks-handlers/jira-rest.sh — add a comment at the top
```
3. Now switch to a completely different area:
```
Edit the file plugins/jira-autopilot/commands/jira-setup.md — add a comment at the top
Edit the file plugins/jira-autopilot/commands/jira-start.md — add a comment at the top
```
4. Say: "I'm done for now"

**What to check:**
- [ ] Stop hook fires and analyzes activity buffer
- [ ] Should detect directory cluster shift (hooks-handlers/ → commands/)
- [ ] Should flag unattributed chunk and ask: log to CLAUDEPLUG-1 or create new issue?
- [ ] Check debug log: `cat ~/.claude/jira-autopilot-debug.log` — should have `[context-switch]` entry

---

## Test 5: Idle Detection

**Goal:** Verify idle gaps are detected and excluded from time.

**Steps:**
1. Start tracking: `/jira-autopilot:jira-start CLAUDEPLUG-1`
2. Make an edit:
```
Edit plugins/jira-autopilot/hooks-handlers/helpers.sh — add a comment
```
3. **Wait 20+ minutes** (or set `idleThreshold` to 1 min in config for faster testing)
4. Make another edit:
```
Edit plugins/jira-autopilot/hooks-handlers/helpers.sh — add another comment
```
5. Run `/jira-autopilot:jira-stop`

**What to check:**
- [ ] Worklog time should NOT include the idle gap
- [ ] Debug log should show `[idle-detected]` entry with gap duration
- [ ] Worklog summary should reflect only active working time

**Shortcut for faster testing:** Before step 1, set idle threshold low:
```
Edit .claude/jira-autopilot.json and set "idleThreshold": 1
```

---

## Test 6: Worklog Approval Flow (`/jira-stop`)

**Goal:** Verify all 5 worklog approval options work.

**Steps:**
1. Start and do some work:
```
/jira-autopilot:jira-start CLAUDEPLUG-1
```
2. Make a few edits to any files
3. Run `/jira-autopilot:jira-stop`

**What to check:**
- [ ] Shows worklog summary (1-3 lines describing what you did)
- [ ] Shows 5 options: Approve / Approve+silent / Edit / Different issue / Reject

**Test each option** (repeat steps 1-3 for each):

### Option 1: Approve
- [ ] Posts worklog to Jira with summary text
- [ ] Check in Jira: issue should have a new worklog with time + description

### Option 2: Approve + silent
- [ ] Posts worklog
- [ ] Next time you stop this issue, it should auto-approve without asking

### Option 3: Edit
- [ ] Lets you type a replacement summary
- [ ] Posts the edited version

### Option 4: Different issue
- [ ] Shows active issues, recent issues, option to enter key
- [ ] Reattributes the worklog to the chosen issue

### Option 5: Reject
- [ ] Asks: "Keep for later?" or "Drop entirely?"
- [ ] "Keep": should appear as deferred in `/jira-autopilot:jira-status`
- [ ] "Drop": should be gone completely

---

## Test 7: Autonomy Level B

**Goal:** Verify auto-approve behavior.

**Steps:**
1. Set autonomy to B:
```
Edit .claude/jira-autopilot.json and set "autonomyLevel": "B"
```
2. Start a new session
3. Do some work and stop

**What to check:**
- [ ] Worklog summary is shown but auto-approves without waiting for input
- [ ] Issue creation (if triggered) shows summary and auto-proceeds

---

## Test 8: Autonomy Level A (Full Autopilot)

**Goal:** Verify fully silent mode.

**Steps:**
1. Set autonomy to A:
```
Edit .claude/jira-autopilot.json and set "autonomyLevel": "A"
```
2. Start a new session
3. Do some work and stop

**What to check:**
- [ ] Worklog posts silently with just a one-liner confirmation
- [ ] Issue creation (if triggered) happens silently with one-liner
- [ ] Type classification happens automatically without asking

---

## Test 9: Accuracy Parameter

**Goal:** Verify accuracy affects time rounding and sensitivity.

### Low accuracy (accuracy: 2)
1. Set `"accuracy": 2` in config
2. Work for ~10 min across a couple files
3. `/jira-autopilot:jira-stop`

- [ ] Time should round to 30-min increments
- [ ] Small context switches should be ignored

### High accuracy (accuracy: 9)
1. Set `"accuracy": 9` in config
2. Work for ~10 min
3. `/jira-autopilot:jira-stop`

- [ ] Time should round to 1-min increments
- [ ] Even small context switches should be flagged

---

## Test 10: Status and Summary Commands

**Prompts:**
```
/jira-autopilot:jira-status
```

**What to check:**
- [ ] Shows current issue, elapsed time, activities, files
- [ ] Shows autonomy level, accuracy, debug log status
- [ ] Shows pending worklogs count (if any deferred from Test 6)

```
/jira-autopilot:jira-summary
```

**What to check:**
- [ ] Aggregates today's sessions
- [ ] Shows time per issue in a table
- [ ] Includes deferred worklogs

---

## Test 11: Debug Log

**Goal:** Verify debug logging captures everything.

**Prompt:**
```
cat ~/.claude/jira-autopilot-debug.log
```

**What to check:**
- [ ] `[session-start]` entries with root and sessionId
- [ ] `[log-activity]` entries with tool, file, issueKey
- [ ] `[idle-detected]` entries (if idle occurred)
- [ ] `[context-switch]` entries (if context switch occurred)
- [ ] `[drain-buffer]` entries with chunk counts
- [ ] `[classify-issue]` entries with type and confidence
- [ ] `[worklog-post]` entries with issue key and seconds
- [ ] `[jira-api]` entries with HTTP method and response code

---

## Test 12: Backward Compatibility

**Goal:** Verify old config files are auto-migrated.

**Steps:**
1. Rename config files to old names:
```bash
mv .claude/jira-autopilot.json .claude/jira-tracker.json
mv .claude/jira-autopilot.local.json .claude/jira-tracker.local.json
```
2. Start a new Claude Code session

**What to check:**
- [ ] Session starts normally — hook auto-migrates config files
- [ ] `.claude/jira-autopilot.json` exists (renamed from jira-tracker.json)
- [ ] `.claude/jira-tracker.json` no longer exists
- [ ] Everything works as before

---

## Test 13: Multi-Issue Switching

**Goal:** Verify working on two issues in one session.

**Steps:**
1. Start first issue:
```
/jira-autopilot:jira-start CLAUDEPLUG-1
```
2. Make some edits
3. Switch to second issue:
```
/jira-autopilot:jira-start CLAUDEPLUG-2
```
4. Make some edits
5. Check status:
```
/jira-autopilot:jira-status
```
6. Stop all:
```
/jira-autopilot:jira-stop
```

**What to check:**
- [ ] Status shows both issues with separate time tracking
- [ ] CLAUDEPLUG-1 is paused when CLAUDEPLUG-2 starts
- [ ] Stop presents separate worklogs for each issue
- [ ] Each worklog has the correct time (no double-counting)

---

## Test 14: Disable Tracking

### Session disable
```
Tell Claude: "pause jira tracking for this session"
```
- [ ] Tracking pauses, no Jira calls
- [ ] Activities still recorded locally (silent tracking)
- [ ] "resume tracking" re-enables

### Day disable
```
Tell Claude: "disable jira tracking for today"
```
- [ ] Sets `disabledUntil` in local config
- [ ] Tomorrow it auto-re-enables

---

## Quick Smoke Test (5 minutes)

If you only have 5 minutes, run these:

1. `/jira-autopilot:jira-setup` — verify new fields appear (autonomy, accuracy)
2. `/jira-autopilot:jira-start Fix a small bug` — verify type=Bug suggested, parent selection shown
3. Edit 2-3 files
4. `/jira-autopilot:jira-stop` — verify worklog summary + 5-option flow
5. `/jira-autopilot:jira-status` — verify display
6. Check `~/.claude/jira-autopilot-debug.log` — verify entries exist
