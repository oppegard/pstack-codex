#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="$repo_root/plugins/pstack-codex/codex-agents"
target_dir="${CODEX_HOME:-$HOME/.codex}/agents"

mkdir -p "$target_dir"
for source in "$source_dir"/*.toml; do
	cp "$source" "$target_dir/$(basename "$source")"
done

printf 'Installed %s custom-agent profiles into %s\n' \
	"$(find "$source_dir" -maxdepth 1 -name '*.toml' | wc -l | tr -d ' ')" \
	"$target_dir"
printf 'Start a new Codex task to load the updated profiles.\n'
