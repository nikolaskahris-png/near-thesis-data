# NEAR to 2031: value capture is real, small and discretionary

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

**For each $1 of new NEAR issued, NEAR Intents' buybacks buy and hold NEAR worth about <!--n:iv.cents_per_new_dollar-->11 cents<!--/n-->, and <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can move it.** None of it is burned.

**Rating to 2031: Hold.** Keep the NEAR you own staked. Do not add more.

**What would change it.** Buy needs the buybacks in a lock that the chain shows cannot send NEAR out, plus either buybacks that match all new NEAR (<!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> today's pace), or growth of <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year from 1 November. Avoid comes at once if the amount of NEAR the buybacks hold falls more than 10% below its highest ([all the rules](#the-rating-as-rules)).

![What holders get for the NEAR issued, a day: the buybacks keep about a tenth of it, and all fees together would cover less than half](docs/coverage.svg)

**[Live dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/)** · [Check it with one command](#check-it-with-one-command) · [How NEAR is used](#how-near-is-used) · [One-page thesis](THESIS.md) · [Objections we expect](#objections-we-expect) · [Every detail](docs/DETAILS.md) · [Terms](#terms) · Window: 2 October → 1 November 2026; any other date is named where used

## The short version

- **The question.** Cases for NEAR cite NEAR Intents' trading. They do not say how much reaches a holder, or who decides. We measure both on mainnet.
- **The demand is real.** Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees on NEAR Intents in the window, by DefiLlama's data.
- **Holders get a small part.** The buybacks keep <!--n:iv.buybacks_kept_usd_per_year-->$17.1M<!--/n--> a year, against <!--n:iv.issuance_usd_per_year-->$157.5M<!--/n--> of new NEAR, at the window's pace: <!--n:n1.coverage_buybacks-->10.8%<!--/n-->. By calendar month since April it ran from <!--n:f1.coverage_buybacks.2026-04-->5.3%<!--/n--> to <!--n:f1.coverage_buybacks.2026-09-->15.3%<!--/n-->. Counting the front-end fund, the third revenue wallet, it is <!--n:n1.coverage_with_front_end-->16.5%<!--/n-->. The bought NEAR is held, not burned, so your share of all NEAR does not change.
- **People decide.** Issuance changes only through a release run by validators with <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake. The buybacks are a choice that <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers can undo.
- **It held when swaps went private.** After 27 October, the three revenue wallets kept nearly as much NEAR a day as before: <!--n:ps.change.kept_near_per_day-->-3%<!--/n-->. [Claim D](#d-it-did-not-stop-when-the-flow-went-private) has other start dates and the dollar figures.
- **Why not add.** Holders' revenue is <!--n:peer.near.holders_yield_on_mcap-->0.40%<!--/n--> of NEAR's value a year, by DefiLlama's count. Hyperliquid's is <!--n:peer.hyperliquid.holders_yield_on_mcap-->4.09%<!--/n--> of its circulating value and <!--n:peer.hyperliquid.holders_yield_on_fdv-->1.03%<!--/n--> of its fully diluted value ([peers](docs/DETAILS.md#peers-on-one-basis)), and the tokens it buys go to an address with no private key ([The Block](https://www.theblock.co/news/defi/2025-12-17-hyper-foundation-proposes-removing-1-billion-hype-tokens-from-circulating-supply-by-zeroing-out-hyperliquids-assistance-fund-383091)). And the latest proposal would delay what holders get: a House of Stake draft of 8 November, with no number yet, would put a share of NEAR Intents' fees in US Treasury bills, with buybacks or dividends only after venture exits ([saved copy](data/raw/sources/hos_draft_2026_11_08.md), [gov.near.org](https://gov.near.org/t/hsp-xxx-sovereign-yield-engine-treasury-backed-venture-protocol-buyback-model-for-near-intents/42760)).
- **Growth is not what blocks Buy first.** Since April the buybacks grew <!--n:bt.a_pace.near_multiple-->×2.1<!--/n--> in NEAR, faster than <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year. But most of that came from NEAR's share of fees rising <!--n:lr.history.2026-04_2026-10.take_rate_multiple-->×4.2<!--/n-->, which cannot rise forever, and measured from August or September the pace falls short. Buy counts growth from 1 November, and it needs a lock first.
- **What to do.** Staked, your share of all NEAR grows +<!--n:iv.staked_share_growth-->2.44%<!--/n--> a year, before your validator's fee. Unstaked, it changes <!--n:iv.unstaked_share_change-->-2.40%<!--/n-->.

## What to watch from Monday, 16 November

- The bought NEAR, every day. If it falls more than 10% below its peak since 1 November, the rating turns to Avoid at once. The [dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/) reads it live from the chain, in your browser.
- The House of Stake draft of 8 November. Watch whether it gets a number and goes to a vote.
- HSP-029, the issuance cut, leaves its timelock at <!--n:f8.timelock_end_utc-->2026-11-16 16:48 UTC<!--/n-->. It cuts issuance only once validators with 4/5 of stake run a release.
- From 10 December, the two 30-day revenue tests in [the rules](#the-rating-as-rules) can also turn the rating to Avoid.

## The thesis in four claims

Each marked figure comes from [`data/numbers.json`](data/numbers.json), and a check fails if one differs. Each claim in full, with every source: [long version](docs/DETAILS.md#v4-the-thesis-in-four-claims).

### A. The demand is real

NEAR Intents moved <!--n:d.ours_30d_usd-->$4.02B<!--/n--> in the 30 days to <!--n:d.window_end-->7 November<!--/n-->, <!--n:d.parent_rank-->15th<!--/n--> of <!--n:d.parent_groups_with_volume-->885<!--/n--> protocols by DEX volume on DefiLlama. Users paid <!--n:n2.fees_usd_per_day-->$206,049<!--/n--> a day in fees in the window, <!--n:n2.fees_bps-->16.0<!--/n--> bps of volume, most of it to the apps that route swaps; the contract's own fee is <!--n:c.intents_fee_pips-->1 pip<!--/n-->.

**Against.** Volume and fees are DefiLlama's, not rebuilt from the chain. In NEAR, fees halved (<!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n-->) from April to October while the price rose <!--n:lr.history.2026-04_2026-10.mean_price_multiple-->×3.6<!--/n-->. Two other public repositories count what they see on chain at 46% of DefiLlama's volume (all swaps, six sampled days) and 24% (stablecoin legs only), so DefiLlama may count both sides of a swap or swaps on the private path; coverage and the rating use fees and wallet balances, not volume.

**Check.** `python scripts/demand.py --verify` → `OK`.

### B. It is small

Each day the buybacks wallets keep <!--n:n1.buybacks_near_per_day-->9,570<!--/n--> NEAR, against <!--n:n1.new_near_per_day-->88,392<!--/n--> new NEAR issued: coverage <!--n:n1.coverage_buybacks-->10.8%<!--/n-->. If NEAR kept every fee, third-party apps' included, coverage would be <!--n:n2.max_coverage-->47.9%<!--/n-->; fees alone would cover issuance only at a NEAR price of <!--n:n2.equilibrium_price_usd-->$2.33<!--/n--> or less. New NEAR adds <!--n:iv.issuance_rate_per_year-->2.46%<!--/n--> to supply a year.

**Against.** Coverage is counted in NEAR and revenue is earned in dollars, so coverage falls when the price rises. In dollars the buybacks kept <!--n:lr.history.2026-04_2026-10.buybacks_kept_usd_multiple-->×7.5<!--/n--> as much a day in October as in April.

**Check.** `python scripts/daily.py --verify`; `python scripts/coverage.py --verify`. Each ends with `OK`.

### C. It is a policy, not a rule

Nothing in code burns, locks or requires the buybacks:

1. **The NEAR they hold can move.** The <!--n:n1.wallets_held_near-->4,109,089<!--/n--> NEAR in the three revenue wallets moves with <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> signers for each buybacks wallet and <!--n:c.front_end_transfer-->2 of 5<!--/n--> for the front-end fund.
2. **A passed vote is not yet a rule.** HSP-027 passed on 3 July 2026 and reached the chain <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days later, once validators ran a release. HSP-029, the issuance cut, passed on 2 November and waits for the same step.
3. **Other links work the same way.** The protocol treasury and NEAR AI's staking pool and credits are also set by a few accounts. The rating does not use them ([the other links](docs/DETAILS.md#the-control-map-other-links)).

**Against.** The policy has been kept: from April to October the three wallets held on to <!--n:f2.wallets_kept_share_of_revenue.2026-04_2026-10-->96.9%<!--/n--> of what flowed in. Holding a reserve rather than burning is a stated choice (a co-founder's [sovereign-fund post](https://gov.near.org/t/near-governance-discussion-sovereign-fund/42419), 3 August 2026); we rate whether it is fixed, not whether it is wise. A policy kept for years is worth almost as much as a rule, so the gap costs Buy, not Hold.

**Check.** `python scripts/control_map.py --verify`; `python scripts/control_history.py --verify`. Each ends with `OK`.

### D. It did not stop when the flow went private

From 27 October swaps began to settle privately on FAR (contract `intents.far`), unseen by public indexers; from 2 to 8 November that path carried 85% of the dollars counted on chain ([Tideline at commit 90a78e6](https://github.com/ervhint/tideline-thesis/blob/90a78e6a358315331dbb0c68548edcb736244a3e/THESIS.md), another public repository). We read the three revenue wallets daily on mainnet; DefiLlama's revenue counts the same three, so the two compare like for like:

| A day, in NEAR | 2–26 October | 27 October – 8 November | Change |
|---|---|---|---|
| Kept by the three wallets | <!--n:ps.before.kept_near_per_day-->14,261<!--/n--> | <!--n:ps.after.kept_near_per_day-->13,800<!--/n--> | <!--n:ps.change.kept_near_per_day-->-3%<!--/n--> |
| DefiLlama's revenue | <!--n:ps.before.revenue_near_per_day-->14,323<!--/n--> | <!--n:ps.after.revenue_near_per_day-->13,514<!--/n--> | <!--n:ps.change.revenue_near_per_day-->-6%<!--/n--> |

In dollars both fell about a fifth (<!--n:ps.change.kept_usd_per_day-->-19%<!--/n--> and <!--n:ps.change.revenue_usd_per_day-->-21%<!--/n-->), mostly the price. The private path's account on mainnet held <!--n:ct.priced_usd.2026-11-08-->$123.5M<!--/n--> on 8 November, <!--n:ct.stablecoins_usd.2026-11-08-->$37.4M<!--/n--> of it in stablecoins.

**Against.** Thirteen days are a short run. Tideline's date gives the smallest fall of the five dates tried; from 30 October it is <!--n:ps.cut.2026-10-30.kept_near-->-13%<!--/n-->, from 2 November, the first day of the 85% week, <!--n:ps.cut.2026-11-02.kept_near-->-8%<!--/n-->. Agreement shows little flowed out, not which fees paid for what came in. [PREREG-3](PREREG-3.md) tests the next 30 days.

**Check.** `python scripts/private_shift.py --verify` → `OK`.

## What a holder earns to 2031

How your share of all NEAR changes. HSP-029 is assumed in force from <!--n:lr.activation_utc-->2027-02-14 16:48 UTC<!--/n-->; the 10% commission is assumed, not read. The buybacks are held, not burned, so they leave your share of all NEAR unchanged; only staking moves it.

| | A year, today | To 1 Jan 2031, today's rule | To 1 Jan 2031, with HSP-029 |
|---|---|---|---|
| Staked, before commission | +<!--n:iv.staked_share_growth-->2.44%<!--/n--> | +<!--n:iv.to2031.staked_share_change-->10.6%<!--/n--> | +<!--n:iv.to2031.staked_share_change.hsp029-->7.9%<!--/n--> |
| Staked, after a 10% commission | +<!--n:iv.staked_share_growth.commission_10-->1.95%<!--/n--> | +<!--n:iv.to2031.staked_share_change.commission_10-->8.4%<!--/n--> | **+<!--n:iv.to2031.staked_share_change.hsp029_commission_10-->6.3%<!--/n-->** |
| Not staked | <!--n:iv.unstaked_share_change-->-2.40%<!--/n--> | <!--n:iv.to2031.unstaked_share_change-->-9.6%<!--/n--> | <!--n:iv.to2031.unstaked_share_change.hsp029-->-7.4%<!--/n--> |

In dollars, your holding is that share times the value of all NEAR. No price target: L1 tokens are not priced on fees. Three stated paths and their wide range: [paths to 2031](docs/DETAILS.md#v4-what-a-holder-earns-to-2031).

## The rating as rules

`scripts/rating.py` applies these rules every day to each 30-day window, and writes [`data/rating.csv`](data/rating.csv). They ask one question: does a rule, rather than a choice, pay holders for the NEAR issued?

| Rating | When | Read from |
|---|---|---|
| **Avoid** (overrides Buy) | **Either** the bought NEAR at a window's end (the two buybacks wallets, their wNEAR in Intents, any declared lock) is more than 10% below its highest since 1 November. Avoid starts at once and stays until it is back within 10%.<br>**Or** this window and the one ending 30 days earlier each fail one of two tests: (1) the three revenue wallets keep less than 75% of DefiLlama's revenue; (2) the buybacks keep April's <!--n:f2.buybacks_kept_usd_per_day.2026-04-->$6,270<!--/n--> a day or less. | the chain; DefiLlama for test 1 |
| **Buy** | **All three:**<br>1. The buybacks sit in a declared lock that the chain shows cannot send NEAR out. That is an account with no contract and no access keys, or a contract whose code hash we reviewed and listed (`AUDITED_CODE`, none yet) with no full-access key.<br>2. `treasury.near` sent nothing in the window.<br>3. The buybacks cover issuance, or at the yearly check on 1 November they have grown <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year, in dollars and in NEAR. | the chain; DefiLlama caps what counts |
| **Hold** | Everything else, including any window that cannot be judged. | |

Notes on the rules:

- A buy-and-burn or lock contract counts once we have reviewed its code and listed its hash. An upgrade has a new hash and stops counting until it is reviewed. A contract another account can replace never counts.
- One transfer of the whole stock gives Avoid from the next daily window. A full stop of the buybacks would show as Avoid about eight weeks later.
- The drain test also reads NEAR staked or wrapped outside Intents as moved out.
- Test 2 is "not judged" when it fails while DefiLlama's fees fell and the stablecoins in the Confidential Intents Treasury rose. We read that pattern as flow moving to the private path. It is a proxy, not proof.
- **Why Hold today.** Until 10 December the rules give Hold, or Avoid on a drain. Buy needs a lock that does not exist. Across <!--n:sens.combinations-->54<!--/n--> threshold settings, <!--n:sens.hold-->378<!--/n--> of <!--n:sens.month_ratings-->378<!--/n--> monthly ratings from April to October are Hold. So the rules are an alarm, not the reason for Hold: the reasons are in [Why not add](#the-short-version).
- **A crash alone can trigger Avoid.** At this window's NEAR kept a day, test 2 fails at a price of <!--n:iv.avoid_test2_price_usd-->$0.655<!--/n--> or less.

Every rule, edge case and the backtest: [the rating in full](docs/DETAILS.md#the-rating-in-full).

## What would change our mind

- **Any day:** the buybacks stock falls more than 10% below its highest since 1 November: Avoid at once (it rose every day from 1 to 12 November).
- **10 December 2026 at the earliest, then daily:** Avoid can fire through the two window tests; the windows ending 1–9 November passed and are final.
- **9 December 2026:** if from 9 November the buybacks keep less than half of <!--n:iv.buybacks_kept_usd_per_day-->$46,692<!--/n--> a day, PREREG-3's P6 (0.90) is scored wrong, and claim D with it.
- **Any day:** a lock as the Buy rule defines it, plus coverage of 100% (best month so far <!--n:bt.highest_coverage_counted-->15.3%<!--/n-->) gives Buy.
- **1 November 2027, then yearly:** a lock plus the growth test (<!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> a year once validators run HSP-029) gives Buy.

**How likely a rule is.** **0.25** that the buybacks go to such a lock by 1 January 2031: our judgment, from three peers (Pump.fun sent half its revenue to a buy-and-burn contract for a year, the kind the Buy rule accepts once its code is reviewed; Jupiter burned once; Aave's sit in a reserve that can be spent) and NEAR's proposals so far, which point away from a lock. Buy also needs coverage or growth, so it is less likely ([sources](docs/DETAILS.md#how-likely-a-rule-is)).

## Objections we expect

- **"Hold is built into the rules."** The rules give Hold until the buybacks are locked, and today they are not. That is the finding: what holders lack is a rule. The distance to Buy is a lock plus <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> what the buybacks keep, or +75% a year of growth. Avoid can fire any day on a drain. What can prove the thesis wrong has dates: PREREG-3 is judged on 9 and 11 December, and coverage of 25% or more in three months running would end "small" ([the full list](THESIS.md#what-would-change-our-mind)).
- **"HSP-029 changes the arithmetic."** It does, once validators run it. With today's buybacks, holders would get about <!--n:iv.hsp029_cents_per_new_dollar-->17 cents<!--/n--> per $1 of new NEAR, and full coverage would need <!--n:iv.hsp029_wallets_multiple_buybacks-->×5.9<!--/n--> instead of <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n-->. Buy's growth test falls to <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> a year. The lock is still missing.
- **"Other repositories say 12–19%, not 10.8%."** They add burned gas, or count revenue instead of balances. Like for like, with all three revenue wallets, ours is <!--n:n1.coverage_with_front_end-->16.5%<!--/n-->, and full coverage is <!--n:iv.wallets_multiple_with_front_end-->×6.1<!--/n--> away rather than <!--n:iv.wallets_multiple_buybacks-->×9.2<!--/n--> ([the definitions side by side](docs/DETAILS.md#why-public-coverage-figures-differ)).
- **"Hyperliquid looks better only on circulating value."** Both bases are shown. On fully diluted value Hyperliquid's holders' revenue is <!--n:peer.hyperliquid.holders_yield_on_fdv-->1.03%<!--/n--> a year, against NEAR's <!--n:peer.near.holders_yield_on_mcap-->0.40%<!--/n-->.
- **"People decide issuance too."** A core team writes releases. But issuance changes only when validators with 4/5 of stake run one, and HSP-027 took <!--n:pr.v87.days_from_hsp027_passed-->124<!--/n--> days to reach the chain. The buybacks can move with two signatures, on any day.
- **"Holding a reserve is a sensible choice."** It may be. It is a stated choice (a co-founder's [sovereign-fund post](https://gov.near.org/t/near-governance-discussion-sovereign-fund/42419), 3 August 2026). We rate whether it is fixed, not whether it is wise.

## Predictions, anchored before they are judged

Each file's SHA-256 is anchored in SocialDB on mainnet before it is judged; none has been amended (`python scripts/check_prereg.py --file`). Results go in whatever they are ([details](docs/DETAILS.md#pre-registration)).

| File | Prediction | Probability | Result |
|---|---|---|---|
| [PREREG-2](PREREG-2.md) #4 | process check: HSP-027 in effect by 6 Nov | 0.85 | <!--n:pr.4.result-->holds<!--/n-->, Brier <!--n:pr.4.brier-->0.0225<!--/n--> |
| [PREREG-2](PREREG-2.md) #5 | process check: protocol version 88 by 8 Nov | 0.75 | <!--n:pr.5.result-->holds<!--/n-->, Brier <!--n:pr.5.brier-->0.0625<!--/n--> |
| [PREREG](PREREG.md) #1–3 | the NEAR AI farm; buybacks inflows 1–15 Nov | — | judged 16 Nov |
| [PREREG-3](PREREG-3.md) #6–8 | the buybacks keep at least half / all of the window's dollars, 9 Nov – 9 Dec; DefiLlama has every day | 0.90 / 0.75 / 0.90 | judged 9 and 11 Dec |

#4 and #5 only show the pipeline works; the thesis has no judged prediction yet. PREREG-3 was anchored at block <!--n:pr.anchor3.tx_block-->223,613,293<!--/n-->, before its window opened.

## Check it with one command

Python 3.10 or later (`python3` on some systems, `py` on Windows), standard library only, no network, no keys, about three minutes. From the repository root:

```
python scripts/rebuild.py
```

It ends with `REBUILD: PASS`: every test passes, every number recomputes from the saved raw responses, every marked number on this page matches [`data/numbers.json`](data/numbers.json), every quote is in its saved page, and the chart redraws the same. Each step, and what needs the network: [AGENTS.md](AGENTS.md). Lists that name accounts are redacted in git, so offline the check proves their totals, not each entry; that the saved responses are what the chain returned takes one read-only call per number ([Verify live](docs/DETAILS.md#verify-live)).

## How NEAR is used

- **Read.** The holder's side comes from NEAR mainnet by archival RPC: the buybacks wallets' balances, new NEAR issued, the multisig signers and keys, `treasury.near` and protocol upgrades.
- **Written.** Each prediction file's SHA-256 is anchored in SocialDB (`social.near`) on mainnet before it is judged, so a later edit would show.
- **Every day.** A GitHub Action re-reads the chain and re-runs the rating; the [dashboard](https://nikolaskahris-png.github.io/near-thesis-data/dashboard/) reads the drain test live from the chain, in your browser.

## What we can't measure

The fees (NEAR's datasets on Dune; only revenue is checked on chain), volume and fees on FAR, why NEAR moved (purposes are not on chain), the NEAR AI credits' dollar value (off-chain), and peers (from their docs, DefiLlama and CoinGecko).

## Terms

- **Buybacks wallets:** `buybacks.multisignature.near` and `1csfundsadmin.sputnik-dao.near`, where NEAR bought with NEAR Intents' fees is kept.
- **Front-end fund:** `fefundsadmin.sputnik-dao.near`, a separate DAO that holds near-intents.org's own fees. With the two above, the **three revenue wallets**.
- **Coverage:** NEAR the buybacks wallets keep (inflows less outflows) ÷ new NEAR issued (minted less gas burnt), over the same 30 days.
- **FAR:** a private instance of the NEAR protocol, run by a small validator set; NEAR Intents' contract there is `intents.far`. Swaps settled there are not visible to public indexers.
- **HSP-027 / HSP-029:** House of Stake proposals: end the developer gas rebate (in force); cut issuance (passed, not in force).
- **pip:** a millionth (0.0001%).
- More: [Terms](docs/DETAILS.md#terms).

## Timeline and disclosure

- Research into data sources: 22–31 October 2026, in private notes that are not part of this repository.
- Code and data: from the first commit, 2026-10-31 13:51:52 UTC; there is no earlier code. The [rules](https://nearhackathon.com/HACKATHON.md) (FAQ Q-001) count work from the hackathon's announcement on 19 October: "Earlier commits are baseline".
- Sources: NEAR archival RPC, NearBlocks, DefiLlama, SEC filings and NEAR's docs, linked where used, and one off-chain read of a NEAR AI Cloud setting. Raw responses are saved byte for byte; those that list people's accounts are kept private, with their SHA-256.
- AI: the code, scripts and text were written with Claude Code (Anthropic), directed by the author; those commits are marked `Co-Authored-By: Claude`. The video's voice is AI text-to-speech (ElevenLabs), reading a script the author approved; its captions carry the same words.
- Libraries: none beyond the Python standard library. `docs/sign*.html` load NEAR Wallet Selector 10.1.4 from esm.sh.
- This is the author's only submission to NEAR HACKATHON.

License: [MIT](LICENSE).
