# Updating from cursor/plugins

The port is pinned by `upstream-lock.json` to one exact commit of
[`cursor/plugins`](https://github.com/cursor/plugins), subtree `pstack/`.
Do not copy a new upstream tree directly over the Codex plugin. Some files are
mechanically convertible; orchestration and agent behavior require a manual
merge.

## 1. Check for an update

```bash
uv run python scripts/sync_upstream.py --check
```

For CI or scripts that need a non-zero result when an update exists:

```bash
uv run python scripts/sync_upstream.py --check --fail-on-change
```

Exit code `3` means the upstream file set changed. Other non-zero values mean
the check failed.

## 2. Build a reviewable candidate

```bash
uv run python scripts/sync_upstream.py --stage
```

This creates ignored files under `.sync/`:

- `.sync/upstream/`: untouched new Cursor source.
- `.sync/candidate/`: mechanically converted Codex candidate.
- `.sync/report.md`: changed files split into automatic and manual lanes.
- `.sync/metadata.json`: exact commit, version, and source hashes.

The converter preserves current Codex-owned orchestration files in the
candidate. If their upstream source changed, the report marks them for manual
merge instead of silently overwriting the port.

## 3. Review and reconcile

```bash
git diff --no-index -- plugins/pstack-codex .sync/candidate
```

For every entry under **Manual merge required**:

1. Compare `.sync/upstream/<path>` with the old upstream file at the commit in
   `upstream-lock.json`.
2. Re-express the behavioral change using Codex custom agents, `$`-qualified
   plugin skills, task plans, and Codex wait/thread semantics.
3. Edit `.sync/candidate`, never the raw `.sync/upstream` copy.
4. Keep Cursor-only Grok Bot and Benny sources under
   `upstream-cursor-only/` unless a real Codex replacement is implemented.

Reject new unresolved Cursor runtime dependencies such as `Task(...)`,
`subagent_type`, `run_in_background`, `.cursor/skills`, or `/loop`.

## 4. Apply only the reviewed candidate

```bash
uv run python scripts/sync_upstream.py --apply-staged
```

This validates the candidate, replaces `plugins/pstack-codex`, and advances
`upstream-lock.json` to the exact staged commit. It does not commit or push.

## 5. Validate, install, and publish

Follow [the release procedure](RELEASING.md) to validate the candidate version
against the current target branch before publishing. Upstream staging creates
a timestamp, but another release may have merged after staging.

```bash
uv run python ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  plugins/pstack-codex

for skill in plugins/pstack-codex/skills/*; do
  uv run python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"
done

codex plugin marketplace upgrade pstack-codex
codex plugin add pstack-codex@pstack-codex
bash scripts/install-agents.sh
```

Then inspect the diff, commit the plugin and lock together, push, and test from
a new Codex task. Never advance the lock without the matching reviewed port.

## Offline fixture mode

Tests and local audits can avoid a network fetch:

```bash
uv run python scripts/sync_upstream.py \
  --stage \
  --source /path/to/cursor-plugins/pstack
```

If the source is not inside a Git checkout, also pass `--source-commit`.
