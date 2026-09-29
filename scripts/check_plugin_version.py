#!/usr/bin/env python3
"""Check the plugin release identity against two committed Git trees."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
import subprocess
import sys


PLUGIN_ROOT = "plugins/pstack-codex"
MANIFEST = f"{PLUGIN_ROOT}/.codex-plugin/plugin.json".encode()
VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"\+codex\.([0-9]{14})"
)


class InputError(ValueError):
    pass


class PolicyError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class ReleaseVersion:
    upstream: tuple[int, int, int]
    timestamp: str

    def __str__(self) -> str:
        return ".".join(map(str, self.upstream)) + "+codex." + self.timestamp


@dataclass(frozen=True)
class TreeEntry:
    mode: bytes
    kind: bytes
    identity: bytes


@dataclass(frozen=True)
class PluginSnapshot:
    version: ReleaseVersion
    entries: dict[bytes, TreeEntry]


def parse_version(value: object) -> ReleaseVersion:
    match = VERSION_PATTERN.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise InputError(
            "manifest version must match major.minor.patch+codex.YYYYMMDDHHMMSS "
            "with no leading zeroes in the upstream version"
        )
    timestamp = match[4]
    try:
        datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise InputError(f"manifest version has an invalid UTC timestamp {timestamp}") from error
    return ReleaseVersion(tuple(int(match[i]) for i in (1, 2, 3)), timestamp)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"manifest contains duplicate JSON key {key!r}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise InputError(f"manifest contains invalid JSON constant {value}")


def read_manifest(raw: bytes) -> tuple[ReleaseVersion, bytes]:
    try:
        text = raw.decode("utf-8")
        decoder = json.JSONDecoder(
            object_pairs_hook=unique_object, parse_constant=reject_constant
        )
        manifest = decoder.decode(text)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise InputError(f"manifest is not valid UTF-8 JSON: {error}") from error
    if not isinstance(manifest, dict):
        raise InputError("manifest must be a JSON object")
    if "version" not in manifest:
        raise InputError("manifest is missing its version")
    version = parse_version(manifest["version"])

    # Decode boundaries so nested members and escaped keys cannot mask another value.
    whitespace = re.compile(r"[ \t\r\n]*")
    offset = whitespace.match(text).end() + 1
    while True:
        offset = whitespace.match(text, offset).end()
        key, offset = decoder.raw_decode(text, offset)
        offset = whitespace.match(text, offset).end() + 1
        start = whitespace.match(text, offset).end()
        _, end = decoder.raw_decode(text, start)
        if key == "version":
            return version, (text[:start] + '""' + text[end:]).encode("utf-8")
        offset = whitespace.match(text, end).end() + 1


def git(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise InputError(f"Git command failed: {detail}")
    return result.stdout


def load_snapshot(revision: str) -> PluginSnapshot:
    commit = git("rev-parse", "--verify", "--end-of-options", revision + "^{commit}")
    commit = commit.decode("ascii").strip()
    entries = {}
    for record in git("ls-tree", "-r", "-z", commit, "--", PLUGIN_ROOT).split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, identity = metadata.split(b" ")
        entries[path] = TreeEntry(mode, kind, identity)
    manifest = entries.get(MANIFEST)
    if manifest is None:
        raise InputError(f"{revision}: missing plugin manifest")
    if manifest.kind != b"blob" or manifest.mode not in (b"100644", b"100755"):
        raise InputError(f"{revision}: plugin manifest must be a regular file")
    try:
        version, content = read_manifest(git("cat-file", "blob", manifest.identity.decode("ascii")))
    except InputError as error:
        raise InputError(f"{revision}: {error}") from error
    entries[MANIFEST] = TreeEntry(manifest.mode, manifest.kind, content)
    return PluginSnapshot(version, entries)


def check_release(base: PluginSnapshot, head: PluginSnapshot) -> str:
    if head.version < base.version:
        raise PolicyError(f"head version {head.version} is lower than base version {base.version}")
    changed = head.entries != base.entries
    if changed and head.version == base.version:
        raise PolicyError(
            f"plugin content changed but head version {head.version} "
            f"is not newer than base version {base.version}"
        )
    return (
        f"plugin content {'changed' if changed else 'unchanged'}; "
        f"base version {base.version}; head version {head.version}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="target branch commit or revision")
    parser.add_argument("--head", default="HEAD", help="candidate commit or revision (default HEAD)")
    arguments = parser.parse_args(argv)
    try:
        result = check_release(load_snapshot(arguments.base), load_snapshot(arguments.head))
    except PolicyError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    except (InputError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"PASS: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
