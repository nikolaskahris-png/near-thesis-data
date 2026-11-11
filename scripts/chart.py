"""Draw the chart at the top of the README from data/numbers.json, offline, standard library only.

    python scripts/chart.py            # write docs/coverage.svg
    python scripts/chart.py --verify   # redraw in memory; OK only if docs/coverage.svg is the same

Every label is the "text" of a number in numbers.json (the same text the README shows) and every
bar's length is its "value", so the picture cannot drift from the figures without this check failing.
"""
import argparse
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parent.parent
NUMBERS = REPO / "data" / "numbers.json"
OUT = REPO / "docs" / "coverage.svg"

W, H = 800, 268
LABEL_X, BAR_X, BAR_MAX, BAR_H = 16, 262, 360, 26
ROW_Y = (70, 112, 154, 196)


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


def day_month_year(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def bar(x, y, value, scale, cls):
    w = (Decimal(value) * scale).quantize(Decimal("0.1"))
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{BAR_H}" rx="3"/>', x + w


def render(doc):
    n = doc["numbers"]
    win = doc["window"]
    issued = Decimal(n["n1.new_near_per_day"]["value"])
    buy = Decimal(n["n1.buybacks_near_per_day"]["value"])
    front = Decimal(n["n1.front_end_near_per_day"]["value"])
    fees = Decimal(n["n2.fees_near_per_day"]["value"])
    scale = Decimal(BAR_MAX) / issued
    t = {k: escape(n[k]["text"]) for k in (
        "n1.new_near_per_day", "n1.buybacks_near_per_day", "n1.front_end_near_per_day",
        "n2.fees_near_per_day", "n1.coverage_buybacks", "n1.coverage_with_front_end",
        "n2.max_coverage")}
    rows = []

    def row(y, label, sub, shapes, end, value_text):
        rows.append(f'<text class="lab" x="{LABEL_X}" y="{y + 12}">{label}</text>')
        rows.append(f'<text class="sub" x="{LABEL_X}" y="{y + 26}">{sub}</text>')
        rows.extend(shapes)
        rows.append(f'<text class="val" x="{end + 10}" y="{y + 18}">{value_text}</text>')

    s, e = bar(BAR_X, ROW_Y[0], issued, scale, "issued")
    row(ROW_Y[0], "New NEAR issued", "a protocol rule", [s], e,
        f'{t["n1.new_near_per_day"]} NEAR · 100%')
    s, e = bar(BAR_X, ROW_Y[1], buy, scale, "buy")
    row(ROW_Y[1], "Kept by the buybacks wallets", "a choice; none of it burned", [s], e,
        f'<tspan class="big">{t["n1.coverage_buybacks"]}</tspan> · {t["n1.buybacks_near_per_day"]} NEAR')
    s1, e1 = bar(BAR_X, ROW_Y[2], buy, scale, "buy")
    s2, e2 = bar(e1, ROW_Y[2], front, scale, "front")
    row(ROW_Y[2], "… plus the front-end fund", "the three revenue wallets", [s1, s2], e2,
        f'{t["n1.coverage_with_front_end"]} · +{t["n1.front_end_near_per_day"]} NEAR')
    s, e = bar(BAR_X, ROW_Y[3], fees, scale, "fees")
    row(ROW_Y[3], "If NEAR kept every fee", "the ceiling; fees from DefiLlama", [s], e,
        f'{t["n2.max_coverage"]} · {t["n2.fees_near_per_day"]} NEAR')

    title = "What holders get for the NEAR issued, a day"
    a, b = date.fromisoformat(win["start"]), date.fromisoformat(win["end"])
    when = (f"{a.day} {MONTHS[a.month - 1]}" + (f" {a.year}" if a.year != b.year else "")
            + f" to {day_month_year(win['end'])}")
    foot = "Drawn from data/numbers.json by scripts/chart.py; python scripts/chart.py --verify checks it."
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="t d">',
        f'<title id="t">{escape(title)}</title>',
        f'<desc id="d">Bars in NEAR a day, {escape(when)}: new NEAR issued; what the buybacks wallets '
        f'keep; with the front-end fund; and what all fees would buy.</desc>',
        "<style>",
        "svg{--bg:#ffffff;--ink:#1f2328;--mute:#59636e;--issued:#c4c9d0;--buy:#0b6bcb;--front:#7fb2e8;--fees:#0b6bcb}",
        "@media (prefers-color-scheme:dark){svg{--bg:#0d1117;--ink:#e6edf3;--mute:#9198a1;"
        "--issued:#3d444d;--buy:#4c9ef0;--front:#24578a;--fees:#4c9ef0}}",
        ".bg{fill:var(--bg)}",
        "text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:var(--ink)}",
        ".h{font-size:17px;font-weight:600}.when,.sub,.foot{font-size:12px;fill:var(--mute)}",
        ".lab{font-size:14px;font-weight:600}.val{font-size:14px}.big{font-weight:700;fill:var(--buy)}",
        ".issued{fill:var(--issued)}.buy{fill:var(--buy)}.front{fill:var(--front)}",
        ".fees{fill:none;stroke:var(--fees);stroke-width:1.5;stroke-dasharray:5 4}",
        "</style>",
        f'<rect class="bg" width="{W}" height="{H}" rx="6"/>',
        f'<text class="h" x="{LABEL_X}" y="30">{escape(title)}</text>',
        f'<text class="when" x="{LABEL_X}" y="50">NEAR a day, {escape(when)}</text>',
        *rows,
        f'<text class="foot" x="{LABEL_X}" y="{H - 14}">{escape(foot)}</text>',
        "</svg>",
        "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    svg = render(json.loads(NUMBERS.read_text(encoding="utf-8")))
    rel = OUT.relative_to(REPO).as_posix()
    if args.verify:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != svg:
            print(f"FAILED: {rel} differs from the chart drawn from data/numbers.json; "
                  "run python scripts/chart.py")
            return 1
        print(f"OK: {rel} is the chart drawn from data/numbers.json")
        return 0
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"Saved {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
