"""The dashboard shows only numbers read from the data files, and calls the RPC read-only."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASH = REPO / "dashboard"
# Digits allowed in the page's visible text: names and fixed protocol terms, not measurements.
ALLOWED = ["HSP-027", "HSP-029", "16 November", "9 December", "8 November",  # dates: a timelock end, a scored prediction, a draft
           "1/40", "4/5", "SHA-256", "2031", "1Click",  # the horizon; a product name
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
        # numbers written into data-n elements by build_numbers.py --render are checked against numbers.json
        # below; they are not hand-written, so they are left out of the visible-text check
        cls.page.feed(re.sub(r'(data-n="[^"]+"[^>]*>)[^<]*', r"\1", cls.html))

    def test_every_key_exists(self):
        js_keys = re.search(r"const KEYS = \[(.*?)\];", self.js, re.S).group(1)
        keys = self.page.keys + re.findall(r'"([^"]+)"', js_keys)
        self.assertTrue(keys)
        missing = [k for k in keys if k not in self.numbers or self.numbers[k]["text"] is None]
        self.assertEqual(missing, [])

    def test_peer_rows_have_their_numbers(self):
        ids = re.findall(r"(\w+): \"[^\"]+\"", re.search(r"const PEER_LABELS = \{(.*?)\};", self.js, re.S).group(1))
        self.assertEqual(len(ids), 10)
        for pid in ids:
            for key in ("market_cap_usd", "revenue_usd_per_year", "mcap_to_revenue"):
                self.assertIn(f"peer.{pid}.{key}", self.numbers)

    def test_rating_files_exist_and_have_the_columns_it_reads(self):
        head = (REPO / "data" / "rating.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
        for col in ("date", "status", "kept_share", "buybacks_kept_usd_per_day", "coverage_buybacks", "coverage_counted", "test_kept_share",
                    "test_usd", "earlier_window", "rule_b", "rating", "stock_near", "stock_peak_near", "test_stock"):
            self.assertIn(col, head)
        rules = json.loads((REPO / "data" / "rating.json").read_text(encoding="utf-8"))["rules"]
        self.assertIn("kept_share_min", rules)
        self.assertIn("drain_max", rules)

    def test_rendered_numbers_match_numbers_json(self):
        found = re.findall(r'data-n="([^"]+)"[^>]*>([^<]*)<', self.html)
        self.assertTrue(found)
        wrong = [(k, t) for k, t in found
                 if t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") != self.numbers[k]["text"]]
        self.assertEqual(wrong, [], "run: python scripts/build_numbers.py --render dashboard/index.html")

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
        self.assertEqual(set(re.findall(r'request_type: "([a-z_]+)"', self.js)), {"call_function", "view_account"})
        for word in ("broadcast_tx", "send_tx", "signAndSend", "privateKey"):
            self.assertNotIn(word, self.js)

    def test_drain_alarm_reads_the_rule_and_the_stock_accounts(self):
        # the live drain test uses rating.json's threshold and the accounts daily.py sums as buybacks_end
        self.assertIn("ratingDoc.rules.drain_max", self.js)
        self.assertIn('"buybacks.multisignature.near", "1csfundsadmin.sputnik-dao.near"', self.js)
        self.assertIn('id="drain"', self.html)

    def test_files_it_reads_are_in_the_repository(self):
        for rel in re.findall(r'getJSON\("([^"$`]+)"\)', self.js):
            self.assertTrue((REPO / "data" / rel).exists(), rel)
        for rel in re.findall(r'saved\("([^"]+)"\)', self.js):
            self.assertTrue((REPO / "data" / rel).exists(), rel)

    def test_lever_model_reproduces_numbers_json(self):
        # the dashboard's calculator: coverage = fees_usd x growth x kept / price / (issued x factor)
        v = lambda k: float(self.numbers[k]["value"])
        fees, issued, p0 = v("n2.fees_usd_per_day"), v("n1.new_near_per_day"), v("iv.fees_conversion_price_usd")
        cov = lambda k, f=1.0: fees * k / p0 / (issued * f)
        self.assertAlmostEqual(cov(1), v("n2.max_coverage"), places=5)
        self.assertAlmostEqual(cov(1, 16 / 25), v("n2.hsp029_max_coverage"), places=5)
        self.assertAlmostEqual(cov(v("iv.wallets_share_of_fees_with_front_end")), v("n1.coverage_with_front_end"), places=5)
        self.assertAlmostEqual(cov(v("iv.wallets_share_of_fees_buybacks")), v("n1.coverage_buybacks"), places=5)
        self.assertAlmostEqual(fees / issued, v("n2.equilibrium_price_usd"), places=3)
        self.assertIn("HSP029_FACTOR = 16 / 25", self.js)

    def test_no_external_scripts_or_styles(self):
        self.assertIsNone(re.search(r'<script[^>]+src="https?:', self.html))
        self.assertIsNone(re.search(r'<link[^>]+href="https?:', self.html))

    def test_levers_svg_takes_its_numbers_from_numbers_json(self):
        """Every figure drawn in docs/levers.svg is a value from numbers.json (scripts/levers_chart.py writes it)."""
        svg = (REPO / "docs" / "levers.svg").read_text(encoding="utf-8")
        pool = " ".join(v["text"] for v in self.numbers.values() if v["text"]) + " 1Click"
        drawn = []
        for chunk in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S):
            chunk = re.sub(r"&#?\w+;", " ", chunk)
            drawn += [t.strip(".,;") for t in re.findall(r"\S*\d\S*", chunk)]
        self.assertTrue(drawn)
        self.assertEqual([t for t in drawn if t not in pool], [])

    def test_the_page_shows_the_levers_picture(self):
        self.assertIn('src="../docs/levers.svg"', self.html)
        self.assertTrue((REPO / "docs" / "levers.svg").exists())

    def test_old_wordings_do_not_return(self):
        """Wordings the K5b reviews found wrong or loose (13 Nov) stay out of every text a reader sees."""
        files = ["README.md", "THESIS.md", "EVIDENCE.md", "docs/DETAILS.md", "dashboard/index.html",
                 "dashboard/app.js", "docs/levers.svg"]
        bad = ["c.issuance_validators_to_pass_upgrade\")} of them", "payment requests", "of what flowed in",
               "a release, not a vote", "the gap costs Buy"]
        # issuance needs block producers with MORE than 4/5 of their stake; DETAILS keeps old README versions as they were
        bad_current = ["4/5 of stake run", "four fifths of the stake", "validators with four fifths"]
        for f in files:
            text = (REPO / f).read_text(encoding="utf-8")
            for b in bad + ([] if f == "docs/DETAILS.md" else bad_current):
                self.assertNotIn(b, text, f"{f}: {b}")


if __name__ == "__main__":
    unittest.main()
