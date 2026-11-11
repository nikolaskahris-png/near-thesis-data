"""The README's chart is drawn from numbers.json: labels are its texts, bars its values.

Run: python -m unittest discover -s tests
"""
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import chart  # noqa: E402


def doc(issued="100", buy="10", front="5", fees="50"):
    def item(value, text):
        return {"value": value, "text": text}
    return {"window": {"start": "2026-10-02", "end": "2026-11-01"}, "numbers": {
        "n1.new_near_per_day": item(issued, "100"),
        "n1.buybacks_near_per_day": item(buy, "10"),
        "n1.front_end_near_per_day": item(front, "5"),
        "n2.fees_near_per_day": item(fees, "50"),
        "n1.coverage_buybacks": item("0.1", "10.0%"),
        "n1.coverage_with_front_end": item("0.15", "15.0%"),
        "n2.max_coverage": item("0.5", "50.0%"),
    }}


def widths(svg):
    return [float(w) for w in re.findall(r'<rect class="(?:issued|buy|front|fees)"[^>]* width="([\d.]+)"', svg)]


class ChartTest(unittest.TestCase):
    def test_bars_are_proportional_to_values(self):
        # issued, buybacks, buybacks again (stacked), front-end, fees
        self.assertEqual(widths(chart.render(doc())), [360.0, 36.0, 36.0, 18.0, 180.0])

    def test_labels_are_the_texts(self):
        svg = chart.render(doc())
        for text in ("100 NEAR · 100%", "10.0%", "15.0% · +5 NEAR", "50.0% · 50 NEAR",
                     "2 October to 1 November 2026"):
            self.assertIn(text, svg)

    def test_committed_chart_matches_numbers_json(self):
        numbers = json.loads((REPO / "data" / "numbers.json").read_text(encoding="utf-8"))
        self.assertEqual((REPO / "docs" / "coverage.svg").read_text(encoding="utf-8"),
                         chart.render(numbers))

    def test_readme_shows_it(self):
        self.assertIn("docs/coverage.svg", (REPO / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
