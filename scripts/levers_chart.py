"""Draw docs/levers.svg: who holds each lever, from the fees users pay to what a holder keeps.

    python scripts/levers_chart.py            write docs/levers.svg from data/numbers.json
    python scripts/levers_chart.py --verify   redraw it and compare with the committed file

Every figure in the picture is read from data/numbers.json (the same keys the dashboard uses, from
data/control_map.json), so no digit is typed by hand. tests/test_dashboard.py also checks that every
figure in the file is a value in numbers.json.
"""
import json
import sys
from pathlib import Path

W, H = 1400, 712
COLS = [(24, 280), (328, 280), (632, 368), (1024, 352)]
FEW, RULE, OFF = "few", "rule", "off"

STYLE = """<style>
svg{--bg:#ffffff;--ink:#1f2328;--mute:#59636e;--card:#f7f7f5;--line:#d8d8d2;--few:#c2410c;--rule:#15803d;--fewbg:#fdf0e8;--rulebg:#eaf6ee}
@media (prefers-color-scheme:dark){svg{--bg:#0d1117;--ink:#e6edf3;--mute:#9198a1;--card:#161b22;--line:#30363d;--few:#f0834c;--rule:#4ac07c;--fewbg:#231611;--rulebg:#102018}}
text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;fill:var(--ink)}
.bg{fill:var(--bg)}
.h{font-size:27px;font-weight:700}.sub{font-size:18px;fill:var(--mute)}
.rowh{font-size:16px;font-weight:700;fill:var(--mute);letter-spacing:.06em}
.bx{fill:var(--card);stroke:var(--line);stroke-width:1.5}
.bx.few{fill:var(--fewbg)}.bx.rule{fill:var(--rulebg)}
.bar.few{fill:var(--few)}.bar.rule{fill:var(--rule)}.bar.off{fill:var(--mute)}
.t{font-size:21px;font-weight:700}.v{font-size:19px;fill:var(--ink)}
.w{font-size:17px;font-weight:600}.w.few{fill:var(--few)}.w.rule{fill:var(--rule)}.w.off{fill:var(--mute)}
.ar{stroke:var(--mute);stroke-width:3;fill:none}.arh{fill:var(--mute)}
.key{font-size:17px;fill:var(--mute)}.foot{font-size:16px;fill:var(--mute)}
</style>"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(x, y, w, h, kind, title, lines, who):
    """One link: a title, its value, and who can change it."""
    out = ['<rect class="bx %s" x="%d" y="%d" width="%d" height="%d" rx="10"/>' % (kind, x, y, w, h),
           '<rect class="bar %s" x="%d" y="%d" width="8" height="%d"/>' % (kind, x, y, h)]
    ty = y + 34
    out.append('<text class="t" x="%d" y="%d">%s</text>' % (x + 22, ty, esc(title)))
    for ln in lines:
        ty += 27
        out.append('<text class="v" x="%d" y="%d">%s</text>' % (x + 22, ty, esc(ln)))
    if who:
        out.append('<text class="w %s" x="%d" y="%d">%s</text>' % (kind, x + 22, y + h - 16, esc(who)))
    return "\n".join(out)


def arrow(x1, x2, y):
    return ('<path class="ar" d="M %d %d H %d"/>' % (x1, y, x2 - 12) +
            '<path class="arh" d="M %d %d L %d %d L %d %d Z"/>' % (x2 - 13, y - 7, x2, y, x2 - 13, y + 7))


def main():
    verify = "--verify" in sys.argv[1:]
    repo = Path(__file__).resolve().parent.parent
    n = json.loads((repo / "data" / "numbers.json").read_text(encoding="utf-8"))["numbers"]

    def t(key):
        return n[key]["text"]

    (x1, w1), (x2, w2), (x3, w3), (x4, w4) = COLS
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'role="img" aria-labelledby="ttl desc">' % (W, H, W, H),
         '<title id="ttl">Who holds each lever, from the fee a user pays to the NEAR a holder keeps</title>',
         '<desc id="desc">Two flows read on chain. Above: users’ fees reach NEAR Intents, then three revenue '
         'wallets, and stop there — no lock, no burn, and each of those wallets moves with two signers. Below: '
         'new NEAR is issued under a protocol rule that only a release run by block producers with more than four fifths of their stake can change; '
         'the treasury takes its share with two signers, and stakers receive the rest.</desc>',
         STYLE,
         '<rect class="bg" width="%d" height="%d" rx="8"/>' % (W, H),
         '<text class="h" x="24" y="40">Who holds each lever</text>',
         '<text class="sub" x="24" y="68">Read on chain at the window’s end block. '
         'The colour says how many signatures move it.</text>']

    # ---- fees -> holders
    s.append('<text class="rowh" x="24" y="104">FEES &#8594; HOLDERS</text>')
    ay = 116
    s.append(box(x1, ay + 101, w1, 134, OFF, "Fees users pay",
                 ["%s bps of volume" % t("n2.fees_bps"), "%s a day in October" % t("n2.fees_usd_per_day")],
                 "set off-chain, by the apps"))
    s.append(box(x2, ay + 101, w2, 134, FEW, "NEAR Intents",
                 ["intents.near", "protocol fee %s" % t("c.intents_fee_pips")],
                 "DAO: %s signers" % t("c.intents_fee_change")))
    bh = 104
    s.append(box(x3, ay, w3, bh, FEW, "Buybacks wallets",
                 ["%s NEAR" % t("n1.buybacks_held_near")],
                 "multisig: %s signers" % t("c.buybacks_confirmations")))
    s.append(box(x3, ay + 116, w3, bh, FEW, "1Click fee fund",
                 ["holds NEAR with the buybacks stock"],
                 "DAO: %s signers" % t("c.wallet_1cs_transfer")))
    s.append(box(x3, ay + 232, w3, bh, FEW, "Front-end fund",
                 ["%s NEAR" % t("n1.front_end_held_near")],
                 "send %s · rules %s" % (t("c.front_end_transfer"), t("c.front_end_rules"))))
    s.append(box(x4, ay + 75, w4, 187, FEW, "No lock. No burn.",
                 ["The wallets kept %s for every" % t("iv.cents_per_new_dollar"),
                  "dollar of new NEAR issued;",
                  "%s of revenue since April" % t("f2.wallets_kept_share_of_revenue.2026-04_2026-10"),
                  "stayed in its wallets"],
                 "nothing on chain requires it"))
    s.append(arrow(x1 + w1, x2, ay + 168))
    s.append(arrow(x2 + w2, x3, ay + 168))
    s.append(arrow(x3 + w3, x4, ay + 168))

    # ---- new NEAR -> stakers
    by = 516
    s.append('<text class="rowh" x="24" y="%d">NEW NEAR &#8594; STAKERS</text>' % (by - 16))
    s.append(box(x1, by, w1, 134, RULE, "New NEAR issued",
                 ["at most %s a year" % t("c.issuance_max_inflation_rate"), "a protocol rule"],
                 "changed only by a release"))
    s.append(box(x2, by, w2, 134, RULE, "Validators run it",
                 ["block producers with more",
                  "than %s of their stake" % t("c.issuance_upgrade_stake_threshold")],
                 "they vote by running it"))
    s.append(box(x3, by, w3, 134, FEW, "treasury.near",
                 ["%s of net new NEAR, measured" % t("c.treasury_share_of_new_supply"),
                  "paid %s NEAR out this year" % t("ts.year_out_near")],
                 "multisig: %s signers" % t("c.treasury_confirmations")))
    s.append(box(x4, by, w4, 134, RULE, "Stakers",
                 ["receive the rest, minus their", "validator’s commission;",
                  "unstaked NEAR receives none"], ""))
    s.append(arrow(x1 + w1, x2, by + 67))
    s.append(arrow(x2 + w2, x3, by + 67))
    s.append(arrow(x3 + w3, x4, by + 67))

    ky = H - 28
    s.append('<rect class="bar few" x="24" y="%d" width="8" height="18"/>' % (ky - 14))
    s.append('<text class="key" x="40" y="%d">moves with one to three signatures</text>' % ky)
    s.append('<rect class="bar rule" x="420" y="%d" width="8" height="18"/>' % (ky - 14))
    s.append('<text class="key" x="436" y="%d">a protocol rule, or many validators</text>' % ky)
    s.append('<rect class="bar off" x="790" y="%d" width="8" height="18"/>' % (ky - 14))
    s.append('<text class="key" x="806" y="%d">set off the chain</text>' % ky)
    s.append('<text class="foot" x="1036" y="%d">data/control_map.json · data/numbers.json</text>' % ky)
    s.append("</svg>")

    out = repo / "docs" / "levers.svg"
    text = "\n".join(s) + "\n"
    if verify:
        same = out.exists() and out.read_text(encoding="utf-8") == text
        print("OK: docs/levers.svg is the picture drawn from data/numbers.json" if same
              else "DIFFERS: run python scripts/levers_chart.py")
        sys.exit(0 if same else 1)
    out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (out, out.stat().st_size))


if __name__ == "__main__":
    main()
