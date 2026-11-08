"""Tests for scripts/quotes.py on simulated pages (no network)."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import quotes  # noqa: E402

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def page_for(url):
    sid = next(k for k, (u, _q) in quotes.SOURCES.items() if u == url)
    body = " ".join(f"<p>&ldquo;{q.replace('NEAR', '<b>NEAR</b>', 1)}&rdquo;</p>" for q in quotes.SOURCES[sid][1])
    return f"<html><head><script>var x='hidden';</script></head><body>{body}</body></html>".encode(), "text/html"


class QuotesTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "data").mkdir()
        (self.root / "docs").mkdir()
        text = "\n".join(f'"{q}"' for _u, qs in quotes.SOURCES.values() for q in qs)
        for d in quotes.DOCS:
            (self.root / d).write_text(text, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_normalise_html_entities_quotes_and_backticks(self):
        self.assertEqual(quotes.normalise("<p>It&rsquo;s `token_diff`  &amp; <i>FAR</i></p>"),
                         "it's token_diff & far")

    def test_fetch_all_then_verify_offline(self):
        report = quotes.run(self.root, fetch=page_for, now=NOW)
        self.assertTrue(all(r.startswith("SAVED") for r in report), report)
        problems, pages, n = quotes.verify(self.root)
        self.assertEqual(problems, [])
        self.assertEqual(pages, len(quotes.SOURCES))
        self.assertEqual(n, sum(len(q) for _u, q in quotes.SOURCES.values()))

    def test_tampered_copy_and_dropped_quote_fail(self):
        quotes.run(self.root, fetch=page_for, now=NOW)
        doc = json.loads((self.root / "data" / "sources.json").read_text(encoding="utf-8"))
        p = self.root / doc["sources"]["sec_svrn_6k"]["path"]
        p.write_bytes(p.read_bytes() + b" ")
        (self.root / "README.md").write_text("nothing quoted", encoding="utf-8")
        (self.root / "THESIS.md").write_text("", encoding="utf-8")
        (self.root / "docs" / "DETAILS.md").write_text("", encoding="utf-8")
        problems, _p, _n = quotes.verify(self.root)
        self.assertTrue(any("sha256 differs" in x for x in problems))
        self.assertTrue(any("no longer in" in x for x in problems))

    def test_refused_or_js_page_is_not_saved_and_import_works(self):
        def refuse(url):
            if "sec.gov" in url:
                raise RuntimeError("HTTP 403")
            if "near.org/blog" in url:
                return b"<html><div id=root></div></html>", "text/html"
            return page_for(url)
        report = quotes.run(self.root, fetch=refuse, now=NOW)
        left = [r for r in report if r.startswith("NOT SAVED")]
        self.assertEqual(len(left), 4)
        self.assertTrue(all("--import" in r for r in left))
        saved = self.root / "saved.html"
        saved.write_bytes(page_for(quotes.SOURCES["sec_svrn_6k"][0])[0])
        quotes.import_file(self.root, "sec_svrn_6k", saved, now=NOW)
        doc = json.loads((self.root / "data" / "sources.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["sources"]["sec_svrn_6k"]["how"], "saved from a browser")
        problems, _p, _n = quotes.verify(self.root)
        self.assertEqual(len([x for x in problems if "not saved" in x]), 3)

    def test_import_rejects_a_page_without_the_quote(self):
        bad = self.root / "bad.html"
        bad.write_bytes(b"<p>other text</p>")
        with self.assertRaises(SystemExit):
            quotes.import_file(self.root, "sec_svrn_6k", bad, now=NOW)


if __name__ == "__main__":
    unittest.main()
