# Jira Autopilot — Product Requirements & User Stories

**Author:** Boris Sigalov
**Date:** 28/02/2026
**Version:** 1.0
**Audience:** AI agent reimplementing the plugin from scratch

---

## Mission Statement

**Jira Autopilot** is an intelligent Claude Code plugin that solves a new problem born from the AI coding era: developers now work across multiple terminals simultaneously, each running Claude Code on a different feature or bug fix. A single developer can have 5+ parallel sessions, effectively multiplying their output — but traditional time tracking tools can't capture this reality.

The plugin runs inside each Claude Code session and smartly tracks two distinct contributors' time: the **developer's active time** interacting with the terminal, and **Claude's autonomous working time** on the task. Optionally, these can be logged as separate worklogs under separate Jira users — Claude gets its own seat on the team, giving managers real visibility into how much work the AI is doing versus the human, per issue.

It intelligently observes every tool action (file edits, commands, test runs), groups them into meaningful work chunks, and attributes them to the correct Jira issue. Multiple issues can be tracked concurrently across sessions. When a developer switches between terminals, each session independently and smartly captures and logs its own work.

At session end — or on demand — the plugin calculates total time for both the developer and Claude, generates an intelligent human-readable summary of what was accomplished, and posts worklogs to Jira. The plugin operates at three autonomy levels: ask before every action (cautious), show and auto-proceed (balanced), or work silently (autonomous). Developers just code across their terminals, and Jira stays up to date — with smart, accurate attribution for both human and AI contributions.

---

## Feature Map

| # | Feature | Trigger | Commands |
|---|---------|---------|----------|
| 1 | Global-first setup with auto-activation | First run / on demand | `/jira-setup` |
| 2 | Automatic session tracking | Every session start | — |
| 3 | Intelligent activity capture | Every tool action | — |
| 4 | Smart work chunking | Continuous / on stop | — |
| 5 | Manual issue tracking | Developer command | `/start-work`, `/report-work` |
| 6 | Automatic issue detection and creation | Developer prompt analysis | — |
| 7 | Intelligent worklog generation | Session end / stop / flush | — |
| 8 | Periodic worklog flushing | Timer-based | — |
| 9 | Retroactive work attribution | Issue creation / linking | — |
| 10 | Review and approve pending work | Developer command | `/approve-work` |
| 11 | Daily work summary | Developer command | `/work-summary` |
| 12 | Work status display | Developer command | `/work-status` |
| 13 | Git commit integration | Before git commit | — |
| 14 | Separate dev/Claude time logging | Optional config | — |
| 15 | Credential security and data protection | Always active | — |
| 16 | Resilience and error handling | Always active | — |

---

# Epic 1: Global-First Setup & Configuration

## US-1.1: One-Time Global Setup

**As a** developer using Claude Code,
**I want** to configure my Jira connection once at the machine level,
**so that** the plugin works automatically in every project without repeated setup.

**Acceptance Criteria:**
1. Running `/jira-setup` for the first time walks me through: Jira URL, email, API token, connection test, autonomy level, accuracy, and worklog language.
2. Credentials are saved globally on my machine (not per-project).
3. After global setup, the plugin auto-activates in every new Claude Code session without requiring `/jira-setup` again.
4. The connection is tested before completing setup — setup cannot finish with invalid credentials.

## US-1.2: Automatic Project Key Detection

**As a** developer starting work in a new repository,
**I want** the plugin to intelligently detect which Jira project this repo belongs to,
**so that** I don't have to configure it manually for each project.

**Acceptance Criteria:**
1. The plugin scans git commit history and branch names for Jira issue key patterns.
2. Detected keys are validated against real Jira projects accessible to the user.
3. If a valid match is found, it is used automatically.
4. If no valid match is found, the project key is left empty and work is still monitored (unattributed mode).
5. Phantom keys from forked repos or old references are never suggested.

## US-1.3: Per-Project Configuration Override

**As a** developer working on a project with different needs,
**I want** to optionally override global settings for a specific project,
**so that** I can use different autonomy, accuracy, or project key per repo.

**Acceptance Criteria:**
1. Running `/jira-setup` in a project with existing global config offers to override specific settings.
2. Per-project settings take priority over global defaults.
3. Credentials fall back to global if not set per-project.

## US-1.4: Autonomy Level Selection

**As a** developer,
**I want** to choose how autonomous the plugin is,
**so that** I control the balance between convenience and oversight.

**Acceptance Criteria:**
1. Three levels are available: Cautious (ask before every action), Balanced (show and auto-proceed), Autonomous (act silently).
2. Cautious is the default.
3. Balanced and Autonomous enable automatic issue creation.
4. The level can be changed at any time via `/jira-setup`.

## US-1.5: Accuracy Setting

**As a** developer or manager,
**I want** to control how precisely time is tracked,
**so that** I can balance between granularity and noise.

**Acceptance Criteria:**
1. Accuracy is a scale from 1 to 10.
2. Low accuracy (1-3) produces coarser time entries, longer idle thresholds, and fewer issues per day.
3. High accuracy (8-10) produces fine-grained entries, shorter idle thresholds, and more issues per day.
4. Default is 5 (medium).

## US-1.6: Worklog Language

**As a** developer in a multilingual team,
**I want** to choose the language for worklog descriptions,
**so that** Jira entries are readable by my team.

**Acceptance Criteria:**
1. Supported languages include at minimum: English, Hebrew, Russian.
2. Custom language names are accepted.
3. The setting can be saved as a global default.
4. All generated worklog summaries and comments use the configured language.

## US-1.7: Plugin Disable Per-Project

**As a** developer,
**I want** to disable the plugin for a specific project,
**so that** it doesn't track work in repos where I don't want Jira integration.

**Acceptance Criteria:**
1. A developer can disable the plugin for a specific project.
2. A disabled plugin produces no side effects — no API calls, no state files, no messages.
3. The plugin can be re-enabled at any time.

## US-1.8: Reconfiguration

**As a** developer,
**I want** to change my settings after initial setup,
**so that** I can adjust as my workflow evolves.

**Acceptance Criteria:**
1. Running `/jira-setup` when already configured shows current values.
2. The developer can change any individual setting without re-entering everything.
3. Changed settings take effect immediately.

---

# Epic 2: Automatic Session Tracking

## US-2.1: Session Initialization

**As a** developer,
**I want** the plugin to start tracking automatically when a Claude Code session begins,
**so that** I never forget to log my work.

**Acceptance Criteria:**
1. Work tracking begins automatically at session start if global credentials exist.
2. No user interaction is required to start tracking.
3. The plugin displays a brief status message showing the current tracking state.

## US-2.2: Branch-Based Issue Detection

**As a** developer working on a feature branch,
**I want** the plugin to intelligently detect which Jira issue I'm working on from my branch name,
**so that** time is attributed to the right issue without me running any command.

**Acceptance Criteria:**
1. Branch names matching configurable patterns (e.g. `feature/PROJ-42-description`) are detected.
2. The detected issue is automatically set as the current active issue.
3. If the issue key is valid, tracking starts immediately.
4. Any work done before the issue was detected is retroactively attributed to it.

## US-2.3: Session State Persistence

**As a** developer,
**I want** my tracking state to survive session interruptions,
**so that** resuming a session doesn't lose my work context.

**Acceptance Criteria:**
1. If a session resumes with active issues from a previous session, they are preserved.
2. Time tracking continues from where it left off.
3. Active issues, work chunks, and pending worklogs are all preserved.

## US-2.4: Stale Issue Cleanup

**As a** developer,
**I want** old inactive issues to be automatically cleaned up,
**so that** my session state doesn't accumulate abandoned work.

**Acceptance Criteria:**
1. Issues idle for more than 24 hours with no logged work are automatically removed at session start.
2. Issues with existing work chunks are preserved regardless of age.
3. Cleanup happens silently without user interaction.

## US-2.5: Multi-Issue Concurrency

**As a** developer working on multiple things,
**I want** to track multiple Jira issues simultaneously within a single session,
**so that** switching between tasks doesn't require stopping and restarting.

**Acceptance Criteria:**
1. Multiple issues can be active at the same time.
2. One issue is designated as the "current" issue at any time.
3. Switching between issues is possible without losing tracking on any of them.

## US-2.6: Session Archival

**As a** developer or manager,
**I want** completed session data to be archived,
**so that** daily summaries can aggregate across multiple sessions.

**Acceptance Criteria:**
1. At session end, the full session state is archived with a unique session ID.
2. Archived sessions are available for cross-session reporting.
3. Archives do not interfere with new sessions.

---

# Epic 3: Intelligent Activity Capture

## US-3.1: Capture All Claude Activity

**As a** developer,
**I want** the plugin to capture all of Claude's work activity,
**so that** every minute Claude spends working is tracked and logged.

**Acceptance Criteria:**
1. Every tool action Claude performs is recorded — file edits, file creation, bash commands, agent tasks, searches, reads, and all other tool use.
2. All Claude working time is attributed to a worklog — nothing is silently discarded.
3. Activities are timestamped for accurate time calculation.

## US-3.2: Developer Idle Detection

**As a** developer,
**I want** idle time (when I'm not interacting with the terminal) to be excluded from tracking,
**so that** logged time reflects actual work, not time away from keyboard.

**Acceptance Criteria:**
1. If the developer is idle for longer than a configurable threshold, that time is excluded.
2. The idle threshold is derived from the accuracy setting but can be overridden.
3. Idle gaps are recorded and subtracted from total work time per chunk.

## US-3.3: Credential Sanitization

**As a** developer,
**I want** sensitive data to be automatically redacted from all captured activity,
**so that** API tokens and credentials never leak into session state or logs.

**Acceptance Criteria:**
1. API tokens, auth headers, and credential patterns are detected and replaced with redacted placeholders.
2. Sanitization applies to: activity records, session state, debug logs.
3. Sanitization happens automatically — no developer action required.

## US-3.4: Planning vs. Implementation Tracking

**As a** developer,
**I want** the plugin to distinguish between planning and implementation time,
**so that** worklogs reflect the nature of the work.

**Acceptance Criteria:**
1. Planning activities (brainstorming, exploring, researching, plan mode) are tracked as a separate work type.
2. Implementation activities (file editing, writing, building) are tracked normally.
3. Planning time is logged to the appropriate issue when planning ends.
4. Very short planning sessions (under 1 minute) are discarded as noise.

## US-3.5: Task-Level Time Tracking

**As a** developer using Claude's task management,
**I want** time spent on individual tasks (TaskCreate/TaskUpdate) to be tracked,
**so that** sub-task time is captured within the broader issue.

**Acceptance Criteria:**
1. When a Claude task is marked as in-progress, time tracking begins for that task.
2. When the task is completed, the elapsed time is logged to the current Jira issue.
3. Very short tasks (under 1 minute) are discarded as noise.

---

# Epic 4: Smart Work Chunking

## US-4.1: Idle Gap Splitting

**As a** developer,
**I want** work to be split into chunks when I go idle,
**so that** each chunk represents a continuous block of active work.

**Acceptance Criteria:**
1. When the gap between consecutive activities exceeds the idle threshold, a new chunk begins.
2. The idle threshold scales with the accuracy setting.
3. Idle gaps are recorded within chunks for accurate time subtraction.

## US-4.2: Issue-Based Splitting

**As a** developer working on multiple issues,
**I want** work to be split when I switch between Jira issues,
**so that** each chunk is attributed to the correct issue.

**Acceptance Criteria:**
1. When consecutive activities belong to different issues, a new chunk begins.
2. Each chunk carries its issue key.
3. Unattributed work (no issue key) is kept in separate chunks.

## US-4.3: Context Switch Detection

**As a** developer,
**I want** the plugin to intelligently detect when I switch to a completely different area of the codebase,
**so that** unrelated work is not lumped into the same chunk.

**Acceptance Criteria:**
1. The plugin detects context switches based on changes in the file directories being worked on.
2. High accuracy settings make context switch detection more sensitive.
3. Low accuracy settings require a more significant shift before flagging a switch.
4. Context-switched chunks are marked for potential re-attribution.

## US-4.4: Accuracy-Scaled Granularity

**As a** manager or developer,
**I want** the accuracy setting to control how finely work is chunked,
**so that** I can choose between detailed tracking and simpler summaries.

**Acceptance Criteria:**
1. High accuracy (8-10): shorter idle thresholds, more sensitive context detection, more chunks.
2. Low accuracy (1-3): longer idle thresholds, less sensitive detection, fewer combined chunks.
3. Medium accuracy (4-7): balanced defaults.

---

# Epic 5: Manual Issue Tracking

## US-5.1: Start Tracking an Existing Issue (`/start-work`)

**As a** developer,
**I want** to explicitly link my work to an existing Jira issue,
**so that** time is tracked against the right issue from the start.

**Acceptance Criteria:**
1. Running `/start-work PROJ-42` fetches the issue from Jira and begins tracking.
2. The issue is added to active issues and set as the current issue.
3. A feature branch is created or switched to (e.g. `feature/PROJ-42-description`).
4. Work never happens directly on main/master/develop branches.
5. If another issue is already active, the developer is asked to switch or stop.

## US-5.2: Create and Track a New Issue (`/start-work`)

**As a** developer starting new work,
**I want** to create a Jira issue and start tracking it in one command,
**so that** I don't have to leave Claude Code to create issues in Jira.

**Acceptance Criteria:**
1. Running `/start-work "Fix login crash"` creates a new issue in Jira.
2. The issue type is intelligently classified (Bug or Task) based on the summary.
3. A parent issue (Epic/Story) is suggested based on recent work context.
4. The issue is created with appropriate labels, assignee, and optional component/version.
5. In cautious mode, the developer confirms type, parent, and details before creation.
6. In balanced/autonomous mode, defaults are applied automatically.

## US-5.3: Stop and Report Work (`/report-work`)

**As a** developer finishing work on an issue,
**I want** to stop tracking, review what was done, and log time to Jira,
**so that** my work is properly documented.

**Acceptance Criteria:**
1. Running `/report-work` builds a worklog for the current issue.
2. A human-readable summary of the work is generated in the configured language.
3. Time is calculated and rounded up to the configured increment.
4. In cautious mode: 5 options — approve, approve and go silent, edit summary, redirect to different issue, reject (keep or drop).
5. In balanced mode: summary is shown, then auto-approved.
6. In autonomous mode: worklog is posted silently with a one-line confirmation.
7. The worklog is posted to Jira with the summary as a rich-text comment.

## US-5.4: Post-Stop Branch Cleanup

**As a** developer who just finished an issue,
**I want** the plugin to help me handle the feature branch,
**so that** I can cleanly transition to the next task.

**Acceptance Criteria:**
1. After stopping, if on a feature branch: cautious mode offers options (open PR, keep working, switch to main).
2. Balanced/autonomous mode auto-suggests opening a PR if there are unpushed commits.

## US-5.5: Issue Type Classification

**As a** developer creating an issue,
**I want** the plugin to intelligently classify whether it's a Bug or Task,
**so that** issues are properly categorized without manual selection.

**Acceptance Criteria:**
1. The summary text is analyzed for bug signals (fix, crash, broken, error) and task signals (implement, add, build, refactor).
2. Classification includes a confidence score.
3. Context from the current session (new files vs. editing existing files) influences the classification.
4. In cautious mode, the developer can override the classification.

## US-5.6: Parent Issue Suggestion

**As a** developer creating a sub-task,
**I want** the plugin to suggest an appropriate parent issue,
**so that** new issues are properly organized in the Jira hierarchy.

**Acceptance Criteria:**
1. The plugin suggests parents based on: the last-used parent in this session, contextually relevant parents, and recently used parents across sessions.
2. The developer can accept a suggestion, pick a different parent, create a new parent, or choose no parent.
3. The most recently used parents are remembered (last 10).

---

# Epic 6: Automatic Issue Detection and Creation

## US-6.1: Work Intent Detection from Prompts

**As a** developer giving Claude instructions,
**I want** the plugin to detect when I'm starting new work,
**so that** issues are created proactively without me needing to remember.

**Acceptance Criteria:**
1. Implementation signals (implement, add feature, build, create, refactor, migrate) are detected.
2. Bug signals (fix, bug, broken, crash, error, regression) are detected.
3. Detection runs on the developer's prompt text before Claude begins work.

## US-6.2: Auto-Create Issue on Intent

**As a** developer in balanced or autonomous mode,
**I want** issues to be created automatically when I start new work,
**so that** all my work is tracked without manual commands.

**Acceptance Criteria:**
1. In autonomous/balanced mode: when work intent is detected with sufficient confidence, a Jira issue is automatically created.
2. The confidence threshold prevents false positives.
3. Duplicate detection prevents creating issues for work already being tracked.
4. In balanced mode, a notice is shown. In autonomous mode, a one-line confirmation.
5. The developer is prompted to switch to a feature branch for the new issue.

## US-6.3: Cautious Mode Fallback

**As a** developer in cautious mode,
**I want** to be notified when the plugin detects new work,
**so that** I can decide whether to create an issue.

**Acceptance Criteria:**
1. In cautious mode, the plugin does not auto-create issues.
2. Instead, it notifies the developer: "Work detected. Run /start-work to link to a Jira issue."
3. If an issue is already active, it suggests creating a sub-issue.

## US-6.4: Duplicate Issue Prevention

**As a** developer,
**I want** the plugin to avoid creating duplicate issues,
**so that** Jira stays clean.

**Acceptance Criteria:**
1. Before creating an issue, the plugin checks all active issues for similarity.
2. If a high-similarity match is found, the new work is attributed to the existing issue instead.
3. The similarity check works on summary text comparison.

---

# Epic 7: Intelligent Worklog Generation

## US-7.1: Worklog Summary Generation

**As a** developer,
**I want** the plugin to generate a meaningful summary of my work,
**so that** Jira worklogs are informative without me writing them manually.

**Acceptance Criteria:**
1. The summary includes which files were changed and what commands were run.
2. The summary is written in the configured language.
3. The summary is 2-4 sentences plus an optional file list.
4. Raw commands, hashes, and internal details are excluded.
5. A maximum of 8 file names are shown, with a "+N more" overflow.

## US-7.2: AI-Enriched Summaries (Optional)

**As a** developer with an Anthropic API key configured,
**I want** worklog summaries to be enriched by AI,
**so that** they read more naturally and professionally.

**Acceptance Criteria:**
1. If an Anthropic API key is available, the raw work facts are sent to a fast AI model.
2. The AI generates a concise, natural description in the configured language.
3. If the AI call fails, the fallback summary is used instead.
4. The enrichment adds no more than a few seconds of latency.

## US-7.3: Time Rounding

**As a** manager or developer,
**I want** logged time to be rounded to a sensible increment,
**so that** Jira entries look clean and consistent.

**Acceptance Criteria:**
1. Time is always rounded UP to the configured increment.
2. The rounding increment scales with the accuracy setting.
3. The minimum logged time is one rounding increment (never zero).
4. Both actual and rounded time are shown during approval.

## US-7.4: Worklog Sanity Cap

**As a** manager,
**I want** a maximum limit on a single worklog entry,
**so that** inflated or erroneous entries are prevented.

**Acceptance Criteria:**
1. A single worklog is capped at 4 hours.
2. If the calculated time exceeds the cap, the worklog is marked as capped.
3. The developer is informed when capping occurs.

## US-7.5: Worklog Posting to Jira

**As a** developer,
**I want** worklogs to be posted to Jira automatically,
**so that** time entries appear on the correct issue without manual data entry.

**Acceptance Criteria:**
1. Worklogs are posted as time entries on the Jira issue.
2. The summary is included as a rich-text comment on the worklog.
3. If posting fails, the worklog is marked as failed and can be retried.
4. Successful posting is confirmed to the developer.

---

# Epic 8: Periodic Worklog Flushing

## US-8.1: Timer-Based Flush

**As a** developer in a long session,
**I want** work to be flushed to Jira periodically,
**so that** if my session crashes, most of my work is already captured.

**Acceptance Criteria:**
1. At a configurable interval (default: 15 minutes), accumulated work is flushed.
2. For autonomous/balanced mode: worklogs are posted to Jira immediately.
3. For cautious mode: worklogs are saved as pending for review.

## US-8.2: Unattributed Work Handling During Flush

**As a** developer,
**I want** unattributed work to be handled intelligently during periodic flush,
**so that** no Claude work time is lost.

**Acceptance Criteria:**
1. In autonomous mode: the plugin attempts to auto-create an issue for unattributed work.
2. In balanced/cautious mode: unattributed work is saved for manual attribution later.
3. Unattributed work is never silently discarded.

## US-8.3: Session End Flush

**As a** developer ending a session,
**I want** all remaining work to be flushed and logged,
**so that** nothing is lost when the session closes.

**Acceptance Criteria:**
1. At session end, all remaining activity buffer is drained into work chunks.
2. Worklogs are built for all active issues.
3. Approved worklogs are posted to Jira before the session closes.
4. Pending/deferred worklogs are preserved for later review.

---

# Epic 9: Retroactive Work Attribution

## US-9.1: Claim Unattributed Work on Issue Creation

**As a** developer who started coding before creating an issue,
**I want** earlier unattributed work to be automatically linked to the new issue,
**so that** all my time is accurately captured.

**Acceptance Criteria:**
1. When an issue is created or linked via `/start-work`, all unattributed work chunks are claimed by that issue.
2. The time from claimed chunks is added to the issue's total.
3. Claiming updates the work chunks' issue key attribution.

## US-9.2: Claim on Branch Detection

**As a** developer who switches to a feature branch,
**I want** unattributed work from before the branch switch to be claimed,
**so that** work done while preparing for the branch is not lost.

**Acceptance Criteria:**
1. When the plugin detects an issue from a branch name, unattributed work is retroactively claimed.
2. Only chunks with no existing issue attribution are claimed.
3. The claimed time is accurately calculated (idle gaps subtracted).

---

# Epic 10: Review and Approve Pending Work

## US-10.1: Review Pending Issues (`/approve-work`)

**As a** developer in cautious mode,
**I want** to review suggested issues before they are created in Jira,
**so that** I control what gets created.

**Acceptance Criteria:**
1. Pending issues show: suggested summary, files changed, activity count.
2. Options: approve (create in Jira), link to existing issue, skip.
3. Approved issues are created and tracking begins.

## US-10.2: Review Pending Worklogs (`/approve-work`)

**As a** developer,
**I want** to review and approve pending worklogs before they are posted,
**so that** I can verify time and summaries are accurate.

**Acceptance Criteria:**
1. Pending worklogs show: issue key, time, summary.
2. Options: approve (post to Jira), edit summary, redirect to different issue, drop.
3. Summaries are enriched into human-readable text before showing.

## US-10.3: Review Unattributed Work (`/approve-work`)

**As a** developer,
**I want** to handle unattributed work that was captured but not linked to any issue,
**so that** no tracked time goes to waste.

**Acceptance Criteria:**
1. Unattributed work shows: time, files, activities.
2. Options: create new issue, log to existing issue, drop.
3. Creating a new issue follows the same flow as `/start-work` with a summary.

---

# Epic 11: Daily Work Summary

## US-11.1: Aggregate Today's Work (`/work-summary`)

**As a** developer,
**I want** to see a summary of everything I worked on today,
**so that** I can review my day's output at a glance.

**Acceptance Criteria:**
1. Aggregates work from the current session and all archived sessions from today.
2. Shows: issues worked on, time per issue, files per issue, activities per issue.
3. Highlights pending and unattributed work that needs attention.
4. Shows total time worked across all issues.

## US-11.2: Post Summary to Jira

**As a** developer,
**I want** to optionally post the daily summary as a comment on each Jira issue,
**so that** my team has visibility into what was accomplished.

**Acceptance Criteria:**
1. The developer can choose to post the summary to Jira.
2. Each issue gets a comment with its portion of the day's work.
3. Posting uses the same language setting as worklogs.

---

# Epic 12: Work Status Display

## US-12.1: Current Tracking Status (`/work-status`)

**As a** developer,
**I want** to see the current state of all my tracked work at a glance,
**so that** I know what's active, pending, and needs attention.

**Acceptance Criteria:**
1. Shows: project key, autonomy level, accuracy, language.
2. Shows: current active issue with elapsed time.
3. Shows: all active issues with individual elapsed times.
4. Shows: work chunks count per issue.
5. Shows: pending worklogs count and activity buffer size.
6. Provides usage tips for available commands.

---

# Epic 13: Git Commit Integration

## US-13.1: Issue Key in Commit Messages

**As a** developer,
**I want** the plugin to suggest including the Jira issue key in my commit messages,
**so that** commits are linked to Jira for traceability.

**Acceptance Criteria:**
1. When a git commit is about to be made and a Jira issue is active, the plugin suggests the format `KEY-123: description`.
2. If the issue key is already present in the commit message, the plugin stays silent.
3. If no issue is active, the plugin stays silent.
4. The suggestion is non-blocking — the developer can ignore it.

---

# Epic 14: Separate Developer and Claude Time Logging (Optional)

## US-14.1: Enable Split Time Logging

**As a** manager,
**I want** to optionally track developer time and Claude time as separate entries,
**so that** I can see how much work the AI does versus the human.

**Acceptance Criteria:**
1. This feature is off by default.
2. When enabled, the plugin distinguishes between developer interaction time and Claude's autonomous working time.
3. Two separate worklogs are posted per work session: one under the developer's Jira account, one under Claude's Jira account.

## US-14.2: Claude as a Jira Team Member

**As a** manager,
**I want** Claude to have its own Jira seat,
**so that** AI work time appears in reports and dashboards like any team member.

**Acceptance Criteria:**
1. Claude's Jira account credentials are configured during setup (or separately).
2. Worklogs posted under Claude's account show Claude as the author.
3. Time reports in Jira accurately reflect both human and AI contributions.

## US-14.3: Combined Mode (Default)

**As a** developer who doesn't need split tracking,
**I want** all time logged as a single entry under my name,
**so that** the simpler default works without extra configuration.

**Acceptance Criteria:**
1. When split logging is disabled, all time (developer + Claude) is combined into one worklog.
2. The worklog is posted under the developer's Jira account.
3. No Claude Jira account is needed.

---

# Epic 15: Credential Security and Data Protection

## US-15.1: Secure Credential Storage

**As a** developer,
**I want** my Jira credentials to be stored securely,
**so that** API tokens are never exposed in the repository.

**Acceptance Criteria:**
1. Credentials are stored in gitignored files (local) or in the user's home directory (global).
2. The plugin enforces gitignore entries during setup.
3. API tokens are never displayed after initial entry.
4. Credentials are never committed to version control.

## US-15.2: Automatic Credential Redaction

**As a** developer,
**I want** credentials to be automatically scrubbed from all plugin data,
**so that** tokens never leak into session files, logs, or captured activity.

**Acceptance Criteria:**
1. Known credential patterns (API tokens, auth headers, bearer tokens) are detected via pattern matching.
2. Detected credentials are replaced with redacted placeholders.
3. Redaction applies to: session state, activity records, debug logs, API logs.
4. Redaction is automatic and requires no developer action.

---

# Epic 16: Resilience and Error Handling

## US-16.1: Never Block Claude Code

**As a** developer,
**I want** the plugin to never crash or block a Claude Code session,
**so that** my coding workflow is never interrupted by plugin errors.

**Acceptance Criteria:**
1. All hook scripts exit successfully even on internal errors.
2. Corrupt session files are handled gracefully (return empty state, log error).
3. No exception in plugin code propagates to Claude Code.

## US-16.2: Jira API Failure Resilience

**As a** developer working with an unreliable network,
**I want** the plugin to continue working even when Jira is unreachable,
**so that** my work is still tracked locally and posted later.

**Acceptance Criteria:**
1. All Jira API call failures are caught and logged.
2. Failed worklogs are marked as failed and can be retried.
3. The plugin continues tracking locally regardless of API status.
4. No API failure causes data loss.

## US-16.3: Concurrent Write Safety

**As a** developer with async hooks running,
**I want** session state to never get corrupted by concurrent writes,
**so that** my tracking data stays consistent.

**Acceptance Criteria:**
1. Session state writes use atomic file operations (write to temp file, then rename).
2. Concurrent hook executions do not corrupt the session file.
3. No temporary files are left behind after writes.

## US-16.4: Log Rotation

**As a** developer running the plugin long-term,
**I want** debug and API logs to rotate automatically,
**so that** they don't consume unlimited disk space.

**Acceptance Criteria:**
1. Logs rotate when they exceed a size threshold (e.g. 1MB).
2. One backup log is kept.
3. Rotation happens automatically without developer action.

## US-16.5: Double-Posting Prevention

**As a** developer,
**I want** the plugin to never post the same worklog twice,
**so that** Jira entries are accurate.

**Acceptance Criteria:**
1. Work chunks used to build a worklog are cleared after processing.
2. Worklogs marked as posted are not reprocessed.
3. Session end and periodic flush do not produce duplicate entries.
