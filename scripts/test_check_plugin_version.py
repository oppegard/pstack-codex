import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).with_name("check_plugin_version.py").resolve()
BASE_VERSION = "0.15.0+codex.20260910010513"
NEW_VERSION = "0.15.0+codex.20260929010101"


class PluginVersionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git("init", "-b", "main")
        for key, value in (
            ("user.name", "Version Policy Test"),
            ("user.email", "version-test@example.invalid"),
            ("commit.gpgsign", "false"),
            ("core.hooksPath", str(self.repo / "empty-hooks")),
            ("core.autocrlf", "false"),
            ("core.filemode", "true"),
        ):
            self.git("config", key, value)
        self.plugin = self.repo / "plugins/pstack-codex"
        self.manifest = self.plugin / ".codex-plugin/plugin.json"
        self.manifest.parent.mkdir(parents=True)
        self.write_manifest(BASE_VERSION)
        (self.plugin / "skill.md").write_text("original skill\n")
        (self.plugin / "link").symlink_to("skill.md")
        self.base = self.commit()

    def git(self, *arguments, check=True):
        result = subprocess.run(
            ["git", *arguments], cwd=self.repo,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if check:
            self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-m", "fixture", "--allow-empty")
        return self.git("rev-parse", "HEAD").stdout.strip()

    def write_manifest(self, version, **metadata):
        self.manifest.write_text(json.dumps({"name": "fixture", "version": version, **metadata}) + "\n")

    def check_policy(self, status, diagnostic, *, base=None, head=None):
        arguments = [sys.executable, str(CHECKER), "--base=" + (base or self.base)]
        if head is not None:
            arguments.extend(("--head", head))
        result = subprocess.run(
            arguments, cwd=self.repo, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        self.assertIn(diagnostic, result.stdout + result.stderr)
        return result

    def test_unrelated_commit_and_dirty_worktree_allow_same_version(self):
        (self.repo / "README.md").write_text("unrelated repository instructions\n")
        self.commit()
        (self.plugin / "skill.md").write_text("uncommitted change\n")
        (self.plugin / "untracked.md").write_text("untracked change\n")
        self.check_policy(0, "plugin content unchanged")

    def test_version_only_bump_is_not_content_change(self):
        self.write_manifest(NEW_VERSION)
        self.commit()
        self.check_policy(0, "plugin content unchanged")

    def test_equal_version_fails_for_content_change(self):
        (self.plugin / "skill.md").write_text("new skill\n")
        self.commit()
        self.check_policy(1, "plugin content changed but head version")

    def test_lower_version_fails_without_content_change(self):
        self.write_manifest("0.15.0+codex.20260910010512")
        self.commit()
        self.check_policy(1, "is lower than base version")

    def test_newer_timestamp_allows_content_change(self):
        (self.plugin / "skill.md").write_text("new skill\n")
        self.write_manifest(NEW_VERSION)
        self.commit()
        self.check_policy(0, "plugin content changed")

    def test_upstream_increase_wins_over_older_timestamp(self):
        self.write_manifest("0.16.0+codex.20200101000000")
        (self.plugin / "skill.md").write_text("new upstream\n")
        self.commit()
        self.check_policy(0, "head version 0.16.0+codex.20200101000000")

    def test_upstream_decrease_fails_despite_newer_timestamp(self):
        self.write_manifest("0.14.9+codex.20300101000000")
        self.commit()
        self.check_policy(1, "is lower than base version")

    def test_numeric_core_order_is_not_lexicographic(self):
        self.write_manifest("0.9.0+codex.20260910010513")
        base = self.commit()
        self.write_manifest("0.10.0+codex.20260910010513")
        self.commit()
        self.check_policy(0, "head version 0.10.0", base=base)

    def test_invalid_versions_fail_as_input(self):
        for version in (
            "0.15.0", "0.15.0+codex.202609290101", "0.15.0+codex.20260230010101",
            "0.15.0+codex.20261301010101", "0.15.0+codex.20260929240000",
            "0.15.0+codex.00000101000000", "00.15.0+codex.20260929010101",
            "0.15.0-beta+codex.20260929010101", "0.15.0+codex.20260929010101\n",
            15, None,
        ):
            with self.subTest(version=version):
                self.write_manifest(version)
                self.commit()
                self.check_policy(2, "manifest version")

    def test_missing_or_invalid_manifest_fails_as_input(self):
        for text, diagnostic in (
            ('{"name":"fixture"}', "missing its version"),
            ('{"version":', "not valid UTF-8 JSON"),
            ('[]', "must be a JSON object"),
            ('{"version":"' + NEW_VERSION + '", "number":NaN}', "invalid JSON constant"),
        ):
            with self.subTest(text=text):
                self.manifest.write_text(text)
                self.commit()
                self.check_policy(2, diagnostic)

    def test_duplicate_keys_are_rejected_including_nested_objects(self):
        for text in (
            '{"version":"' + NEW_VERSION + '","version":"' + NEW_VERSION + '"}',
            '{"version":"' + NEW_VERSION + '","settings":{"x":1,"x":2}}',
        ):
            with self.subTest(text=text):
                self.manifest.write_text(text)
                self.commit()
                self.check_policy(2, "duplicate JSON key")

    def test_deleted_manifest_fails(self):
        self.manifest.unlink()
        self.commit()
        self.check_policy(2, "missing plugin manifest")

    def test_manifest_symlink_is_not_accepted(self):
        self.manifest.unlink()
        self.manifest.symlink_to("../skill.md")
        self.commit()
        self.check_policy(2, "manifest must be a regular file")

    def test_manifest_metadata_change_requires_bump(self):
        self.write_manifest(BASE_VERSION, description="changed")
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_manifest_formatting_change_requires_bump(self):
        self.manifest.write_text(json.dumps(json.loads(self.manifest.read_text()), indent=2))
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_manifest_key_order_change_requires_bump(self):
        self.manifest.write_text(json.dumps({"version": BASE_VERSION, "name": "fixture"}) + "\n")
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_nested_version_does_not_mask_content(self):
        self.write_manifest(BASE_VERSION, settings={"version": "old"})
        base = self.commit()
        self.write_manifest(BASE_VERSION, settings={"version": "new"})
        self.commit()
        self.check_policy(1, "plugin content changed", base=base)

    def test_mask_finds_top_level_escaped_key_after_nested_values(self):
        template = ' {"settings":{"version":"nested","array":[{"x":"},"}]},"ver\\u0073ion":"%s","name":"fixture"}\n'
        self.manifest.write_text(template % BASE_VERSION)
        base = self.commit()
        self.manifest.write_text(template % NEW_VERSION)
        self.commit()
        self.check_policy(0, "plugin content unchanged", base=base)

    def test_added_file_with_unusual_name_requires_bump(self):
        (self.plugin / "new\nwith\ttabs.md").write_text("new content\n")
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_deleted_file_requires_bump(self):
        (self.plugin / "skill.md").unlink()
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_file_mode_change_requires_bump(self):
        self.git("update-index", "--chmod=+x", "plugins/pstack-codex/skill.md")
        self.git("commit", "-m", "fixture mode")
        self.check_policy(1, "plugin content changed")

    def test_manifest_mode_change_requires_bump(self):
        self.git("update-index", "--chmod=+x", "plugins/pstack-codex/.codex-plugin/plugin.json")
        self.git("commit", "-m", "fixture mode")
        self.check_policy(1, "plugin content changed")

    def test_symlink_target_change_requires_bump(self):
        (self.plugin / "link").unlink()
        (self.plugin / "link").symlink_to("different.md")
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_file_to_symlink_change_requires_bump(self):
        (self.plugin / "skill.md").unlink()
        (self.plugin / "skill.md").symlink_to("different.md")
        self.commit()
        self.check_policy(1, "plugin content changed")

    def test_gitlink_entry_requires_bump(self):
        self.git(
            "update-index", "--add", "--cacheinfo", "160000", self.base,
            "plugins/pstack-codex/vendor",
        )
        self.git("commit", "-m", "fixture gitlink")
        self.check_policy(1, "plugin content changed")

    def test_invalid_revision_and_option_like_revision_fail(self):
        for revision in ("does-not-exist", "--help"):
            with self.subTest(revision=revision):
                self.check_policy(2, "Git command failed", base=revision)

    def test_reverse_pr_order_checks_newer_exact_base_and_resolved_merge(self):
        self.git("switch", "-c", "older-pr")
        (self.plugin / "older-pr.md").write_text("first PR\n")
        self.write_manifest(NEW_VERSION)
        self.commit()
        self.git("switch", "main")
        (self.plugin / "newer-pr.md").write_text("second PR merged first\n")
        self.write_manifest("0.15.0+codex.20260929010102")
        newer_main = self.commit()
        merge = self.git("merge", "older-pr", "--no-ff", "--no-commit", check=False)
        self.assertEqual(merge.returncode, 1, merge.stdout + merge.stderr)
        self.write_manifest(NEW_VERSION)
        self.commit()
        self.check_policy(1, "is lower than base version", base="HEAD^1")
        self.write_manifest("0.15.0+codex.20260929010103")
        self.commit()
        self.check_policy(0, "plugin content changed", base=newer_main)


if __name__ == "__main__":
    unittest.main()
