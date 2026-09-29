# pstack for Codex

A Codex-native port of
[`cursor/plugins/pstack`](https://github.com/cursor/plugins/tree/main/pstack).
It packages pstack's engineering skills and playbooks as an installable Codex
marketplace plugin and provides matching Codex custom-agent profiles.

## Install

```bash
codex plugin marketplace add oppegard/pstack-codex --ref main
codex plugin add pstack-codex@pstack-codex
git clone https://github.com/oppegard/pstack-codex.git
cd pstack-codex
bash scripts/install-agents.sh # https://github.com/openai/codex/issues/18308
```

Start a new Codex task, press `$`, and choose **Poteto Mode**, or invoke it
directly:

```text
$pstack-codex:poteto-mode investigate this bug, fix the root cause, and verify it.
```

The plugin currently contains 46 skills and 12 custom-agent profiles. The
custom agents use Astra for demanding work, Sol for scoped implementation,
Terra for exploration and alternatives, and Luna for bounded mechanical work.
See the [model routing policy](plugins/pstack-codex/skills/poteto-mode/references/model-routing.md)
for coordinator settings, review escalation, and mode composition.

## Update an installation

Marketplace upgrades refresh the configured source. Check the
`marketplaces.pstack-codex.source` value in `~/.codex/config.toml`, or in
`$CODEX_HOME/config.toml` if you set `CODEX_HOME`. If it does not point to
`oppegard/pstack-codex`, replace that source first:

```bash
codex plugin marketplace remove pstack-codex
codex plugin marketplace add oppegard/pstack-codex --ref main
```

From your `oppegard/pstack-codex` clone, run:

```bash
git switch main
git pull --ff-only
codex plugin marketplace upgrade pstack-codex
codex plugin add pstack-codex@pstack-codex
bash scripts/install-agents.sh # https://github.com/openai/codex/issues/18308
```

Start a new Codex task after updating.

## Maintainer workflow

The exact upstream commit and file hashes are recorded in
[`upstream-lock.json`](upstream-lock.json). A weekly GitHub Action checks for
new upstream changes. To stage and review an update locally:

```bash
uv run python scripts/sync_upstream.py --check
uv run python scripts/sync_upstream.py --stage
```

Read [`docs/UPSTREAM_SYNC.md`](docs/UPSTREAM_SYNC.md) before applying a staged
candidate. The process separates mechanical conversions from Codex-owned files
that require a manual semantic merge.

## Port boundary

Cursor-specific `Task` calls, model rules, `/loop`, skill locations, and
transcript lookup are converted to Codex equivalents. The Cursor-only Grok Bot
webhook and Benny automation are retained under `upstream-cursor-only/` for
provenance but are not registered with Codex.

## License

MIT. Original pstack copyright belongs to Lauren Tan. See
[`NOTICE.md`](NOTICE.md) for attribution and port-maintainer details.
