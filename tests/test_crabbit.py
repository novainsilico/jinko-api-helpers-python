import unittest
import crabbit.utils


class TestCrabbit(unittest.TestCase):
    def test_get_sid_revision_from_url_normal(self):
        self.assertEqual(
            crabbit.utils.get_sid_revision_from_url(
                "https://jinko.ai/ca-foo-bar?revision=42"
            ),
            ("ca-foo-bar", 42),
        )

    def test_get_sid_revision_from_url_no_revision(self):
        self.assertEqual(
            crabbit.utils.get_sid_revision_from_url("https://jinko.ai/cm-baz-nix"),
            ("cm-baz-nix", None),
        )

    def test_get_sid_revision_from_url_bad_url(self):
        self.assertEqual(
            crabbit.utils.get_sid_revision_from_url("https://jinko.ai"), (None, None)
        )

    def test_get_sid_revision_from_url_localhost_url(self):
        self.assertEqual(
            crabbit.utils.get_sid_revision_from_url(
                "http://localhost:8000/cm-bla-bla?revision=1"
            ),
            ("cm-bla-bla", 1),
        )


if __name__ == "__main__":
    unittest.main()
