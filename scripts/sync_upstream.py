#!/usr/bin/env python3
"""Stage and apply updates from cursor/plugins/pstack without hiding port conflicts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "pstack-codex"
LOCK_PATH = REPO_ROOT / "upstream-lock.json"
UPSTREAM_REPOSITORY = "https://github.com/cursor/plugins.git"
UPSTREAM_PATH = "pstack"
DEFAULT_REF = "main"

# These files contain deliberate Codex-native behavior. A staged update keeps
# the current ported version and reports an upstream change for manual merge.
PORT_OWNED_TARGETS = {
    ".codex-plugin/plugin.json",
    "README.md",
    "CODEX_PORT.md",
    "codex-agents",
    "skills/architect/SKILL.md",
    "skills/architect/references/rationale-template.md",
    "skills/architect/references/runner-prompt.md",
    "skills/arena/SKILL.md",
    "skills/automate-me/SKILL.md",
    "skills/create-verification-skill/SKILL.md",
    "skills/figure-it-out/SKILL.md",
    "skills/how/SKILL.md",
    "skills/interrogate/SKILL.md",
    "skills/maintain-verification-skill/SKILL.md",
    "skills/no-comments/SKILL.md",
    "skills/poteto-mode/SKILL.md",
    "skills/poteto-mode/references/model-routing.md",
    "skills/poteto-mode/playbooks/autonomous-run.md",
    "skills/poteto-mode/playbooks/autopilot-full.md",
    "skills/poteto-mode/playbooks/autopilot-stack.md",
    "skills/poteto-mode/playbooks/babysit.md",
    "skills/poteto-mode/playbooks/bug-fix.md",
    "skills/poteto-mode/playbooks/eval.md",
    "skills/poteto-mode/playbooks/feature.md",
    "skills/poteto-mode/playbooks/hillclimb.md",
    "skills/poteto-mode/playbooks/multi-phase-plan.md",
    "skills/poteto-mode/playbooks/opening-a-pr.md",
    "skills/poteto-mode/playbooks/orchestrate.md",
    "skills/poteto-mode/playbooks/perf-issue.md",
    "skills/poteto-mode/playbooks/refactoring.md",
    "skills/poteto-mode/playbooks/session-pickup.md",
    "skills/poteto-mode/playbooks/shipping.md",
    "skills/poteto-mode/playbooks/visual-parity.md",
    "skills/poteto-mode/scripts/worktree-audit.sh",
    "skills/reflect/SKILL.md",
    "skills/setup-pstack/SKILL.md",
    "skills/show-me-your-work/SKILL.md",
    "skills/swarm/SKILL.md",
    "skills/technical-writing/SKILL.md",
    "skills/unslop/SKILL.md",
    "skills/why/SKILL.md",
}

# Paths in the raw Cursor source whose updates require a human to reconcile
# with one or more PORT_OWNED_TARGETS.
MANUAL_SOURCE_PATHS = {
    ".cursor-plugin/plugin.json",
    *(path for path in PORT_OWNED_TARGETS if path.startswith("skills/")),
}
MANUAL_SOURCE_PREFIXES = ("agents/",)

REPLACEMENTS = [
    ("name: Poteto Mode", "name: poteto-mode"),
    ('subagent_type: "poteto-agent"', 'agent type `poteto_agent`'),
    ('subagent_type: "Comment Sicko"', 'agent type `comment_sicko`'),
    ("subagent_type: generalPurpose", "agent type `pstack_worker`"),
    ("subagent_type: `generalPurpose`", "agent type `pstack_worker`"),
    ("`subagent_type: generalPurpose`", "agent type `pstack_worker`"),
    ("`poteto-agent`", "`poteto_agent`"),
    ("poteto-agent", "poteto_agent"),
    ("`Comment Sicko`", "`comment_sicko`"),
    ("run_in_background: true", "launch independent agents concurrently"),
    ('environment: "cloud"', "shared Codex workspace"),
    ('environment: "local"', "shared Codex workspace"),
    ("Task subagent", "Codex subagent"),
    ("Task tool", "Codex subagent tools"),
    ("Task schema", "Codex subagent interface"),
    ("Task prompts", "subagent prompts"),
    ("Task calls", "subagent calls"),
    ("Multiple `Task` calls", "Multiple Codex subagent calls"),
    ("`Task` calls", "subagent calls"),
    ("`Task` call", "subagent call"),
    ("`Task`", "a Codex subagent"),
    ("AskQuestion", "ask the user"),
    ("~/.cursor/rules/pstack-models.mdc", "~/.codex/agents/"),
    ("~/.cursor/skills/", "~/.agents/skills/"),
    (".cursor/skills/", ".agents/skills/"),
    ("~/.cursor/plugins/", "Codex-installed plugin paths/"),
    ("~/.cursor/projects/*/", "Codex task history"),
    (".cursor/worktrees/", ".codex/worktrees/"),
    ("Cursor's built-in for authoring SKILL.md files", "Codex's built-in `$skill-creator`"),
    ("Cursor's built-in", "Codex's built-in"),
    ("/create-skill", "$skill-creator"),
    ("**create-skill**", "**skill-creator**"),
    ("create-skill skill", "skill-creator skill"),
    ("the `create-skill` skill", "the `$skill-creator` skill"),
    ("`create-skill`", "`$skill-creator`"),
    ("/deslop", "$unslop"),
    ("the `deslop` skill", "the `unslop` skill"),
    ("`control-ui`", "browser automation tooling"),
    ("`control-cli`", "terminal tooling"),
    ("control-ui", "browser automation tooling"),
    ("control-cli", "terminal tooling"),
    ("cursor-team-kit", "Codex built-ins"),
    ("`/loop`", "a Codex wait/monitor loop"),
    ("/loop", "Codex wait/monitor loop"),
    ("Open a todolist", "Create or update a Codex plan"),
    ("open a todolist", "create or update a Codex plan"),
    ("opens a todo list", "creates or updates a Codex plan"),
    ("todolist", "Codex plan"),
    ("Cursor cloud agent", "Codex subagent"),
    ("cloud agent", "Codex subagent"),
    ("cloud VM", "isolated Codex worktree"),
    ("cloud root", "Codex root task"),
    ("local root", "Codex root task"),
    ("cloud-sleeper wake chain", "Codex wait/monitor mechanism"),
    ("cloud_base_branch", "base branch"),
    ("Cursor", "Codex"),
    ("grok-4.6-fast-xhigh", "gpt-6-luna"),
    ("grok-4.5-fast-xhigh", "gpt-6-luna"),
    ("claude-fable-5-1-thinking-max", "gpt-6.1-sol"),
    ("claude-fable-5-thinking-max", "gpt-6.1-sol"),
    ("claude-opus-5-thinking-xhigh", "gpt-5.6-terra"),
    ("gpt-5.6-sol-max", "gpt-6.1-sol"),
    ("gpt-5.6-sol", "gpt-6.1-sol"),
    ("gpt-6.0-sol-max", "gpt-6.1-sol"),
    ("gpt-6-sol-max", "gpt-6.1-sol"),
    ("gpt-6.0-sol", "gpt-6.1-sol"),
    ("gpt-6-sol", "gpt-6.1-sol"),
    ("gpt-5.6-luna", "gpt-6-luna"),
    ("create-skill", "$skill-creator"),
    ("deslop", "unslop"),
    ("/goal", "the active Codex goal"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check, stage, or apply cursor/plugins/pstack updates."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Report upstream changes only.")
    mode.add_argument("--stage", action="store_true", help="Build .sync/upstream and .sync/candidate.")
    mode.add_argument(
        "--apply-staged",
        action="store_true",
        help="Validate and apply the reviewed .sync/candidate, then update the lock.",
    )
    mode.add_argument(
        "--record-current",
        action="store_true",
        help="Record the supplied upstream source as the baseline for the current port.",
    )
    parser.add_argument("--source", type=Path, help="Use a local pstack source tree.")
    parser.add_argument("--source-commit", help="Commit for a non-Git --source tree.")
    parser.add_argument("--ref", default=DEFAULT_REF, help="Upstream Git ref. Default: main.")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=REPO_ROOT / ".sync",
        help="Staging directory. Default: <repo>/.sync.",
    )
    parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="With --check, return exit code 3 when upstream changed.",
    )
    return parser.parse_args()


def run(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cachebuster() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def load_lock() -> dict[str, object]:
    if not LOCK_PATH.exists():
        return {}
    payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{LOCK_PATH} must contain a JSON object")
    return payload


def source_commit(source: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        return run(["git", "-C", str(source), "rev-parse", "HEAD"])
    except subprocess.CalledProcessError as exc:
        raise ValueError("--source-commit is required when --source is not in a Git checkout") from exc


def acquire_source(args: argparse.Namespace, temp_root: Path) -> tuple[Path, str]:
    if args.source:
        source = args.source.expanduser().resolve()
        if not (source / ".cursor-plugin" / "plugin.json").is_file():
            raise ValueError(f"not a pstack source tree: {source}")
        return source, source_commit(source, args.source_commit)

    checkout = temp_root / "cursor-plugins"
    run(
        [
            "git",
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--sparse",
            "--depth",
            "1",
            "--branch",
            args.ref,
            UPSTREAM_REPOSITORY,
            str(checkout),
        ]
    )
    run(["git", "sparse-checkout", "set", UPSTREAM_PATH], cwd=checkout)
    return checkout / UPSTREAM_PATH, run(["git", "rev-parse", "HEAD"], cwd=checkout)


def upstream_version(source: Path) -> str:
    manifest = json.loads((source / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("upstream plugin manifest has no version")
    return version


def file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            relative = path.relative_to(root).as_posix()
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def compare_hashes(old: dict[str, str], new: dict[str, str]) -> dict[str, list[str]]:
    old_paths = set(old)
    new_paths = set(new)
    return {
        "added": sorted(new_paths - old_paths),
        "removed": sorted(old_paths - new_paths),
        "modified": sorted(path for path in old_paths & new_paths if old[path] != new[path]),
    }


def needs_manual_merge(path: str) -> bool:
    return path in MANUAL_SOURCE_PATHS or path.startswith(MANUAL_SOURCE_PREFIXES)


def summarize_changes(changes: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    automatic: list[str] = []
    manual: list[str] = []
    for status in ("added", "modified", "removed"):
        for path in changes[status]:
            entry = f"{status}: {path}"
            (manual if needs_manual_merge(path) else automatic).append(entry)
    return automatic, manual


def print_report(commit: str, version: str, changes: dict[str, list[str]]) -> bool:
    automatic, manual = summarize_changes(changes)
    changed = bool(automatic or manual)
    previous = load_lock()
    print(f"upstream commit: {previous.get('commit', '-') } -> {commit}")
    print(f"upstream version: {previous.get('version', '-') } -> {version}")
    print(f"changed files: {len(automatic) + len(manual)}")
    print(f"automatic candidates: {len(automatic)}")
    print(f"manual merge required: {len(manual)}")
    if automatic:
        print("\nAutomatic candidates:")
        for entry in automatic:
            print(f"  {entry}")
    if manual:
        print("\nManual merge required:")
        for entry in manual:
            print(f"  {entry}")
    return changed


def transform_text(text: str, skill_names: list[str]) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    for skill_name in skill_names:
        text = re.sub(
            rf"(?<![.\w])/{re.escape(skill_name)}\b",
            f"${skill_name}",
            text,
        )
    for skill_name in sorted(skill_names, key=len, reverse=True):
        text = re.sub(
            rf"\${re.escape(skill_name)}\b",
            f"$pstack-codex:{skill_name}",
            text,
        )
    return text


def move_if_present(root: Path, source: str, destination: str) -> None:
    source_path = root / source
    if not source_path.exists():
        return
    destination_path = root / destination
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_path), str(destination_path))


def copy_port_owned(candidate: Path) -> None:
    for relative in sorted(PORT_OWNED_TARGETS):
        source = PLUGIN_ROOT / relative
        destination = candidate / relative
        if not source.exists():
            continue
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists() or destination.is_symlink():
            destination.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


def build_candidate(source: Path, candidate: Path, version: str, changed: bool) -> None:
    if candidate.exists():
        shutil.rmtree(candidate)
    shutil.copytree(source, candidate)

    move_if_present(candidate, "skills/grokbot", "upstream-cursor-only/grokbot")
    move_if_present(candidate, "skills/make-bot-ui", "upstream-cursor-only/grokbot/make-bot-ui")
    move_if_present(candidate, "agents", "upstream-cursor-only/agents")
    move_if_present(candidate, "automations", "upstream-cursor-only/automations")
    move_if_present(candidate, "docs", "upstream-cursor-only/docs")
    move_if_present(candidate, ".cursor-plugin", "upstream-cursor-only/cursor-plugin")
    move_if_present(candidate, "README.md", "upstream-cursor-only/README.md")

    skills_root = candidate / "skills"
    skill_names = sorted(path.name for path in skills_root.iterdir() if path.is_dir())

    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        reminder_match = re.search(r"(?m)^reminder:\s*(.*?)\s*$", text)
        reminder = reminder_match.group(1) if reminder_match else None
        text = re.sub(r"(?m)^disable-model-invocation:\s*true\s*\n", "", text)
        text = re.sub(r"(?m)^(?:mode|icon|color|paths):\s*.*?\s*\n", "", text)
        text = re.sub(r"(?m)^reminder:\s*.*?\s*\n", "", text)
        text = transform_text(text, skill_names)
        if reminder:
            end = text.find("\n---", 4)
            if end == -1:
                raise ValueError(f"could not find frontmatter end in {skill_md}")
            insertion = end + len("\n---")
            text = text[:insertion] + f"\n\n> Reminder: {reminder}" + text[insertion:]
        skill_md.write_text(text, encoding="utf-8")
        display_name = skill_md.parent.name.replace("-", " ").title()
        metadata = skill_md.parent / "agents" / "openai.yaml"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(
            "interface:\n"
            f"  display_name: {json.dumps(display_name)}\n"
            '  short_description: "Explicit pstack workflow and engineering guidance."\n'
            "policy:\n"
            "  allow_implicit_invocation: false\n",
            encoding="utf-8",
        )

    for markdown in sorted(skills_root.rglob("*.md")):
        if markdown.name == "SKILL.md":
            continue
        markdown.write_text(
            transform_text(markdown.read_text(encoding="utf-8"), skill_names),
            encoding="utf-8",
        )

    recall = skills_root / "recall" / "SKILL.md"
    if recall.exists():
        text = recall.read_text(encoding="utf-8")
        text = re.sub(
            r"Transcripts live at `~/.cursor/projects/.*?(?=\n\n)",
            "Use Codex task tools to list and read relevant prior tasks. When local memory is "
            "available, search `~/.codex/memories/MEMORY.md` and only open the directly "
            "referenced rollout summaries needed for exact evidence.",
            text,
            flags=re.S,
        )
        recall.write_text(text, encoding="utf-8")

    copy_port_owned(candidate)

    manifest_path = candidate / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if changed:
        manifest["version"] = f"{version}+codex.{cachebuster()}"
    manifest["homepage"] = "https://github.com/ColdTbrew/pstack-codex"
    manifest["repository"] = "https://github.com/ColdTbrew/pstack-codex"
    manifest["interface"]["websiteURL"] = "https://github.com/ColdTbrew/pstack-codex"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    notes = candidate / "CODEX_PORT.md"
    text = notes.read_text(encoding="utf-8")
    text = re.sub(
        r"derives from `cursor/plugins/pstack` [^ ]+ under",
        f"derives from `cursor/plugins/pstack` {version} under",
        text,
    )
    notes.write_text(text, encoding="utf-8")


def validate_plugin(root: Path) -> None:
    manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if manifest.get("name") != "pstack-codex":
        raise ValueError("plugin manifest name must be pstack-codex")

    skill_dirs = sorted(path.parent for path in (root / "skills").glob("*/SKILL.md"))
    if not skill_dirs:
        raise ValueError("plugin contains no skills")
    names: list[str] = []
    for skill_dir in skill_dirs:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"(?m)^name:\s*[\"']?([^\n\"']+)", text)
        if not match:
            raise ValueError(f"missing skill name: {skill_dir}")
        name = match.group(1).strip()
        if name != skill_dir.name:
            raise ValueError(f"skill name mismatch: {skill_dir.name} != {name}")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("duplicate skill names")

    banned = re.compile(
        r"\.cursor/(?:rules|skills|projects|worktrees)|subagent_type|run_in_background|"
        r"AskQuestion|/loop\b|cursor-team-kit|control-ui|control-cli|"
        r"api2\.cursor|agent-transcripts",
        re.I,
    )
    for path in sorted((root / "skills").rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".yaml", ".toml", ".sh", ".py"}:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if banned.search(line):
                raise ValueError(f"Cursor runtime dependency: {path}:{line_number}: {line.strip()}")

    agents = sorted((root / "codex-agents").glob("*.toml"))
    if not agents:
        raise ValueError("plugin contains no custom-agent profiles")
    for path in agents:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        for key in ("name", "description", "developer_instructions"):
            if not payload.get(key):
                raise ValueError(f"{path} is missing {key}")


def write_stage_metadata(
    work_dir: Path,
    commit: str,
    version: str,
    hashes: dict[str, str],
    changes: dict[str, list[str]],
) -> None:
    metadata = {
        "repository": UPSTREAM_REPOSITORY,
        "path": UPSTREAM_PATH,
        "ref": DEFAULT_REF,
        "commit": commit,
        "version": version,
        "staged_at": utc_now(),
        "files": hashes,
        "changes": changes,
    }
    (work_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    automatic, manual = summarize_changes(changes)
    report = [
        "# Upstream sync report",
        "",
        f"- Commit: `{commit}`",
        f"- Version: `{version}`",
        f"- Automatic candidates: {len(automatic)}",
        f"- Manual merges: {len(manual)}",
        "",
        "## Automatic candidates",
        "",
        *(f"- `{entry}`" for entry in automatic),
        "",
        "## Manual merge required",
        "",
        *(f"- `{entry}`" for entry in manual),
        "",
    ]
    (work_dir / "report.md").write_text("\n".join(report), encoding="utf-8")


def write_lock(metadata: dict[str, object]) -> None:
    lock = {
        "repository": metadata["repository"],
        "path": metadata["path"],
        "ref": metadata["ref"],
        "commit": metadata["commit"],
        "version": metadata["version"],
        "synced_at": utc_now(),
        "files": metadata["files"],
    }
    LOCK_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def replace_plugin(candidate: Path) -> None:
    validate_plugin(candidate)
    backup_parent = Path(tempfile.mkdtemp(prefix="pstack-codex-backup-", dir=REPO_ROOT))
    backup = backup_parent / "pstack-codex"
    try:
        shutil.move(str(PLUGIN_ROOT), str(backup))
        shutil.copytree(candidate, PLUGIN_ROOT)
        validate_plugin(PLUGIN_ROOT)
    except Exception:
        if PLUGIN_ROOT.exists():
            shutil.rmtree(PLUGIN_ROOT)
        shutil.move(str(backup), str(PLUGIN_ROOT))
        raise
    finally:
        shutil.rmtree(backup_parent, ignore_errors=True)


def main() -> int:
    args = parse_args()
    work_dir = args.work_dir.expanduser().resolve()

    if args.apply_staged:
        candidate = work_dir / "candidate"
        metadata_path = work_dir / "metadata.json"
        if not candidate.is_dir() or not metadata_path.is_file():
            raise ValueError(f"missing staged candidate or metadata under {work_dir}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        replace_plugin(candidate)
        write_lock(metadata)
        print(f"applied reviewed candidate: {candidate}")
        print(f"updated lock: {LOCK_PATH}")
        return 0

    with tempfile.TemporaryDirectory(prefix="pstack-upstream-") as temp:
        source, commit = acquire_source(args, Path(temp))
        version = upstream_version(source)
        hashes = file_hashes(source)
        old_hashes = load_lock().get("files", {})
        if not isinstance(old_hashes, dict):
            raise ValueError("upstream-lock.json files must be an object")
        changes = compare_hashes(old_hashes, hashes)
        changed = print_report(commit, version, changes)

        if args.check:
            return 3 if changed and args.fail_on_change else 0

        if args.record_current:
            validate_plugin(PLUGIN_ROOT)
            write_lock(
                {
                    "repository": UPSTREAM_REPOSITORY,
                    "path": UPSTREAM_PATH,
                    "ref": args.ref,
                    "commit": commit,
                    "version": version,
                    "files": hashes,
                }
            )
            print(f"recorded current upstream baseline: {LOCK_PATH}")
            return 0

        if work_dir.exists():
            shutil.rmtree(work_dir)
        upstream_copy = work_dir / "upstream"
        candidate = work_dir / "candidate"
        work_dir.mkdir(parents=True)
        shutil.copytree(source, upstream_copy)
        build_candidate(upstream_copy, candidate, version, changed)
        validate_plugin(candidate)
        write_stage_metadata(work_dir, commit, version, hashes, changes)
        print(f"staged raw upstream: {upstream_copy}")
        print(f"staged Codex candidate: {candidate}")
        print(f"review report: {work_dir / 'report.md'}")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
