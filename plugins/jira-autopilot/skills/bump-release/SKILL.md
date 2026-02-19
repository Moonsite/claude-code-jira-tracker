---
name: bump-release
description: This skill should be used when the user asks to "bump version", "release new version", "create a release", "publish new version", "tag and release", "bump and release", "push and bump version", or "make a release". Handles the full release workflow for this repository: version bump in plugin.json and marketplace.json, commit on a release branch, PR creation, merge, git tag, and GitHub release with auto-generated notes.
version: 1.0.0
---

# Bump & Release Skill

Full release workflow for the moonsite-claude-extensions repository. Covers version bump, PR, merge, tag, and GitHub release in one pass.

## Files to Update

| File | Field |
|---|---|
| `plugins/<name>/.claude-plugin/plugin.json` | `"version"` |
| `.claude-plugin/marketplace.json` | `"version"` inside the matching plugin entry |

Both files must stay in sync — bump them together.

## Version Strategy

- **Patch** (`3.2.1 → 3.2.2`): bug fixes, logging improvements, minor tweaks
- **Minor** (`3.2.x → 3.3.0`): new features, new config options, new hooks
- **Major** (`3.x.x → 4.0.0`): breaking changes, major redesign

When in doubt about which bump level to use, infer from the commit history since the last tag:
```bash
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

## Release Workflow

### Step 1 — Determine next version

Read current version from `plugins/<name>/.claude-plugin/plugin.json`, apply the appropriate bump.

### Step 2 — Create release branch

```bash
git checkout -b release/<version>
```

### Step 3 — Bump version in both files

Edit `plugin.json` and `marketplace.json`. Confirm both are updated before committing.

### Step 4 — Commit and push

```bash
git add plugins/<name>/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "Bump <plugin-name> to <version>"
git push -u origin release/<version>
```

### Step 5 — Create and merge PR

```bash
gh pr create \
  --title "Bump <plugin-name> to <version>" \
  --body "$(cat <<'EOF'
## Release <version>

<summary of changes since last release>

### Changes
- <bullet points from commits since last tag>
EOF
)"

gh pr merge --squash --auto
```

Wait for the merge to complete:
```bash
gh pr view --json state -q .state
```

### Step 6 — Pull merged main and tag

```bash
git checkout main && git pull
git tag v<version>
git push origin v<version>
```

### Step 7 — Create GitHub release

```bash
gh release create v<version> \
  --title "<plugin-name> v<version>" \
  --generate-notes
```

`--generate-notes` auto-fills the body from commits since the previous tag. Replace with `--notes "..."` if a custom description is preferred.

## After Release

- Switch back to main: `git checkout main`
- Delete the local release branch: `git branch -d release/<version>`
- Confirm the release appears on GitHub: `gh release view v<version>`

## Generating Release Notes Manually

To draft notes from commits:
```bash
PREV=$(git describe --tags --abbrev=0)
git log ${PREV}..HEAD --oneline
```

Group into sections:
- **Features** — `feat:` commits
- **Fixes** — `fix:` commits
- **Improvements** — `chore:`, `refactor:`, `perf:` commits
