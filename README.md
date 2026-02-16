# jira-tracker

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that automatically enforces Jira workflow — issue tracking, branch naming, and time logging — without relying on Claude's memory.

## Why

Adding Jira instructions to `CLAUDE.md` works until Claude forgets them. This plugin uses **hooks** and **commands** to make the workflow automatic:

- A **SessionStart hook** detects your active task from the git branch and starts a timer
- **Slash commands** create/link issues, log time, and show status
- Per-project **config files** store your Jira project key and Cloud ID

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- [Atlassian MCP server](https://www.npmjs.com/package/@anthropic/mcp-atlassian) configured in Claude Code settings
- A Jira Cloud project

## Installation

### Option 1: Clone to local plugins directory

```bash
git clone https://github.com/user/claude-code-jira-tracker.git ~/.claude/plugins/local/jira-tracker
```

### Option 2: Manual download

```bash
mkdir -p ~/.claude/plugins/local/jira-tracker
cd ~/.claude/plugins/local/jira-tracker
# Copy plugin files here
```

### Register the plugin

Add to `~/.claude/plugins/installed_plugins.json` inside the `"plugins"` object:

```json
"jira-tracker@local": [
  {
    "scope": "user",
    "installPath": "/Users/<you>/.claude/plugins/local/jira-tracker",
    "version": "1.0.0",
    "installedAt": "2026-01-01T00:00:00.000Z",
    "lastUpdated": "2026-01-01T00:00:00.000Z"
  }
]
```

Add to `~/.claude/settings.json` inside `"enabledPlugins"`:

```json
"jira-tracker@local": true
```

## Quick Start

### 1. Configure your project

Open Claude Code in your project directory and run:

```
/jira:setup
```

Claude will ask for your Jira project key (e.g., `MYPROJ`) and Atlassian Cloud ID, then create `.claude/jira-tracker.json` in your project root.

### 2. Start working on a task

**Link to an existing Jira issue:**
```
/jira:start MYPROJ-42
```

**Create a new issue and start tracking:**
```
/jira:start Add user export feature
```

This will:
- Create/fetch the Jira issue
- Start a timer
- Create a feature branch if needed (e.g., `feature/MYPROJ-42-add-user-export`)

### 3. Check your progress

```
/jira:status
```

Shows the active issue, branch, and elapsed time.

### 4. Finish and log time

```
/jira:stop
```

Calculates elapsed time, rounds up to the nearest 15 minutes, and logs a worklog to Jira.

## Automatic Task Detection

When you start a new Claude Code session, the **SessionStart hook** runs automatically:

1. Reads the current git branch name
2. If it matches the pattern (e.g., `feature/MYPROJ-42-description`), extracts the issue key
3. Starts a timer and shows: `🎯 Detected task MYPROJ-42 from branch. Timer started.`
4. If no task is detected: `⚠️ No Jira task detected. Run /jira:start to begin.`

No action needed from you — just work on a properly named branch and tracking happens automatically.

## Commands Reference

| Command | Description |
|---------|-------------|
| `/jira:setup` | Configure Jira tracking for the current project |
| `/jira:start <KEY-123>` | Link to existing issue and start timer |
| `/jira:start <summary>` | Create new Jira issue and start timer |
| `/jira:stop` | Log elapsed time to Jira and stop timer |
| `/jira:status` | Show current task, branch, and elapsed time |

## Configuration

### Project config (committed, shared with team)

`<project-root>/.claude/jira-tracker.json`:

```json
{
  "projectKey": "MYPROJ",
  "cloudId": "your-atlassian-cloud-id",
  "enabled": true,
  "branchPattern": "^(?:feature|fix|hotfix|chore|docs)/({key}-\\d+)",
  "commitPattern": "{key}-\\d+:",
  "timeRounding": 15
}
```

| Field | Description |
|-------|-------------|
| `projectKey` | Jira project key (e.g., `MYPROJ`) |
| `cloudId` | Atlassian Cloud ID (find it in your Jira URL or via MCP) |
| `enabled` | Enable/disable tracking for this project |
| `branchPattern` | Regex to extract issue key from branch name. `{key}` is replaced with `projectKey` |
| `commitPattern` | Expected pattern in commit messages. `{key}` is replaced with `projectKey` |
| `timeRounding` | Round logged time up to nearest N minutes (default: 15) |

### Local overrides (gitignored, per-developer)

`<project-root>/.claude/jira-tracker.local.json`:

```json
{
  "enabled": false
}
```

Use this to disable tracking on your machine without affecting teammates.

### Runtime state (gitignored, auto-managed)

`<project-root>/.claude/current-task.json`:

```json
{
  "issueKey": "MYPROJ-42",
  "summary": "Add user export feature",
  "startTime": 1708100000,
  "branch": "feature/MYPROJ-42-add-user-export"
}
```

Created automatically by `/jira:start` or the session hook. Deleted by `/jira:stop`.

## Time Rounding

Logged time is always rounded **up** to the nearest increment (default 15 minutes):

| Actual elapsed | Logged as |
|---------------|-----------|
| 1–15 min | `15m` |
| 16–30 min | `30m` |
| 31–45 min | `45m` |
| 46–60 min | `1h` |
| 61–90 min | `1h 30m` |
| 91–120 min | `2h` |

## Plugin Structure

```
jira-tracker/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── commands/
│   ├── jira-setup.md            # /jira:setup command
│   ├── jira-start.md            # /jira:start command
│   ├── jira-stop.md             # /jira:stop command
│   └── jira-status.md           # /jira:status command
├── hooks/
│   └── hooks.json               # SessionStart hook definition
├── hooks-handlers/
│   ├── session-start-check.sh   # Task detection script
│   └── helpers.sh               # Shared shell utilities
└── README.md
```

## Troubleshooting

**"Jira tracking not configured"** — Run `/jira:setup` in your project directory.

**Hook doesn't fire on session start** — Verify the plugin is registered in both `installed_plugins.json` and `settings.json`. Restart Claude Code.

**"No Jira task detected"** — Either run `/jira:start` manually, or name your branch with the issue key: `feature/MYPROJ-42-description`.

**Time not logging** — Ensure the Atlassian MCP server is configured in `~/.claude/settings.json` under `mcpServers`.

## License

MIT
