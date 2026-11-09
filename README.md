# NEAR to 2031: value capture is real, small and discretionary

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**NEAR Intents has real demand, but only a small part of what users pay reaches NEAR holders, and how much is decided by a few signers, not by code.** So the rating is **Hold**: keep the NEAR you own, staked, and do not add until the buybacks become a published rule. Horizon 1 January 2031, checked every year.

**[Live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/)** · [Check it in two minutes](#check-it-in-two-minutes) · [One-page thesis](THESIS.md) · [Every detail](docs/DETAILS.md) · [Terms](#terms) · Window: 2 October → 1 November 2026 · As of 9 November 2026; figures from other dates say so where they appear

## In sixty seconds

- **The demand is real.** Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees on NEAR Intents in the window, by DefiLlama's data.
- **Holders get a small part of it.** The buybacks wallets keep NEAR equal to <!--n:n1.coverage_buybacks-->10.8%<!--/n--> of the new NEAR issued (<!--n:n1.coverage_with_front_end-->16.5%<!--/n--> counting the front-end fund), and burn none of it.
- **It is a policy, not a rule.** No code requires the buybacks, and <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can move what the buybacks wallet holds.
- **It held when the flow went private.** Since 27 October most NEAR Intents flow settles on its private path. On mainnet the buybacks kept <!--n:ps.after.kept_near_per_day-->10,071<!--/n--> NEAR a day from then to 8 November, against <!--n:ps.before.kept_near_per_day-->9,154<!--/n--> before; DefiLlama's revenue over the same days: <!--n:ps.change.revenue_usd_per_day-->-21%<!--/n-->.
- **Staking is what pays.** Staked, your share of all NEAR grows +<!--n:iv.staked_share_growth-->2.44%<!--/n--> a year before the validator's commission; unstaked, it changes <!--n:iv.unstaked_share_change-->-2.40%<!--/n-->.
- **What would change the rating.** Buy if the buybacks become a published rule and grow fast enough to cover issuance by 2031 (+<!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year); Avoid if they stop. Until 1 December 2026 the rules can only give Hold, because they need two windows of history.

## The thesis in four claims

Each claim gives what we found, what argues against it, and the command that recomputes it with no network. Every figure in this file comes from [`data/numbers.json`](data/numbers.json), and a check fails if one differs.

### A. The demand is real

NEAR Intents moved <!--n:d.ours_30d_usd-->$4.02B<!--/n--> in DefiLlama's 30 days to <!--n:d.window_end-->7 November<!--/n--> (its latest 30 days at the fetch, not the window): <!--n:d.parent_rank-->15th<!--/n--> of <!--n:d.parent_groups_with_volume-->885<!--/n--> protocols in DefiLlama's DEX-volume overview, with each protocol's versions counted as one. Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees in the window, <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume. The fee in the contract is only <!--n:c.intents_fee_pips-->1 pip<!--/n--> (<!--n:c.intents_fee_percent-->0.0001%<!--/n-->); what users pay is set off-chain, by NEAR Intents' terms and by the apps that route swaps to it.

**Against.** Volume and fees are DefiLlama's, from NEAR's datasets on Dune, and are not rebuilt from the chain here. Counted in NEAR, fees fell <!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n--> from April to October while the price rose <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n-->. "Real" means what can be shown: users pay these fees in DefiLlama's data, and NEAR arrives in the buybacks wallets on mainnet. No swap from fee income to those inflows is traced.

**Check.** `python scripts/demand.py --verify` → `OK`.

### B. It is small

Each day the buybacks wallets keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> NEAR, against <!--n:n1.new_near_per_day-->88,392<!--/n--> new NEAR issued: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n-->, or <!--n:n1.coverage_with_front_end-->16.5%<!--/n--> counting the front-end fund. If NEAR kept every fee, coverage would be <!--n:n2.max_coverage-->47.9%<!--/n-->; fees alone would cover issuance only at a NEAR price of <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less. New NEAR adds <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> to supply a year, worth <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n-->, against <!--n:iv.buybacks_kept_usd_per_year-->$17.1M<!--/n--> kept by the buybacks.

**Against.** Coverage is counted in NEAR and revenue is earned in dollars, so coverage falls when the price rises. In dollars the buybacks kept <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> as much a day in October as in April, of which <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n--> is the price.

**Check.** `python scripts/daily.py --verify`; `python scripts/coverage.py --verify`. Each ends with `OK`.

### C. It is a policy, not a rule

Nothing in code burns, locks or requires the buybacks, and every link can be changed by people:

1. **The bought NEAR can move.** The <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR the wallets hold can be moved by their signers: <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> for the buybacks wallet, <!--n:c.front_end_transfer-->2 of 5<!--/n--> for the front-end fund.
2. **The treasury is managed, not coded.** The protocol treasury, `treasury.near`, is "currently managed by the NEAR Foundation" ([SEC filing](https://www.sec.gov/Archives/edgar/data/0002067111/000121390026103106/ea0306486-424b3_bitwise.htm)). It paid out <!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR in April and May 2026; on 1 November the three accounts that received it held <!--n:tt.first_receivers_held_near-->302<!--/n--> NEAR ([where it went](docs/DETAILS.md#where-the-treasury-payout-went)).
3. **One account set a rate.** One account changed the NEAR AI credits rate <!--n:f6.change1.ratio-->×2.0<!--/n--> on <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, with no DAO proposal, and the pool keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of staking rewards ([details](docs/DETAILS.md#the-near-ai-farm)).
4. **A vote is not a rule.** HSP-027 passed on 3 July 2026 and reached the chain <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days later, when validators ran the release. HSP-029, the issuance cut, passed on 2 November and waits for the same step.

**Against.** The policy has been kept: from April to October the wallets held on to <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of what flowed in. Seven months is not years. A policy kept long enough is worth almost as much as a rule, so this thesis prices the difference as the gap between Hold and Buy, not as a reason to sell.

**Check.** `python scripts/control_map.py --verify`; `python scripts/control_history.py --verify`; `python scripts/farm_rate.py --verify`; `python scripts/treasury_trace.py --verify`. Each ends with `OK`.

### D. It held when the flow went private

Private swaps on NEAR Intents settle on FAR, an instance that public indexers do not see; their funds pass through a Treasury account on the public chain. Tideline, another public repository on NEAR Intents, reads that account's transfers and reports private settlement growing from 27 October, with the account carrying 85% of the USD it counts on chain from 2 to 8 November ([THESIS](https://github.com/ervhint/tideline-thesis/blob/main/THESIS.md)). We took that date before looking at our own series, and read the buybacks wallets on mainnet, day by day:

| | 2–26 October | 27 October – 8 November | Change |
|---|---|---|---|
| NEAR the buybacks kept a day | <!--n:ps.before.kept_near_per_day-->9,154<!--/n--> | <!--n:ps.after.kept_near_per_day-->10,071<!--/n--> | <!--n:ps.change.kept_near_per_day-->+10%<!--/n--> |
| The same in dollars | <!--n:ps.before.kept_usd_per_day-->$45,242<!--/n--> | <!--n:ps.after.kept_usd_per_day-->$41,781<!--/n--> | <!--n:ps.change.kept_usd_per_day-->-8%<!--/n--> |
| DefiLlama's revenue a day, for context | <!--n:ps.before.revenue_usd_per_day-->$70,677<!--/n--> | <!--n:ps.after.revenue_usd_per_day-->$56,007<!--/n--> | <!--n:ps.change.revenue_usd_per_day-->-21%<!--/n--> |

The after-mean sits inside the range of every <!--n:ps.after.days-->13<!--/n--> consecutive days before (<!--n:ps.before_runs.lowest_kept_near_per_day-->8,596<!--/n--> to <!--n:ps.before_runs.highest_kept_near_per_day-->10,461<!--/n--> NEAR a day): capture did not leave with the flow, and the fall in dollars is the price. A reading built on public datasets alone would have shown a drop the chain does not. The Treasury account itself held <!--n:ct.priced_usd.2026-11-08-->$123.5M<!--/n--> on 8 November, <!--n:ct.stablecoins_usd.2026-11-08-->$37.4M<!--/n--> of it in stablecoins.

**Against.** Thirteen days are a short run, the last days of DefiLlama's series can still be revised, and we take Tideline's date without re-reading its transactions. What the buybacks receive does not show which fees paid for it. PREREG-3 tests the next 30 days.

**Check.** `python scripts/private_shift.py --verify`; `python scripts/confidential_treasury.py --verify`. Each ends with `OK`.

## What a holder earns to 2031

Your share of all NEAR, before the validator's commission (at an assumed 10%, the first figure is +<!--n:iv.staked_share_growth.commission_10-->1.95%<!--/n-->). The buybacks hold what they buy, so they change neither row.

| | A year, today | To 1 Jan 2031, at today's rates | A year, with HSP-029 |
|---|---|---|---|
| Staked with a validator | +<!--n:iv.staked_share_growth-->2.44%<!--/n--> | +<!--n:iv.to2031.staked_share_change-->10.6%<!--/n--> | +<!--n:iv.hsp029.staked_share_growth-->1.57%<!--/n--> |
| Not staked | <!--n:iv.unstaked_share_change-->-2.40%<!--/n--> | <!--n:iv.to2031.unstaked_share_change-->-9.6%<!--/n--> | <!--n:iv.hsp029.unstaked_share_change-->-1.55%<!--/n--> |

In dollars, your holding changes by that share times the value of all NEAR. Three paths for that value, each built from figures in this repository, with no probability on any ([how](docs/DETAILS.md#three-paths-to-2031)):

| Path for the value of all NEAR, window to 1 Jan 2031 | All NEAR | Staked, in $ | Not staked, in $ |
|---|---|---|---|
| **Bear.** The buybacks stop, and NEAR is valued on its gas alone at the median of the four L1s in the peers table (<!--n:sc.l1_peer_median_multiple-->2,695×<!--/n--> a year of revenue) | <!--n:sc.bear.value_change-->-34%<!--/n--> | <!--n:sc.bear.staked_usd_change-->-27%<!--/n--> | <!--n:sc.bear.unstaked_usd_change-->-40%<!--/n--> |
| **Base.** The value of all NEAR stays at <!--n:sc.base.value_usd-->$6.39B<!--/n--> | <!--n:sc.base.value_change-->0%<!--/n--> | +<!--n:sc.base.staked_usd_change-->11%<!--/n--> | <!--n:sc.base.unstaked_usd_change-->-10%<!--/n--> |
| **Bull.** Intents' revenue grows at Buy's (a) pace, <!--n:sc.bull.capture_multiple-->×10.2<!--/n--> by 2031, and all NEAR keeps today's <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> of revenue | +<!--n:sc.bull.value_change-->871%<!--/n--> | +<!--n:sc.bull.staked_usd_change-->973%<!--/n--> | +<!--n:sc.bull.unstaked_usd_change-->777%<!--/n--> |

From the window's mean price, <!--n:n2.mean_price_usd-->$4.88<!--/n-->; from the price at the peers fetch, <!--n:peer.near.price_usd-->$3.71<!--/n-->, the bear path is <!--n:sc.bear.value_change.at_fetch-->-13%<!--/n--> (<!--n:sc.bear.staked_usd_change.at_fetch-->-4%<!--/n--> staked). The base path is the staking rate on share. The bear path is what Avoid is built to catch. The bull path is what Buy asks for: capture <!--n:sc.bull.capture_multiple-->×10.2<!--/n--> in about four years. For scale, on its chain's gas alone NEAR's market value is <!--n:peer.near_l1.mcap_to_revenue-->4,091×<!--/n--> a year of that revenue, above Ethereum's <!--n:peer.ethereum.mcap_to_revenue-->3,394×<!--/n-->; counting Intents, <!--n:peer.near_all.mcap_to_revenue-->234×<!--/n--> ([peers](docs/DETAILS.md#peers-on-one-basis)).

## The rating as rules

`scripts/rating.py` applies these to every 30-day window and writes [`data/rating.csv`](data/rating.csv). Today it is Hold in every window, and until 1 December it cannot be anything else: Avoid needs a failing window 30 days earlier and the daily history starts on 1 November, and Buy needs (b), a lock that does not exist. Read the rules as a monitor that can fire from then on, not as evidence for Hold.

| | Rule | Read from |
|---|---|---|
| **Buy** | (b) a published rule keeps the buybacks: a declared lock with no contract and no access keys; **and** `treasury.near` sent nothing in the window; **and** either the NEAR the buybacks keep, capped at DefiLlama's revenue and fees, covers issuance, or at the yearly check it has grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year in dollars and in NEAR | the chain; DefiLlama for the caps |
| **Avoid** | this 30-day window and the one ending 30 days before it each fail a test: (1) the wallets keep less than 75% of DefiLlama's revenue; (2) the buybacks keep April's <!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day or less. If DefiLlama's revenue is zero or a day is missing, test 1 is not judged and test 2 decides alone. Test 2 is not judged when DefiLlama's fees fell too and the Confidential Intents Treasury account grew, so capture that moved to the private path is not rated as capture that stopped | (1) DefiLlama; (2) the chain, and the Treasury account on it |
| **Hold** | everything else, including any window that cannot be judged | |

Avoid overrides Buy. The rating asks one question: does a rule, rather than a choice, pay holders for the NEAR issued? It sets no price target, because L1 tokens are not priced on fees and a target drawn from fees would be conviction, not evidence. Avoid's dollar test also fires on a crash alone: at this window's NEAR kept a day, at a price of <!--n:iv.avoid_test2_price_usd-->$0.655<!--/n--> or less. Every rule, edge case and the backtest on April to October: [the rating in full](docs/DETAILS.md#the-rating-in-full).

## Predictions, anchored before they are judged

Each file's SHA-256 is anchored on NEAR mainnet, in SocialDB (`social.near`), before its predictions are judged, and no file has been amended since: `python scripts/check_prereg.py --file` (add `--anchor 2` or `--anchor 3` for the others) compares each file with its anchored hash, with no network. Results go into this repository whatever they are ([details](docs/DETAILS.md#pre-registration)).

| File | Prediction | Probability | Result |
|---|---|---|---|
| [PREREG-2](PREREG-2.md) #4 | process check: HSP-027 in effect by 6 Nov | 0.85 | <!--n:pr.4.result-->holds<!--/n-->, Brier <!--n:pr.4.brier-->0.0225<!--/n--> |
| [PREREG-2](PREREG-2.md) #5 | process check: protocol version 88 by 8 Nov | 0.75 | <!--n:pr.5.result-->holds<!--/n-->, Brier <!--n:pr.5.brier-->0.0625<!--/n--> |
| [PREREG](PREREG.md) #1–3 | the NEAR AI farm; buybacks inflows 1–15 Nov | — | judged 16 Nov |
| [PREREG-3](PREREG-3.md) #6–8 | the buybacks keep at least half / all of the 2 October window's dollars, 9 Nov – 9 Dec; DefiLlama has every day | 0.90 / 0.75 / 0.90, measured from history | judged 9 and 11 Dec |

No prediction that tests the thesis has a result yet: #4 and #5 only show that the pipeline works (Brier: 0 is perfect, 0.25 is always saying 0.5). #1–3 and #6–8 are judged after the submission deadline. PREREG-3 was anchored at block <!--n:pr.anchor3.tx_block-->223,613,293<!--/n-->, before its window opened; its probabilities are base rates from history, about 5 independent windows, and its baseline of $46,691.40 a day is the <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n--> used elsewhere before rounding the price.

## What would change our mind

| When | What we watch | If it happens |
|---|---|---|
| 9 Nov – 9 Dec | what the buybacks wallets keep, now that the private path is the main one | PREREG-3 scores it; the rating's own tests run every day |
| any day | a published buyback rule, or a keyless lock | (b) is met; Buy then depends on coverage |
| when validators run HSP-029 | issuance falls | the Buy hurdle drops to <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> |
| any day | `treasury.near` sends anything | the Buy path is closed for that window |
| 1 Nov 2027 | first yearly check | Buy only if +75% (or +56%) is met in dollars and in NEAR |

## Check it in two minutes

Python 3.10 or later (`python3` on some systems, `py` on Windows), standard library only, no network, no keys. From the repository root:

```
python scripts/rebuild.py
```

It ends with `REBUILD: PASS`: every test passes, every number recomputes from the saved raw responses, and every number on this page matches [`data/numbers.json`](data/numbers.json). The same, step by step:

```
python -m unittest discover -s tests              # every script's logic on fixed inputs
python scripts/build_numbers.py --verify           # every script's offline check, then numbers.json rebuilds the same
python scripts/build_numbers.py --check README.md  # every marked number in this file matches numbers.json
python scripts/check_prereg.py --anchor 3 --verify # PREREG-3.md = its SocialDB record = the transaction's args
python scripts/rating.py --verify                  # the rating of every window recomputes
python scripts/quotes.py --verify                  # every quoted line is in its saved page
```

For lists that name accounts, git holds redacted copies: offline, the check proves they are consistent and that their totals match the raw contract responses, not that each entry is right.

**No network is needed for anything above.** What does need it, and what to do offline instead:

| Needs the network | Offline |
|---|---|
| The [live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/) | `python -m http.server 8000` in the repository root, then open `http://localhost:8000/dashboard/` (opening the file directly does not work: browsers block its data reads from `file://`). Every figure is read from `data/numbers.json`; only the "Check live" buttons say they cannot reach the RPC. |
| Re-measuring from the chain | `python scripts/remeasure.py --only 1` stops at once with `REMEASURE: NOT RUN - ...` and exit code 2. That is the expected result offline, not a failure of the repository. |
| Reading the SocialDB anchors | `python scripts/check_prereg.py --anchor 3 --verify` checks the saved record and transaction offline. |
| The pages the text quotes (SEC filings, NEAR's docs and blog, the hackathon rules) | each is saved in `data/raw/sources/` with its SHA-256; `python scripts/quotes.py --verify` checks that every quote is in its saved page (`rebuild.py` runs it). |

Offline, the one thing that cannot be proven is that the saved responses are what the chain returned. That takes one read-only call per number, listed with the expected answers in [Verify live](docs/DETAILS.md#verify-live).

## What we can't measure

- **The fees themselves.** They come from NEAR's datasets on Dune and cannot be rebuilt from the chain here; only the revenue side is checked on chain, through the wallets' balances.
- **The private path.** Volume and fees on FAR are not visible; we read only what the Treasury account holds on mainnet.
- **Who holds an account, and why NEAR moved.** Amounts, blocks and transactions are measured; purposes are not on chain.
- **Credits in dollars** for the NEAR AI farm: an off-chain setting that can change with no trace on chain.
- **Peers' mechanisms** are compared from their docs; their numbers are DefiLlama's and CoinGecko's.

## Terms

- **Buybacks wallets:** `buybacks.multisignature.near` and `1csfundsadmin.sputnik-dao.near`, where NEAR bought with NEAR Intents' fees is kept.
- **Front-end fund:** `fefundsadmin.sputnik-dao.near`, a separate DAO that holds near-intents.org's own fees.
- **Coverage:** NEAR the buybacks wallets keep ÷ new NEAR issued, over the same 30 days.
- **(a)** the growth test for Buy: what the buybacks keep grows <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year, in dollars and in NEAR. **(b)** the rule test: a published lock that no one can spend from.
- **FAR:** NEAR Intents' private instance; swaps settled there are not visible to public indexers.
- **HSP-027 / HSP-029:** House of Stake proposals: remove the developer gas rebate (in force) and cut issuance (passed, not yet in force).
- **pip:** a millionth of the amount (1 pip = 0.0001%).
- More: [Terms](docs/DETAILS.md#terms).

## Timeline and disclosure

- Research into data sources: 22–31 October 2026, in private notes that are not part of this repository.
- Code and data: from the first commit, 2026-10-31 13:51:52 UTC; there is no earlier code. The [rules](https://nearhackathon.com/HACKATHON.md) (FAQ Q-001) count work from the hackathon's announcement on 19 October: "Earlier commits are baseline".
- Sources: NEAR archival RPC, the NearBlocks API, DefiLlama and coins.llama.fi, SEC filings and NEAR's own docs, linked where used, and one off-chain read of a NEAR AI Cloud setting. Raw responses are saved byte for byte; those that list people's accounts are kept private, with their SHA-256.
- AI: the code, scripts and text were written with Claude Code (Anthropic), directed by the author; those commits are marked `Co-Authored-By: Claude`.
- Libraries: none beyond the Python standard library. `docs/sign*.html` load NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
