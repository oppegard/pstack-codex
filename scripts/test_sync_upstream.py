import unittest

from scripts.sync_upstream import transform_text


class ModelConversionTest(unittest.TestCase):
    def test_upstream_model_references_preserve_model_roles(self):
        source = "\n".join(
            (
                "grok-4.6-fast-xhigh",
                "grok-4.5-fast-xhigh",
                "claude-fable-5-1-thinking-max",
                "claude-fable-5-thinking-max",
                "claude-opus-5-thinking-xhigh",
                "gpt-5.6-sol-max",
                "gpt-5.6-sol",
                "gpt-6.0-sol-max",
                "gpt-6-sol-max",
                "gpt-6.0-sol",
                "gpt-6-sol",
                "gpt-6.1-sol",
                "gpt-5.6-terra",
                "gpt-5.6-luna",
            )
        )
        expected = "\n".join(
            (
                "gpt-6-luna",
                "gpt-6-luna",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-5.6-terra",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-6.1-sol",
                "gpt-5.6-terra",
                "gpt-6-luna",
            )
        )

        transformed = transform_text(source, [])
        self.assertEqual(transformed, expected)
        self.assertEqual(transform_text(transformed, []), transformed)
