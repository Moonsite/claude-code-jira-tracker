# Jira Autopilot — Lessons Learned

Technical findings, recommendations, and guidelines derived from developing the jira-autopilot plugin (v1.0 → v3.20.0).

---

## 1. Concurrency & File Safety

### Problem
Multiple Claude Code hooks (SessionStart, PostToolUse, Stop, SessionEnd) run concurrently and share JSON state files (`jira-session.json`, `jira-autopilot.json`). Early versions used plain `open()`/`write()` which caused:

- **Silent data loss** — two hooks read the same file, modify different keys, last writer wins.
- **Corrupt JSON** — partial writes visible to concurrent readers.
- **Empty files** — write truncates the file, process crashes before data is written.

### Root Cause
Python's `open("f", "w")` truncates immediately. If the process is interrupted between truncate and write, the file is empty.

### Solution: Atomic Writes
```
Write to temp file → fsync → os.replace(temp, target)
```

`os.replace()` is atomic on POSIX. The file is either fully old or fully new — never partial.

### Recommendation
- **Every** JSON state file write must use atomic write (tempfile + `os.replace`).
- Use file locking (`fcntl.flock`) for read-modify-write cycles on shared state.
- Never assume a file read will return valid JSON — always wrap in try/except.
- Test with concurrent hook invocations, not just sequential.

---

## 2. Credential Management

### Problem: Credential Leakage
Debug logs, error messages, and JSON dumps exposed API tokens in:
- `~/.claude/jira-autopilot-debug.log`
- stdout/stderr during hook execution
- Error tracebacks containing full config dicts

### Solution
- Centralized `sanitize_for_log()` function that masks `apiToken`, `email`, `password` fields.
- All `debug_log()` calls route through sanitization.
- Config dicts are sanitized before any string formatting.

### Problem: Credential Fallback Chain
Credentials can come from three sources with different precedence:
1. Local project config (`.claude/jira-autopilot.local.json`)
2. Global user config (`~/.claude/jira-autopilot.global.json`)
3. Environment variables (future)

Early code only checked local config. When local creds were missing, operations failed silently.

### Recommendation
- Always use the centralized `get_cred(root, key)` function which handles the fallback chain.
- Never read credential files directly — the fallback logic is non-trivial.
- Sanitize all credential data before logging, error messages, or user-facing output.
- Store secrets in `.local.json` (gitignored), never in `.json` (committed).
- Test credential functions with patched `GLOBAL_CONFIG_PATH` to avoid using real credentials in tests.

---

## 3. Shell Script ↔ Python Boundary

### Problem
The plugin started as pure shell scripts (`bash` + `jq`), then migrated core logic to Python. The boundary between shell and Python caused:

- **JSON parsing inconsistencies** — `jq` and `python3 -c "import json"` handle edge cases differently (unicode, null values, empty arrays).
- **Exit code confusion** — shell scripts check `$?` but Python's `sys.exit()` behavior differs from shell `exit`.
- **Quoting hell** — passing JSON through shell arguments requires careful escaping that broke on special characters in Jira issue titles.

### Solution
- Moved all JSON manipulation to Python (`jira_core.py`).
- Shell scripts became thin wrappers that call `python3 jira_core.py <command> <args>`.
- Python handles all data processing; shell only handles Claude Code hook lifecycle.

### Recommendation
- Keep shell scripts minimal — just the hook entry point and argument passing.
- All business logic, JSON parsing, and API calls should be in Python.
- Use `python3 -c` one-liners sparingly — they're hard to debug and test. Move any non-trivial logic to `jira_core.py`.
- Always use `json.dumps()` for output, never string concatenation.
- Test the Python CLI commands independently from the shell wrappers.

---

## 4. Session State Design

### Problem: State Schema Evolution
As features were added, the session state schema grew. Old state files from previous versions caused crashes when new code expected missing keys.

### Solution
- `_ensure_session_structure()` function that fills missing keys with defaults.
- Called at every session load, not just creation.
- Additive changes only — never remove keys from the schema without migration.

### Problem: Work Chunk Boundaries
Determining when one "work chunk" ends and another begins was unreliable:
- Fixed time thresholds missed context switches within the threshold.
- Tool-based heuristics (e.g., "Read after Write = new task") were fragile.
- Idle detection didn't account for developer thinking time vs. actual idle.

### Solution: Configurable Idle Threshold
- `idleThreshold` parameter (1-30 minutes) controlled via accuracy level.
- Activity gaps larger than threshold create a new chunk.
- Context switch detection uses tool pattern analysis as a secondary signal.

### Recommendation
- Always call `_ensure_session_structure()` after loading session state.
- Design state schemas to be forward-compatible — new keys with sensible defaults.
- Don't hard-code time thresholds — make them configurable and tied to accuracy level.
- Work chunk boundaries should use multiple signals (time gap + tool patterns), not just one.

---

## 5. Jira API Integration

### Problem: API Pagination
`GET /rest/api/3/project/search` and issue search endpoints return paginated results. Early code only read the first page, silently missing projects/issues.

### Problem: Rate Limiting
Burst API calls during SessionEnd (posting worklogs to multiple issues) occasionally hit Jira's rate limits, causing partial updates.

### Problem: Field Validation
Jira issue creation fails silently when:
- `project` key doesn't exist (returns 404, not a validation error).
- Required custom fields are missing (returns generic 400).
- `timeSpent` format is wrong (expects "1h 30m", not minutes).

### Solution
- Added pagination loop for project search (`startAt` + `maxResults`).
- Added retry with exponential backoff for rate-limited requests.
- Validate project key against real Jira projects before use (`jira_get_projects()`).
- Centralized time formatting in `format_jira_time()`.

### Recommendation
- Always paginate API responses — never assume a single page is complete.
- Implement retry with backoff for all write operations (worklogs, issue creation).
- Validate inputs (project key, issue type, time format) before API calls.
- Use `GET /rest/api/3/myself` as a connectivity test during setup.
- Cache project lists and issue types — they change rarely.
- The `timeSpent` field uses Jira notation (`"1h 30m"`), not ISO 8601 duration.

---

## 6. Git Integration

### Problem: Phantom Project Keys
Auto-setup scanned git history (`git log`, `git branch -a`) for patterns like `PROJ-123` to detect the project key. This surfaced keys from:
- Forked repositories (upstream project keys).
- Old branches from other projects.
- Commit messages referencing external issues.

Users were suggested project keys that didn't exist in their Jira instance.

### Solution (v3.20.0)
- Fetch real projects from Jira via `jira_get_projects()`.
- Validate git-detected key against real project list.
- If no match, set `projectKey: ""` (monitoring mode) instead of using phantom key.
- In `/jira-setup`, present real Jira projects as options, sorted with git-matches first.

### Problem: Branch Pattern Matching
The default branch pattern `^(?:feature|fix|hotfix|chore|docs)/(KEY-\d+)` didn't match:
- Branches created by other tools (e.g., `user/KEY-123-description`).
- Branches without the prefix convention.
- Branches with nested paths (e.g., `feature/team/KEY-123`).

### Recommendation
- Never trust git-detected project keys without server-side validation.
- Branch patterns should be configurable and have a permissive fallback.
- Scan both local and remote branches, but weight local higher.
- Consider scanning the last N commits (not all history) to avoid stale references.

---

## 7. Hook Lifecycle Gotchas

### Problem: Async Hook Ordering
`PostToolUse` runs asynchronously (non-blocking). This means:
- Multiple PostToolUse invocations can overlap.
- PostToolUse from tool N might execute after PreToolUse for tool N+1.
- Session state reads in PostToolUse might see stale data.

### Problem: SessionEnd Timing
`SessionEnd` fires when the user exits Claude Code. At this point:
- Network might be unavailable (laptop lid closed).
- The process has limited time before termination.
- Partial API calls can leave Jira in an inconsistent state.

### Solution
- PostToolUse appends to an activity buffer file (append-only, no read-modify-write).
- Stop hook drains the buffer into work chunks (single writer).
- SessionEnd uses best-effort posting with timeout — logs failures for retry.
- Critical data (time tracking) is saved locally first, then synced to Jira.

### Recommendation
- Async hooks must use append-only patterns or file locking.
- Never rely on hook execution order — design for out-of-order delivery.
- SessionEnd should be idempotent — it might run multiple times or not at all.
- Save state locally first, sync to Jira as a separate step.
- Log all failed API calls for manual or automatic retry.

---

## 8. Testing Patterns

### Problem: Real Credentials in Tests
Tests that call `get_cred()` can accidentally use real credentials from `~/.claude/jira-autopilot.global.json`, causing:
- Tests that pass locally but fail in CI.
- Tests that make real API calls to production Jira.
- Flaky tests depending on developer's credential state.

### Solution
- Patch `jira_core.GLOBAL_CONFIG_PATH` to a non-existent path in all tests that touch credentials.
- Use `tmp_path` fixtures for all config file operations.
- Mock all HTTP calls with `unittest.mock.patch("urllib.request.urlopen")`.

### Problem: File System State Leakage
Tests that create/modify files in the real working directory leave artifacts that affect other tests.

### Solution
- All file operations use `tmp_path` (pytest fixture).
- Session state, config files, and log files are created in temp directories.
- Cleanup is automatic via pytest fixture teardown.

### Recommendation
- **Always** patch `GLOBAL_CONFIG_PATH` in tests that touch credentials.
- **Always** use `tmp_path` for file operations — never write to the real file system.
- Mock all network calls — tests must work offline.
- Test the CLI interface (`cmd_*` functions) in addition to the library functions.
- Test error paths (network failure, malformed JSON, missing files) — these are the most common production failures.

---

## 9. Configuration Design

### Problem: Config Proliferation
Configuration is spread across four files with overlapping keys:
1. `.claude/jira-autopilot.json` — project config (committed)
2. `.claude/jira-autopilot.local.json` — credentials (gitignored)
3. `~/.claude/jira-autopilot.global.json` — global credentials
4. `~/.claude/jira-session.json` — runtime state (gitignored)

Developers were confused about which file to edit and which values take precedence.

### Solution
- Clear documentation of the precedence chain: local > global > defaults.
- `get_cred()` handles the fallback transparently.
- `/jira-setup` writes to the correct files automatically.

### Recommendation
- Minimize the number of config files. Consider merging project config and local config with clear separation of committed vs. gitignored fields.
- Document the precedence chain in the setup flow.
- Validate config on load — catch invalid values early with clear error messages.
- Provide a `/jira-status`-style command that shows the effective configuration from all sources.

---

## 10. Autonomy Level Design

### Problem: User Trust Calibration
The three autonomy levels (Cautious/Balanced/Autonomous) affected multiple behaviors:
- Issue creation (ask vs. auto-create)
- Time logging (confirm vs. auto-post)
- Work summaries (review vs. auto-post)

Mapping a single setting to many behaviors was confusing — users wanted fine-grained control.

### Recommendation
- Keep the simple C/B/A levels as presets for onboarding.
- Allow per-action overrides for advanced users (e.g., `autoCreate: true` but `autoLogTime: false`).
- Default to Cautious — it's safer to ask too much than to act without permission.
- Log all automated actions clearly so users can audit what happened.

---

## 11. Debug Logging

### Problem
Without debug logging, diagnosing production issues required reproducing the exact scenario. With debug logging enabled by default, log files grew large and contained sensitive data.

### Solution
- `debug_log()` function that writes to `~/.claude/jira-autopilot-debug.log`.
- Enabled by default during development (`debugLog: true` in config).
- All log entries pass through `sanitize_for_log()`.
- Log rotation not implemented yet — manual cleanup needed.

### Recommendation
- Keep debug logging enabled by default during early adoption.
- Implement log rotation (e.g., max 10MB, keep last 3 files).
- Include structured metadata in log entries (timestamp, hook name, session ID).
- Never log raw API responses — they may contain sensitive user data.

---

## 12. Recurring Patterns Summary

| Pattern | Occurrences | Root Cause | Fix |
|---------|-------------|------------|-----|
| Silent data loss from concurrent writes | 5 bugs | Non-atomic file operations | Atomic writes (tempfile + os.replace) |
| Credential leakage in logs/errors | 4 bugs | No centralized sanitization | `sanitize_for_log()` on all output |
| Config key missing → crash | 4 bugs | Schema evolution without migration | `_ensure_session_structure()` on every load |
| Git-detected values not validated | 3 bugs | Trusting local data over server data | Server-side validation before use |
| Tests using real credentials | 3 bugs | Global config fallback in tests | Patch `GLOBAL_CONFIG_PATH` in tests |
| Shell/Python boundary issues | 3 bugs | JSON through shell arguments | Move all logic to Python |
| API pagination ignored | 2 bugs | Only reading first page | Pagination loop for all list endpoints |
| Time format mismatches | 2 bugs | Jira's non-standard duration format | Centralized `format_jira_time()` |

---

## 13. Key Architectural Recommendations for Reimplementation

1. **Python-first, shell-minimal.** Shell scripts should only be hook entry points (< 10 lines). All logic in Python.

2. **Atomic writes everywhere.** Any file that multiple hooks can access must use atomic write patterns.

3. **Validate against Jira, not git.** Git history is unreliable for project keys, issue types, and user data. Always validate against the Jira API.

4. **Local-first, sync-later.** Save all tracking data locally first. Sync to Jira as a separate, retryable operation. Never lose tracking data because an API call failed.

5. **Test without network.** All tests must work offline. Mock every HTTP call. Patch global config paths.

6. **Sanitize all output.** Every log line, error message, and user-facing string must go through credential sanitization.

7. **Design for concurrent hooks.** Assume any hook can run at any time, in any order, overlapping with other hooks. Use append-only files or locking.

8. **Schema evolution = additive only.** Never remove keys from state files. Add new keys with defaults. Always call structure-ensuring functions on load.

9. **Configurable thresholds.** Don't hard-code time values, confidence thresholds, or limits. Tie them to the accuracy parameter.

10. **Idempotent operations.** SessionEnd might run twice. Worklog posting might retry. Every operation should be safe to repeat.
