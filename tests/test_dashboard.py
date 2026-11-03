"""The dashboard shows only numbers read from the data files, and calls the RPC read-only."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASH = REPO / "dashboard"
# Digits allowed in the page's visible text: names and fixed protocol terms, not measurements.
ALLOWED = ["HSP-027", "HSP-029", "16 November", "1/40", "4/5", "SHA-256",
           # account names and the tag of an implicit account, as in the README
           "ecotreasury5.multisignature.near", "ecotreasury4.multisignature.near", "sha256:e630d735"]


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
        self.keys = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        for k, v in attrs:
            if k == "data-n":
                self.keys.append(v)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def strip_js_strings(src):
    src = re.sub(r'"(?:\\.|[^"\\\n])*"|`(?:\\.|[^`\\])*`', '""', src)
    return re.sub(r"//[^\n]*", "", src)


class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (DASH / "index.html").read_text(encoding="utf-8")
        cls.js = (DASH / "app.js").read_text(encoding="utf-8")
        cls.numbers = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))["numbers"]
        cls.page = Visible()
        cls.page.feed(cls.html)

    def test_every_key_exists(self):
        js_keys = re.search(r"const KEYS = \[(.*?)\];", self.js, re.S).group(1)
        keys = self.page.keys + re.findall(r'"([^"]+)"', js_keys)
        self.assertTrue(keys)
        missing = [k for k in keys if k not in self.numbers or self.numbers[k]["text"] is None]
        self.assertEqual(missing, [])

    def test_no_hand_written_numbers_in_the_page(self):
        text = " ".join(self.page.parts)
        for a in ALLOWED:
            text = text.replace(a, "")
        self.assertEqual(re.findall(r"\d", text), [])

    def test_no_large_numeric_literals_in_the_script(self):
        code = strip_js_strings(self.js)
        big = [m for m in re.findall(r"\b\d[\d_]*(?:\.\d+)?\b", code) if float(m.replace("_", "")) >= 1000]
        self.assertEqual(big, [])

    def test_rpc_is_read_only(self):
        self.assertEqual(set(re.findall(r"https://[a-z0-9.\-]*rpc[a-z0-9.\-]*", self.js)),
                         {"https://rpc.mainnet.fastnear.com"})
        self.assertEqual(set(re.findall(r'method: "([a-z_]+)"', self.js)) - {"POST"}, {"query"})
        self.assertEqual(set(re.findall(r'request_type: "([a-z_]+)"', self.js)), {"call_function"})
        for word in ("broadcast_tx", "send_tx", "signAndSend", "privateKey"):
            self.assertNotIn(word, self.js)

    def test_files_it_reads_are_in_the_repository(self):
        for rel in re.findall(r'getJSON\("([^"$`]+)"\)', self.js):
            self.assertTrue((REPO / "data" / rel).exists(), rel)
        for rel in re.findall(r'saved\("([^"]+)"\)', self.js):
            self.assertTrue((REPO / "data" / rel).exists(), rel)

    def test_no_external_scripts_or_styles(self):
        self.assertIsNone(re.search(r'<script[^>]+src="https?:', self.html))
        self.assertIsNone(re.search(r'<link[^>]+href="https?:', self.html))


if __name__ == "__main__":
    unittest.main()
