# Release plugin changes

## Prepare a release identifier

Use `MAJOR.MINOR.PATCH+codex.YYYYMMDDHHMMSS` in
`plugins/pstack-codex/.codex-plugin/plugin.json`. Keep the upstream numeric
version when making port changes. Advance it when adopting a newer upstream
release. Use a valid UTC timestamp for the Codex suffix.

When tracked files under `plugins/pstack-codex/` change, give the candidate a
version newer than its target branch. This includes skills, agent profiles,
assets, file additions, deletions, executable modes, and symlink targets.
Only the manifest's top-level version value is excluded from content
comparison. Other manifest changes, including formatting, count as changes.

For changes outside the plugin tree, keep the current version or advance it.
Never reduce a version. Compare the upstream numeric version first, then the
Codex timestamp when the upstream version is equal. Standard SemVer
precedence ignores build metadata and cannot order these port timestamps.

Fetch the current target branch before preparing the bump:

```bash
git fetch origin main
git show origin/main:plugins/pstack-codex/.codex-plugin/plugin.json
date -u +%Y%m%d%H%M%S
```

Edit the manifest version with a timestamp greater than the target branch's
suffix. After another release merges first, update your branch and refresh
the bump if needed. For a content rollback, restore the old content under a
newer release identifier.

## Check committed changes

Commit the intended changes, then run:

```bash
python3 scripts/check_plugin_version.py --base origin/main --head HEAD
python3 -m unittest discover -v
```

Use the actual target branch instead of `origin/main` for a PR to another
branch. The checker reads committed Git trees. Stage and commit any edits
before checking them.

The check permits an equal version when plugin content is unchanged. It
rejects equal versions for changed content and lower versions for every PR.
Invalid version formats and timestamps also fail.

## Enable the GitHub merge gate

The `Plugin version policy` job runs on every pull request. It compares
GitHub's tested merge commit with its first parent, the exact target branch
tip represented in that candidate. Its result alone does not invalidate an
older successful run when `main` moves. Enable strict branch protection to
close that race.

After the PR's workflow has reported a successful `Plugin version policy`
check, configure this repository manually:

1. Open **Settings**, then **Branches**.
2. Under **Branch protection rules**, select **Add classic branch protection rule**.
3. Set **Branch name pattern** to `main`.
4. Enable **Require a pull request before merging**. An approval requirement is optional.
5. Enable **Require status checks to pass before merging**.
6. Add `Plugin version policy` as a required check. Select GitHub Actions as its expected source when that option is available.
7. Enable **Require branches to be up to date before merging**.
8. Enable **Do not allow bypassing the above settings** to apply the rule to administrators too.
9. Leave force pushes and deletions disabled, then create the rule.
10. Merge the policy PR after its required check passes.

If the check is not available in the picker yet, wait for its first workflow
run. These settings are separate from the repository files and need a
repository administrator. The PR does not change GitHub settings.

Verify that an outdated PR is blocked until its branch is updated and the
check passes against the new merge candidate. Resolve a manifest conflict
with a release identifier newer than the current target branch.

See [GitHub's branch protection instructions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
and [strict required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging).

## Update Codex installations after merge

Run the installation update sequence from the repository clone:

```bash
git switch main
git pull --ff-only
codex plugin marketplace upgrade pstack-codex
codex plugin add pstack-codex@pstack-codex
bash scripts/install-agents.sh
```

Set `CODEX_HOME` for each installation that uses a custom home. Start a new
Codex task to load the updated profiles. The plugin refresh and the agent
copy script update separate installed files.
