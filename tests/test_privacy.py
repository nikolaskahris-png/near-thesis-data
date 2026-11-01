"""Tests for scripts/privacy.py (no network)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import privacy  # noqa: E402


class PrivacyTest(unittest.TestCase):
    def test_tag_is_stable_and_idempotent(self):
        t = privacy.tag("a.near")
        self.assertTrue(t.startswith("sha256:") and len(t) == 23)
        self.assertEqual(privacy.tag(t), t)

    def test_redact_keeps_public_and_non_accounts(self):
        hexacct = "ab" * 32
        out = privacy.redact({"x.tg": ["a.near", "intents.near", "0.4.5", "call:*", hexacct]},
                             {"intents.near"})
        self.assertEqual(out, {privacy.tag("x.tg"): [privacy.tag("a.near"), "intents.near",
                                                     "0.4.5", "call:*", privacy.tag(hexacct)]})

    def test_check_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "private").mkdir(parents=True)
            orig = json.dumps(["a.near"]).encode()
            (root / "data" / "private" / "x.json").write_bytes(orig)
            files = {"x": {"path": "data/private/x.json", "sha256": privacy.sha256(orig),
                           "private": True}}

            def project(key, raw):
                return privacy.dumps(privacy.redact(json.loads(raw), set()))
            privacy.write_redacted(root, files, project)
            self.assertNotIn(b"a.near", privacy.read(root, files["x"]))
            self.assertEqual(privacy.check_files(root, files, project), ([], 0))
            (root / "data" / "private" / "x.json").unlink()
            self.assertEqual(privacy.check_files(root, files, project), ([], 1))
            (root / files["x"]["redacted"]["path"]).write_bytes(b"[]")
            self.assertTrue(privacy.check_files(root, files, project)[0])


if __name__ == "__main__":
    unittest.main()
