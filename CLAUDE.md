# Checking this repository

Steps for an automated reviewer to check the claims in [README.md](README.md). Claude Code reads `CLAUDE.md`,
Codex reads `AGENTS.md`; the two files are identical (`tests/test_remeasure.py` fails otherwise). This file
contains no measured number and states no conclusion: the claims and their numbers are in the README, the
numbers come from [`data/numbers.json`](data/numbers.json), and each section below says how to check them.

Requirements: Python 3.10 or later (`python` below, `python3` on some systems), standard library only. No
`pip install`, no API keys. No command here signs anything or writes to the chain.

## 1. Offline check (no network, under two minutes)

Run from the repository root. One command runs every check below in order:

```
python scripts/rebuild.py
```

Its last line is `REBUILD: PASS`. The same checks, one by one:

| Command | What it checks | Last line when it passes |
|---|---|---|
| `python -m unittest discover -s tests` | every script's logic on simulated chains and APIs | `OK` |
| `python scripts/build_numbers.py --verify` | every script's own offline check, then `numbers.json` rebuilds byte for byte | starts with `VERIFY: PASS (PUBLIC_REDACTED)` |
| `python scripts/build_numbers.py --check README.md` | every marked number in the README equals `numbers.json` | `OK: <count> marked numbers in README.md match numbers.json` |
| `python scripts/build_numbers.py --check docs/DETAILS.md` | the same for `docs/DETAILS.md` (method, live checks, terms) | `OK: <count> marked numbers in DETAILS.md match numbers.json` |
| `python scripts/build_numbers.py --check THESIS.md` | the same for `THESIS.md` (claim, evidence for and against) | `OK: <count> marked numbers in THESIS.md match numbers.json` |
| `python scripts/upgrade_watch.py --verify` | the validators' vote samples recompute | `OK: <count> day(s) recompute from the saved samples` |
| `python scripts/check_prereg.py --file` | `PREREG.md` hashes to the SHA-256 anchored on chain (saved copy of the record) | `OK: PREREG.md is the anchored file` |
| `python scripts/judge_prereg2.py --verify` | `PREREG-2.md`'s judged predictions recompute from the saved RPC responses | `OK: P4 holds (…)` |
| `python scripts/check_prereg.py --anchor 2 --verify` | `PREREG-2.md` equals its SocialDB record and the anchoring transaction's args | `OK: raw sha256 match, PREREG-2.md = …` |
| `python scripts/peers.py --verify` | the peer table recomputes from the saved DefiLlama and CoinGecko responses | `OK: NEAR (NEAR Intents): mcap/revenue …` |
| `python scripts/demand.py --verify` | NEAR Intents' 30-day volume ranking recomputes from the saved DefiLlama responses | `OK: NEAR Intents $… in 30 days, rank …` |
| `python scripts/sensitivity.py --verify` | the rating rules under 54 combinations of thresholds recompute; every month is Hold; and the lowest Avoid floors at which a month flips (`sens.flip.`) | `OK` |
| `python scripts/private_shift.py --verify` | what the three revenue wallets kept a day before and after 27 October (the private path), beside DefiLlama's revenue in NEAR and with four other cut dates, recomputes from the saved balances and one pinned DefiLlama fetch | `OK` |
| `python scripts/rating.py --verify` | the rating (Hold / Buy / Avoid) of every window in `data/rating.csv` recomputes from `history.csv` and the saved DefiLlama responses | `OK: rating.csv recomputes from history.csv and the saved responses` |
| `python scripts/backtest.py --verify` | the rating rules on each month April–October 2026 in `data/backtest.csv` recompute from `coverage_monthly.json` and the saved DefiLlama responses | `OK: backtest.csv recomputes from coverage_monthly.json and the saved DefiLlama responses` |
| `python scripts/quotes.py --verify` | each page the text quotes is saved under `data/raw/sources/` with its SHA-256 and contains the quote | `OK: <count> quotes found in <count> saved pages, and each is still in the text` |
| `python scripts/chart.py --verify` | the README's chart, `docs/coverage.svg`, is redrawn from `data/numbers.json` and must be identical | `OK: docs/coverage.svg is the chart drawn from data/numbers.json` |

Each passing command exits with code 0. Any other last line, or another exit code, is a failure.

**If your sandbox has no network**, this section is the whole check and needs nothing else. The dashboard works
offline too: `python -m http.server 8000` in the repository root, then `http://localhost:8000/dashboard/` (not
`file://`, where browsers block its data reads); only its "Check live" buttons need the RPC. Section 2 then stops
with `REMEASURE: NOT RUN - ...` and exit code 2: report it as not run, not as a failure. What offline cannot show is
that the saved raw responses are what the chain returned; section 2 and [Verify live](docs/DETAILS.md#verify-live)
do that with read-only calls.

`build_numbers.py --verify` prints one `OK` line per script before the verdict. `PUBLIC_REDACTED` means every
number was recomputed from files in git, some of them redacted copies (on a machine with the private originals it says
`FULL`); for the redacted lists (stakers, voters, validators) that proves
consistency and totals equal to the raw contract totals, not each entry. Responses that list people's accounts are not in git (see
[What is not in the repository](#what-is-not-in-the-repository)); offline, the verdict says which scripts have
such originals and that their match was not checked. Section 2 re-fetches them.

## 2. Re-measure from the chain (network, no keys, a few minutes)

```
python scripts/remeasure.py
```

Re-measures numbers 1 and 3 at the end of the locked window (first block at or after 1 November 2026
00:00 UTC) with the same code that made the saved files. It writes only into a new temporary folder and compares
with `data/history.csv` and `data/stakers/2026-11-01.json`. Last line when it passes: `REMEASURE: SAME`. Each
difference is printed as `DIFFERENT <field>: saved ..., now ...`. `--only 1` runs number 1 alone (about a
minute with a normal connection). Number 3 takes longer because NearBlocks is read without a key, with a 12-second
pause between pages. If the network refuses the RPC host (for example a sandbox proxy answering 403), it stops at
once with `REMEASURE: NOT RUN - ...` and exit code 2; a slow or flaky connection prints one line per retry.

The control map, the control history and the NEAR AI pool's flows re-fetch their locked blocks with:

```
python scripts/control_map.py --verify --archival
python scripts/control_history.py --verify --archival
python scripts/treasury_flows.py --verify --archival
```

Each exits with code 0 when the re-fetched answers give the saved results. Endpoints used:
`archival-rpc.mainnet.fastnear.com` and `api.nearblocks.io`. On HTTP 429 the scripts slow down and retry.

## 3. Live state (five read-only calls)

[docs/DETAILS.md, Verify live](docs/DETAILS.md#verify-live): five `curl` calls to a public RPC, with the answers saved at the
locked block for comparison. Live answers can differ from the locked block.

## Where each number comes from

Each entry of `data/numbers.json` has `value`, `text` (the README form), `source` (a file) and that file's
SHA-256. In the README, `THESIS.md` and `docs/DETAILS.md` each figure is wrapped as `<!--n:KEY-->text<!--/n-->`, where `KEY` is the entry.

| Key prefix | What | Script | Source file |
|---|---|---|---|
| `n1.` | Number 1: coverage of new supply by the buybacks wallets | `daily.py` | `data/daily/2026-11-01.json` |
| `n2.` | Number 2: ceiling if every DefiLlama fee were kept | `fees.py` | `data/fees_2026-10-02_2026-11-01.json` |
| `n3.` | Number 3: spread of NEAR AI staking | `stakers.py` | `data/stakers/2026-11-01.json` |
| `f1.`, `f2.` | Monthly coverage; fees and take rate | `coverage.py`, `fees.py` | `data/coverage_monthly.json`, fees file |
| `f4.` | NEAR AI pool owner's flows | `treasury_flows.py` | `data/treasury_flows.json` |
| `f5.`, `f7.` | Concentration over time; Agents locks | `stakers.py` | `data/stakers/*.json` |
| `f6.` | Farm reward rate and credits | `farm_rate.py`, `stakers.py` | `data/farm_rate.json`, `data/offchain/` |
| `f8.` | HSP-029 vote, at its last block | `hsp029.py`, `hsp029_voters.py` | `data/hsp029.json`, `data/hsp029_voters.json` |
| `f9.`, `iv.` | Front-end share; investment view (derived) | `build_numbers.py` | files named in each entry |
| `b.` | Gross issuance and gas burnt | `burn.py` | `data/burn.json` |
| `ts.` | `treasury.near`: reward rule, 2026 inflows and outflows | `treasury_spend.py` | `data/treasury_spend.json` |
| `te.` | `treasury.near`: each outflow's block and receiver | `treasury_exits.py` | `data/treasury_exits.json` |
| `c.` | Control map | `control_map.py` | `data/control_map.json` |
| `h.` | Control history | `control_history.py` | `data/control_history.json` |
| `tt.` | Where `treasury.near`'s April-May payout went next | `treasury_trace.py` | `data/treasury_trace.json` |
| `ct.` | What the Confidential Intents Treasury account holds | `confidential_treasury.py` | `data/confidential_treasury.json` |
| `pr.` | Pre-registrations: anchors and judged predictions | `check_prereg.py`, `judge_prereg2.py` | `data/prereg*.json` |
| `d.` | NEAR Intents' 30-day volume and its rank in DefiLlama's lists | `demand.py` | `data/demand.json` |
| `lr.` | Issuance to 2031: growth needed, and April-October history | `longrun.py` (through `build_numbers.py`) | window, fees and coverage files |
| `peer.` | Market value against revenue, NEAR and peers | `peers.py` | `data/peers.json` |
| `bt.` | The rating rules on April to October 2026 | `backtest.py` | `data/backtest.json` |
| `ps.` | What the three revenue wallets kept before and after 27 October (the private path), DefiLlama's revenue in NEAR, other cut dates (`ps.cut.`) | `private_shift.py` | `data/private_shift.json` |
| `sc.` | Three stated paths for a holder's dollars to 2031 (derived, no probability) | `build_numbers.py` | `peer.`, `lr.`, `iv.` entries |
| `sens.` | The rating under other thresholds, April-October 2026 | `sensitivity.py` | `data/sensitivity.json` |

All flows use one window: `data/window_2026-10-02_2026-11-01.json` (`lock_window.py`), blocks 218,126,921 →
222,491,356. Public raw responses are under `data/raw/`, byte for byte.

An entry with no `status` is final for that window. Other values:

- `provisional`: based on DefiLlama, final only when its data settles (rule in [docs/DETAILS.md, Method](docs/DETAILS.md#method)).
- `pending`: measured after an on-chain vote closes.
- `off-chain`: NEAR AI Cloud's credit setting, read once in a signed-in session (`data/offchain/`); it cannot be
  re-read without an account.
- `not-measured`: stated as not measured, with the reason in the entry.

To list them: `python -c "import json,collections; n=json.load(open('data/numbers.json'))['numbers']; print(collections.Counter(v.get('status','final') for v in n.values()))"`

## What is not in the repository

- `data/private/` (in `.gitignore`): responses that list people's accounts (stake.dao positions and locks,
  NearBlocks pages, DAO proposal texts, validators, voters). Public files keep each one's SHA-256 and the exact
  request. Numbers are computed from redacted copies under `data/raw/redacted/` (and the account lists inside
  `data/stakers/`), where people's accounts appear as `sha256:` tags. Section 2 re-fetches the originals.
- Until commit `7851eb5` the raw stake.dao responses, with account IDs, were committed; they remain in the git
  history (disclosed in [docs/DETAILS.md, Method](docs/DETAILS.md#method)).
- The research notes written before the first commit (disclosed in
  [README, Timeline and disclosure](README.md#timeline-and-disclosure)).
