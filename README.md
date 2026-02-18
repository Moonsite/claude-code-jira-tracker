# moonsite-claude-extensions

A collection of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) extensions by [Moonsite](https://github.com/Moonsite) — plugins, skills, and hooks for supercharging your Claude Code workflow.

## Extensions

### Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [jira-autopilot](plugins/jira-autopilot/) | Autonomous Jira work tracking, issue creation, and time logging | 3.0.0 |

### Skills

_Coming soon._

### Hooks

_Coming soon._

---

## jira-autopilot

Automatically tracks, documents, and logs your work to Jira. Every task done in Claude Code gets captured — files changed, time spent, work summaries — and posted to your Jira board with minimal manual intervention.

### Features

- **5 lifecycle hooks** track your work in real-time (tool activity, time, file changes)
- **6 slash commands** for setup, tracking, approvals, and daily summaries
- **3 autonomy levels** (C: confirm, B: auto-proceed, A: fully silent)
- **Accuracy parameter** (1-10) controlling time rounding and context switch sensitivity
- **Multi-issue tracking** with automatic time allocation
- **Auto-classification** of issue types (Bug vs Task) from summary text
- **Parent issue selection** with contextual Jira search
- **REST API fallback** when Atlassian MCP tools aren't available

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- A Jira Cloud project
- Jira API token ([create one here](https://id.atlassian.com/manage-profile/security/api-tokens))
- Optional: [Atlassian MCP server](https://www.npmjs.com/package/@anthropic/mcp-atlassian) for enhanced functionality

### Installation

```bash
git clone https://github.com/Moonsite/moonsite-claude-extensions.git ~/.claude/plugins/local/jira-autopilot
```

Register in `~/.claude/plugins/installed_plugins.json`:

```json
"jira-autopilot@local": [
  {
    "scope": "user",
    "installPath": "/Users/<you>/.claude/plugins/local/jira-autopilot",
    "version": "3.0.0",
    "installedAt": "2026-01-01T00:00:00.000Z",
    "lastUpdated": "2026-01-01T00:00:00.000Z"
  }
]
```

Enable in `~/.claude/settings.json`:

```json
"jira-autopilot@local": true
```

### Quick Start

```
/jira-setup                          # Configure Jira connection
/jira-start PROJ-42                  # Track existing issue
/jira-start Fix login redirect       # Create new issue + track
/jira-status                         # Show active issues + time
/jira-stop                           # Log time + work summary
/jira-summary                        # Today's aggregate report
```

### Commands

| Command | Description |
|---------|-------------|
| `/jira-setup` | Configure Jira tracking with guided setup wizard |
| `/jira-start <KEY-123>` | Link to existing issue and start timer |
| `/jira-start <summary>` | Create new Jira issue and start timer |
| `/jira-stop` | Log elapsed time and work summary to Jira |
| `/jira-status` | Show all active issues with time breakdown |
| `/jira-approve` | Review untracked work and create/link Jira issues |
| `/jira-summary` | Show today's aggregated work summary |

### Configuration

**Project config** (committed): `.claude/jira-autopilot.json`

| Field | Description | Default |
|-------|-------------|---------|
| `projectKey` | Jira project key (e.g., `MYPROJ`) | — |
| `cloudId` | Atlassian Cloud ID (auto-fetched) | — |
| `enabled` | Enable/disable tracking | `true` |
| `autonomyLevel` | `C` (confirm), `B` (auto-proceed), `A` (silent) | `C` |
| `accuracy` | 1-10 scale for time/context sensitivity | `5` |
| `idleThreshold` | Minutes of inactivity before idle detection | `15` |
| `branchPattern` | Regex to extract issue key from branch | `^(?:feature\|fix\|...)/{key}-\\d+` |
| `commitPattern` | Expected pattern in commit messages | `{key}-\\d+:` |
| `debugLog` | Enable debug logging to file | `false` |

**Credentials** (gitignored): `.claude/jira-autopilot.local.json`

```json
{
  "email": "you@company.com",
  "apiToken": "your-api-token",
  "baseUrl": "https://company.atlassian.net"
}
```

**Global credentials** (optional): `~/.claude/jira-autopilot.global.json` — shared across all projects.

### Documentation

- [Design spec](docs/plans/2026-02-18-jira-autopilot-autonomous-logging-design.md)
- [Implementation plan](docs/plans/2026-02-18-jira-autopilot-implementation.md)
- [Manual test plan](docs/plans/2026-02-18-jira-autopilot-manual-test-plan.md)

---

## Repository Structure

```
moonsite-claude-extensions/
├── .claude-plugin/
│   └── marketplace.json         # Marketplace manifest
├── plugins/
│   └── jira-autopilot/          # Jira autopilot plugin
├── skills/                      # (future skills)
├── hooks/                       # (future standalone hooks)
├── docs/
│   └── plans/                   # Design docs and test plans
├── CLAUDE.md                    # Claude Code instructions
└── README.md
```

## License

MIT
