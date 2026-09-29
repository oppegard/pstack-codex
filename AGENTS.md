# Repository instructions

## Release validation

Follow [the release procedure](docs/RELEASING.md) for changes to installed
plugin content. The version check owns the release ordering rules.

After committing PR changes, fetch the current target branch and run:

```bash
git fetch origin main
python3 scripts/check_plugin_version.py --base origin/main --head HEAD
```

Use the actual PR target branch when it differs from `main`. Resolve failed
release checks before opening or updating the PR.
