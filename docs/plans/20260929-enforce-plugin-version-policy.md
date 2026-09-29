# Enforce plugin release version policy

## Approved scope

The user approved the preceding proposal with “implement this on a PR”.
Record the release policy, provide a reusable version check, enforce it on
PRs, and document manual GitHub settings. This file records that approved
proposal before implementation. No production dependencies or GitHub settings
changes are included. The user enables branch protection and merges the PR.

## Feature workflow

### Feature

**You own the design. Plan, review, verify.** Delegate implementation. Stay in the lead.

1. `how` over the affected subsystem.
2. `architect` for parallel design exploration. Skipping stays as `architect skipped: <reason>`. Do not fold the design decision silently into implementation.
3. Write the throughput checkpoint as four todo items. A dimension that genuinely does not apply (single file, no fan-out) keeps its item with `n/a: <reason>` rather than being dropped:
   - **Blocking first steps.** Gates run before fan-out.
   - **Independent workstreams.** Disjoint files, services, or layers parallelize. Shared writes serialize.
   - **Shared mutable state.** Default to splitting the target (the **separate-before-serializing-shared-state** principle skill). Serialize only for real invariants.
   - **Smallest safe decomposition.** If one worker is best, name why.
4. Delegate code-writing using [model routing](../references/model-routing.md), matching the implementation profile to the task difficulty. Give it a specific scope: file paths, the named data shape and its organizing structure per **principle-model-the-domain**, and success criteria. Review its diff yourself. When implementation admits multiple valid shapes, use the **arena** skill so candidates surface alternatives and the cross-judge guards the pick. If nested spawning is unavailable, the current agent owns the diff directly; never return a standing-by response. Comments per **Comments**. Re-ground against source for upstream-derived files, port shared-primitive improvements to all consumers, and verify each.
5. Verify on the matching surface. "Inconclusive" or wrong-surface is not a pass; flag it.
6. Rebase into small, ordered commits; stack follow-ups.
   Use the **sequence-verifiable-units** principle skill, building, verifying, and committing each small unit before the next.
7. If the design is contested, `interrogate` before shipping.
8. Run **Opening a PR**.

Code-coupled work (one feature, one migration) goes to a single owner with the checkpoint inline. That owner fans out internally after the blocking phase. Parent-level fan-out is for slices that produce independent artifacts (audits, cross-subsystem investigations, competing experiments). Rewrite the checkpoint at phase boundaries. Spawn a fresh owner rather than chaining interrupts.

**Reply:** what you built, what you chose and why, the throughput checkpoint, open decisions. Tables for design alternatives.

## Task checklist

- [x] Ground the existing manifest, upstream timestamp generation, workflows, and GitHub protection state through the completed Investigation.
- [x] Compare two isolated design sketches and choose the smallest safe shape.
- [x] Implement a standard-library Python CLI and meaningful Git-fixture tests.
- [x] Add a read-only pull_request workflow with no path filter. Use the tested merge candidate and its exact base commit.
- [x] Advance the current port timestamp to give the previously merged Sol update a distinct release identifier.
- [x] Record the policy in docs/RELEASING.md and a root AGENTS.md pointer. Link upstream publication instructions to the general policy.
- [x] Verify stale/equal/decremented releases, content changes, additions/deletions/modes, manifest metadata changes, version-only changes, unrelated changes, and invalid version input.
- [x] Run focused tests, actionlint, existing tests, and the version CLI on the actual PR tree. Obtain independent review and comment review.
- [ ] Commit, push, open a ready PR, and include the approved plan/checklist in an Implementation Plan details section.
- [ ] Give exact manual steps to require the named check on main, require an up-to-date branch, and enforce protections for administrators. Verify the PR check reports before handback.

## Throughput checkpoint

- [x] Blocking first steps. Establish current base, approved requirements, and design before implementation.
- [x] Independent workstreams. One code owner handles checker/tests/workflow. Root owns documentation and the plan after the design is selected.
- [x] Shared mutable state. Exclusive file ownership prevents conflicting writes. Neither actor modifies repository settings.
- [x] Smallest safe decomposition. One reusable checker with one CI caller and one policy document. CI performs checks and never commits a bump.

## Invariants and data shape

Model a release as an upstream numeric version plus a UTC fourteen-digit
Codex timestamp. Model compared package content as two Git tree snapshots,
excluding only the manifest version value from content comparison.
Reject any downgrade. Require a strictly newer version when package content
changes. Allow equal versions for unrelated changes. Validate candidate
versions rather than accepting arbitrary strings or generic build-metadata
precedence. Check the merge candidate against its exact target branch tip,
not the historical merge-base. GitHub strict required checks close the stale
successful-check race. Main currently has no protection or effective rules.

## Progress

The approved requirements came from the preceding source-backed investigation.
Implementation starts from origin/main in an isolated worktree. Two design
sketches and an independent judge established the checker interface before
implementation. The release documentation and current version bump are complete.

## Design synthesis

Two isolated candidates explored a Git tree snapshot map and a Git raw-diff
classifier. An independent judge scored both 10/12. Choose the snapshot map
for its smaller comparison boundary. Graft the raw-diff candidate's literal
JSON version-token masking. Preserve all bytes outside the top-level version
string, including formatting and key order. Reject duplicate keys.

Use one standard-library module with parsed `ReleaseVersion`, immutable
`TreeEntry` and `PluginSnapshot` values, and a pure two-snapshot policy check.
The CLI is `python3 scripts/check_plugin_version.py --base REF --head REF`.
Resolve both Git revisions safely to commits before reading trees. Compare
tracked paths, modes, object kinds, and blob identities. Normalize only the
manifest version token. Allow stable numeric upstream versions and valid UTC
fourteen-digit port timestamps. Reject unsupported formats with a diagnostic.

The workflow uses checkout v4 with depth two, then compares `HEAD^1` and
`HEAD`. Confirm a second parent exists so an ordinary branch commit cannot be
mistaken for GitHub's tested merge. Run on every PR, including base edits,
without path filters. Give it the unique check name `Plugin version policy`.

The raw-diff alternative lost because its status parser adds machinery that
the snapshot map avoids. Canonical JSON comparison lost because it would
ignore manifest formatting changes. Full SemVer prerelease handling is
unnecessary for the current upstream release convention. The synthesis
requires no production dependency or human product decision.

A documentation reviewer found no correctness issue in the manual settings or
release policy. Comment review requested this progress update.

## Verification and review

- `python3 -m unittest scripts.test_check_plugin_version -v` passed 27 real Git fixture tests.
- `python3 -m unittest scripts.test_sync_upstream scripts.test_agent_install -v` passed both existing checks.
- `actionlint .github/workflows/check-plugin-version.yml` passed.
- `git diff --check` passed. Root read the checker, workflow, tests, and documentation.
- An independent reviewer found no blocking correctness issue. Comment review kept the single JSON boundary comment and requested the completed progress update.

The fixtures reproduce a newer main branch merged before an older PR and a
conflict resolution retaining the old timestamp. The checker rejects that
merge result, then accepts a corrected newer release. Tests also cover modes,
symlinks, gitlinks, byte formatting, nested and escaped JSON keys, invalid
versions and refs, unchanged content, and uncommitted worktree isolation.

Build the Lever produced the reusable CLI. Test Behavior, Not Implementation
selected subprocess checks against real Git commits. Independent design
exploration selected a snapshot map. Exclusive file ownership separated code
and documentation writers. The current port identifier is
`0.15.0+codex.20260929211516`.
