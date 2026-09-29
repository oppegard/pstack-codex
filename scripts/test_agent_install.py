import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path


class AgentInstallationTest(unittest.TestCase):
    def test_installed_profiles_select_expected_models(self):
        repo = Path(__file__).resolve().parents[1]
        source = repo / "plugins" / "pstack-codex" / "codex-agents"
        expected = {
            "comment_sicko": "gpt-5.6-terra",
            "poteto_agent": "gpt-6-astra",
            "pstack_builder_astra": "gpt-6-astra",
            "pstack_builder_luna": "gpt-6-luna",
            "pstack_builder_sol": "gpt-6.1-sol",
            "pstack_builder_terra": "gpt-5.6-terra",
            "pstack_explorer": "gpt-5.6-terra",
            "pstack_reviewer_astra": "gpt-6-astra",
            "pstack_reviewer_luna": "gpt-6-luna",
            "pstack_reviewer_sol": "gpt-6.1-sol",
            "pstack_reviewer_terra": "gpt-5.6-terra",
            "pstack_worker": "gpt-6-luna",
        }

        with tempfile.TemporaryDirectory() as codex_home:
            env = os.environ.copy()
            env["CODEX_HOME"] = codex_home
            subprocess.run(
                ["bash", str(repo / "scripts" / "install-agents.sh")],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            installed = Path(codex_home) / "agents"
            actual = {
                path.stem: tomllib.loads(path.read_text())["model"]
                for path in installed.glob("*.toml")
            }
            self.assertEqual(actual, expected)
            for name in expected:
                self.assertEqual(
                    (installed / f"{name}.toml").read_bytes(),
                    (source / f"{name}.toml").read_bytes(),
                )
