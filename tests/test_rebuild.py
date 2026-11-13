"""rebuild.py runs the same checks as the verify workflow, and the README names it."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import rebuild  # noqa: E402


class TestRebuild(unittest.TestCase):
    def test_steps_cover_every_text_and_check(self):
        cmds = [" ".join(c[1:]) for _, c in rebuild.STEPS]
        for text in ("README.md", "EVIDENCE.md", "docs/DETAILS.md", "THESIS.md"):
            self.assertIn(f"scripts/build_numbers.py --check {text}", cmds)
        for c in ("-m unittest discover -s tests", "scripts/build_numbers.py --verify",
                  "scripts/upgrade_watch.py --verify", "scripts/check_prereg.py --file"):
            self.assertIn(c, cmds)

    def test_tests_step_is_not_recursive(self):
        # the tests step runs this file too; it must not call rebuild.main()
        self.assertNotIn("rebuild.py", " ".join(" ".join(c) for _, c in rebuild.STEPS))

    def test_readme_and_workflow_use_it(self):
        self.assertIn("python scripts/rebuild.py", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertIn("python scripts/rebuild.py",
                      (REPO / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
