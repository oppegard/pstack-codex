# Upgrade Sol references to GPT-6.1

## Goal and scope

Open a PR that selects `gpt-6.1-sol` for the shipped Sol builder and reviewer,
updates the routing policy, and keeps upstream conversion on the same model.
Provide commands to update each Codex installation after the user merges.

The data shape is the existing ordered list of source and destination string
pairs in `REPLACEMENTS`, plus the `model` fields in agent TOMLs. Preserve this
structure. This change needs no production dependency or architectural change.

Six active files contain GPT-6 Sol references. Update those files and the
existing converter and installation checks. Keep the September 28 approved
plan as a record of its completed migration. Preserve Astra, Luna, Terra,
reasoning settings, and unrelated repository state.

The [official GPT-6.1 Sol model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
confirms `gpt-6.1-sol` and supports `medium`, which both Sol profiles use.

## Workflow checklist

- [x] `how` over the affected subsystem.
- [x] `architect` for parallel design exploration. Skipping stays as `architect skipped: <reason>`. Do not fold the design decision silently into implementation.
  architect skipped: Existing model fields and ordered replacements determine the mechanical change.
- [x] Write the throughput checkpoint as four todo items. A dimension that genuinely does not apply (single file, no fan-out) keeps its item with `n/a: <reason>` rather than being dropped:
  - **Blocking first steps.** Gates run before fan-out.
  - **Independent workstreams.** Disjoint files, services, or layers parallelize. Shared writes serialize.
  - **Shared mutable state.** Default to splitting the target (the **separate-before-serializing-shared-state** principle skill). Serialize only for real invariants.
  - **Smallest safe decomposition.** If one worker is best, name why.
- [x] Delegate code-writing using [model routing](../../plugins/pstack-codex/skills/poteto-mode/references/model-routing.md), matching the implementation profile to the task difficulty. Give it a specific scope: file paths, the named data shape and its organizing structure per **principle-model-the-domain**, and success criteria. Review its diff yourself. When implementation admits multiple valid shapes, use the **arena** skill so candidates surface alternatives and the cross-judge guards the pick. If nested spawning is unavailable, the current agent owns the diff directly; never return a standing-by response. Comments per **Comments**. Re-ground against source for upstream-derived files, port shared-primitive improvements to all consumers, and verify each.
- [x] Verify on the matching surface. "Inconclusive" or wrong-surface is not a pass; flag it.
- [x] Rebase into small, ordered commits; stack follow-ups.
  Use the **sequence-verifiable-units** principle skill, building, verifying, and committing each small unit before the next.
- [x] If the design is contested, `interrogate` before shipping.
  skip: No contested design. Reconsider if review finds a design issue.
- [x] Run **Opening a PR**.

## Throughput checkpoint

- [x] Blocking first steps. Inventory active references, verify the official model ID, and inspect conversion and installation ownership. The user approved implementation and PR creation.
- [x] Independent workstreams. n/a: The converter, profiles, routing, and checks form one model selection change.
- [x] Shared mutable state. One implementation owner edits the six files. The root updates the plan and reviews the artifact.
- [x] Smallest safe decomposition. One mechanical worker implements the replacement in one commit. Independent review checks the whole diff.

## Tasks after approval

- [x] Update `pstack_builder_sol.toml` and `pstack_reviewer_sol.toml` to `gpt-6.1-sol`.
- [x] Update the routing policy's three Sol model entries.
- [x] Update existing Sol conversion destinations. Add conversion for upstream `gpt-6-sol` and `gpt-6.0-sol`, with any specific suffix forms before their shorter prefixes. Confirm existing `gpt-6.1-sol` stays unchanged.
- [x] Update existing converter and installation checks to expect GPT-6.1 Sol. Cover direct old Sol inputs and idempotent new inputs.
- [x] Inspect conversion output, parse shipped TOMLs, and install into a temporary `CODEX_HOME` to read back actual copies. Check the diff and confirm unrelated model profiles are unchanged.
- [x] Obtain independent review and resolve findings.
- [x] Commit with a Conventional Commit title of at most 50 characters and body lines of at most 72 characters. Push a topic branch and open a PR without merging.
- [x] Include this plan and its current checklist in a collapsed PR section titled `Implementation Plan`.
- [x] Provide post-merge plugin refresh, repository update, agent installation, and new-task instructions for each Codex home.

## Definition of done

The two shipped Sol profiles, routing policy, and converter select GPT-6.1 Sol.
Old direct Sol IDs convert to the new ID without corrupting it on a second
conversion. The installation check reads the new model from copied TOMLs.
The PR contains this bounded change and the approved plan. The final reply
links the open PR and gives concrete post-merge commands.

## Progress

The worktree was clean at inspection. A read-only reviewer confirmed converter
ordering, profile ownership, and the separate agent installation step.
The user chose update instructions without a wizard. The user approved implementation and PR creation on September 29.
Work proceeds in `/tmp/worktrees/pstack-codex/20260929-gpt-6-1-sol` on
`chore/gpt-6-1-sol`, based on the fetched `origin/main`.

## Verification and review

- `python3 -m unittest scripts.test_sync_upstream scripts.test_agent_install -v` passed both tests. The converter check covers fourteen inputs and confirms idempotence. The installation check copies all twelve profiles into a temporary Codex home and reads their models back.
- `git diff --check` passed. The root inspected the full six-file diff.
- An independent Sol reviewer found no blocking issue. Other model families and reasoning settings are unchanged.
- The installed Codex CLI is `0.159.0`. Its help confirms the marketplace refresh and plugin installation commands. The configured pstack marketplace points to `https://github.com/oppegard/pstack-codex.git`.

## Post-merge update instructions

Run these commands for each Codex installation after merge. If an installation
uses a custom `CODEX_HOME`, set that variable for every command in the sequence.

```bash
cd /Users/glenn/src/oppegard/pstack-codex
git switch main
git pull --ff-only
codex plugin marketplace upgrade pstack-codex
codex plugin add pstack-codex@pstack-codex
bash scripts/install-agents.sh
```

Start a new Codex task to load the updated profiles. The plugin refresh updates
skills. The script separately copies the twelve agent TOMLs and overwrites
existing files with the same names in `${CODEX_HOME:-$HOME/.codex}/agents`.

Confirm both Sol profiles select the new model.

```bash
rg '^model =' "${CODEX_HOME:-$HOME/.codex}/agents/pstack_builder_sol.toml" "${CODEX_HOME:-$HOME/.codex}/agents/pstack_reviewer_sol.toml"
```

The comment review found no actionable findings. No comments or suppressions were added.

The ready PR is https://github.com/oppegard/pstack-codex/pull/3. Its base is `main`.
The implementation is committed and pushed. This final plan update records
completion in a separate documentation commit. The PR includes the current
plan in its collapsed `Implementation Plan` section. No merge was performed.
