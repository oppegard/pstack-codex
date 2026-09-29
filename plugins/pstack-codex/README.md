# pstack for Codex

This is a Codex-native port of
[`cursor/plugins/pstack`](https://github.com/cursor/plugins/tree/main/pstack).
It preserves pstack's engineering principles and playbooks while replacing
Cursor-specific model rules, agent calls, skill locations, and loop mechanics.

## Use it

Start a new Codex task after installation, then invoke:

```text
$pstack-codex:poteto-mode investigate this bug, reproduce it, fix the root cause, and verify it.
```

Useful direct workflows include `$pstack-codex:how`, `$pstack-codex:why`,
`$pstack-codex:arena`, `$pstack-codex:swarm`,
`$pstack-codex:interrogate`, `$pstack-codex:tdd`,
`$pstack-codex:unslop`, and `$pstack-codex:technical-writing`.

Run `$pstack-codex:setup-pstack` to review or change the custom-agent model
mapping. The companion agent installation includes the `poteto_agent`, `comment_sicko`,
`pstack_builder_*`, `pstack_reviewer_*`, `pstack_explorer`, and
`pstack_worker` profiles under `~/.codex/agents/`.

## Port boundary

The Cursor-only Grok Bot webhook and Benny automation sources are retained
under `upstream-cursor-only/` for provenance but are not registered in Codex.
See `CODEX_PORT.md` for the runtime mapping.

The public source, installation instructions, and upstream update workflow are
maintained at <https://github.com/oppegard/pstack-codex>.

Original pstack is by Lauren Tan and distributed under the MIT license.
