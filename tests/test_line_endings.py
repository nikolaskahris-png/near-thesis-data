"""Every file a script writes with write_text uses newline="\\n", so a run on Windows saves the
same bytes (and SHA-256) as on Linux. A missing newline= once made data/hsp029.json differ.

Run: python -m unittest discover -s tests
"""
import ast
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


class LineEndingsTest(unittest.TestCase):
    def test_every_write_text_sets_newline(self):
        missing = []
        for path in sorted(SCRIPTS.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "write_text"
                        and not any(k.arg == "newline" for k in node.keywords)):
                    missing.append(f"{path.name}:{node.lineno}")
        self.assertEqual(missing, [], "write_text without newline=: " + ", ".join(missing))


if __name__ == "__main__":
    unittest.main()
