# Who Earns What Users Pay on NEAR Intents? A Pre-Registered Decomposition of Swap Costs and NEAR's Revenue Capture

**Project:** Oriova · **Version:** 1.0, 10 November 2026 · **Status:** Part II (value capture) final; Part I (settlement reliability) is scored after its window closes on 14 November 2026 12:00 UTC
**Registration:** [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md), Part II committed 9 Nov 2026 20:30 UTC (commit `51aabb6`) · **Data:** [`data/published/`](data/published) · **Live report and terminal:** https://d2o8uz0046kzfu.cloudfront.net

---

## Abstract

NEAR Intents is the swap layer whose fees fund NEAR's buybacks, yet the public record reports only the total that reaches NEAR. We decompose what users pay into what is declared to distributors, what is declared to NEAR, and what is declared to no one, and we compare NEAR's declared share with the NEAR that actually arrives in its three revenue wallets according to archival chain state. Five claims and their decision thresholds were registered before the history sample was read. The sample covers 52 complete UTC days (one in six from 1 January 2026; 1,041,004 swaps; USD 1.81 billion), of which 42 days after the revenue wallets went live are scored (828,471 swaps; USD 1.47 billion). Users pay 50.0 basis points (bps) of volume. Distributors are declared 33.8 bps, NEAR 3.6 bps, and 12.6 bps is declared to no one; NEAR's wallets receive 8.6 bps. Four claims are supported and one is rejected: 58% of NEAR's revenue is undeclared (95% interval 42% to 69%; the interval crosses the registered edge), NEAR receives 17% of user cost, the largest captive channel charges 5.4 times the largest aggregator, and NEAR's take per dollar rose 4.2-fold; the undeclared revenue does not track the day's unexplained user cost (Spearman 0.14). Exploratory analysis locates a level shift in received-minus-declared revenue between late August and early October 2026 (permutation p < 0.01 under two statistics). Before it, NEAR received close to its declared fee; after it, about 82% of what NEAR receives is undeclared. Every number is recomputable from published files, in the browser or on the command line.

---

## 1. Introduction

### 1.1 Motivation

Since 23 February 2026 NEAR has swept a share of NEAR Intents revenue into three wallets as native NEAR and used it for open-market buybacks. For a NEAR holder, the size and stability of that stream is the most direct link between protocol usage and token value. Public dashboards publish one figure, the NEAR that arrives. The largest public adapter defines revenue as exactly that inflow and states that the split between revenue streams is backend logic that cannot be reproduced from on-chain data.¹ What users pay, who is named to receive it, and whether NEAR's receipts match what NEAR is named to receive, are therefore unmeasured.

### 1.2 Research question

**RQ.** Who earns the money that users pay on NEAR Intents, and how much of it reaches NEAR?

The question is answered through five claims (Section 3.2), each with a numeric measure, a supported edge and a rejected edge registered before the history data was read.

### 1.3 Contributions

1. **A public decomposition** of user cost on NEAR Intents into distributor fees, NEAR fees and an undeclared residual, by day, channel, size band and corridor, from 1,041,004 swaps.
2. **An independent revenue series**: the three revenue wallets' native NEAR balance at the first block of every UTC day from 1 January to 9 November 2026 (313 consecutive days), read from archival state with no API key.
3. **A pre-registered test** of five claims about value capture, with intervals, sensitivity checks and an explicit separation of confirmatory from exploratory results.
4. **Re-runnable evidence**: the same code computes the report, the command-line rebuild and a browser terminal that any reader can run against public endpoints.

---

## 2. Background

### 2.1 How a swap is priced and who is named to be paid

A user requests a quote from the 1Click API, receives a deposit address and a signed quote with a minimum output (`minAmountOut`) and a deadline, and deposits. Solvers fill the swap through `intents.near`. Each swap record carries `amountIn`, `amountOut`, their USD values at quote time (`amountInUsd`, `amountOutUsd`), a `referral` naming the app or integrator that originated it, and `appFees`: a list of recipients with a fee in basis points of the input. We call the referral the **channel**.

### 2.2 How NEAR is paid

NEAR's share arrives as native NEAR transfers from `intents.near` into `buybacks.multisignature.near`, `fefundsadmin.sputnik-dao.near` and `1csfundsadmin.sputnik-dao.near`. The three wallets held nothing on 1, 7 and 13 January 2026; sweeping began on 23 February 2026. Transfers among the three wallets cancel when their balances are summed.

### 2.3 What an observer can see

The Explorer API lists every swap with its fields. Archival RPC returns any account's balance at any past block. Neither shows the internal accounting of `intents.near` that converts fees into the NEAR swept to the wallets. This study works at the boundary of what is public: the swap records on one side, the wallet balances on the other.

---

## 3. Research design

### 3.1 Pre-registration and timeline

All times UTC. Commit hashes refer to the public repository; `git log --follow docs/PREREGISTRATION.md` lists every change.

| Time | Event |
|---|---|
| 9 Nov 15:52 | Part I (settlement reliability, Q1 to Q5) registered before any scored data (`48c6584`) |
| 9 Nov 20:05 | Amendment 1 (census feed for Part I) registered before any verdict was read (`fed03ce`) |
| 9 Nov 20:23 | History sample download started (files written, none read) |
| 9 Nov 20:30 | **Part II (claims C1 to C5) registered** (`51aabb6`). Seen at that point: one 4-hour census take and the wallet balances at its two ends (listed in the registration) |
| 9 Nov 20:38 | Change-log entry: claims scored only on days from 23 Feb, after the January ledger and zero January balances were read |
| 9 Nov 20:45 | First public push of the repository |
| 10 Nov 09:44 | History sample complete (52 days) |
| 10 Nov 10:10 | Wallet series complete (313 days); final rebuild |

Commit times before the first public push (20:45 UTC) are the author's own record; the push is the first external timestamp. History was rewritten once around that push to remove private notes, which changed hashes and kept dates and file contents (change log of the registration).

### 3.2 Claims, measures and decision edges (confirmatory)

| # | Claim | Measure on scored days | Supported | Rejected |
|---|---|---|---|---|
| C1 | Most of NEAR's revenue is undeclared | 1 minus (sum of NEAR-declared fees / sum of swept revenue) | 50% or more | 25% or less |
| C2 | The undeclared part is execution margin | Spearman correlation across days between (swept revenue minus NEAR-declared fees) and the residual, both in dollars | 0.5 or more | 0.2 or less |
| C3 | Distributors capture more than NEAR | Sum of swept revenue / sum of user cost | 25% or less | 50% or more |
| C4 | Price holds only where flow is captive | User cost in bps on the largest captive channel / on the largest aggregator channel (LI.FI, Rango or CoW), swaps of USD 1,000 to 100,000 | 3 or more | 1.5 or less |
| C5 | NEAR's take is rising | Mean swept bps of volume on the last 15 scored days / on the first 15 | 1.25 or more | 0.8 or less |

A reading between its two edges is **open**. Fewer than 20 scored days, or fewer than 200 swaps in either C4 channel, gives **insufficient data**. The verdict reads the point estimate; the interval is reported alongside.

### 3.3 Confirmatory and exploratory results

Section 6 reports only the registered measures. Section 7 reports analyses chosen after the registered readings were computed; each is labelled exploratory, is produced by [`packages/collector/src/robustness.ts`](packages/collector/src/robustness.ts) with fixed seeds, and carries no verdict.

---

## 4. Data

### 4.1 Sources

| Source | Content | Access | Code |
|---|---|---|---|
| NEAR Intents Explorer API | Every swap in a time range with status, amounts, USD values, referral, `appFees`, transaction hashes | Partner token (held privately) | [`census.ts`](packages/collector/src/census.ts) |
| NEAR archival RPC (FastNEAR) | `view_account` of the three wallets at a given block; block headers for the day boundary | Public, no key | [`archive.ts`](packages/core/src/archive.ts) |
| 1Click API | Signed quote and status per swap; token table | Public | [`judge.ts`](packages/core/src/judge.ts) |
| Destination-chain RPCs (two operators per chain) | Delivered amounts for the verifier | Public | [`verify.ts`](packages/core/src/verify.ts) |
| NearBlocks API | Receipts into the three wallets (Sections 7.7 and 7.8) | Public | [`inflows.ts`](packages/collector/src/inflows.ts), cache not stored |

### 4.2 Sampling design

The sampling frame is every UTC day from 1 January to 8 November 2026. We take every sixth day starting on 1 January, which rotates the weekday, and download **every** swap created on each sampled day (a census of the day, sampling only across days). This yields 52 days: 1,056,047 swap records, of which 1,043,864 SUCCESS (USD 1.81 billion), 11,793 REFUNDED (USD 57.6 million), 334 FAILED, 53 PROCESSING and 3 INCOMPLETE_DEPOSIT. The ledger uses SUCCESS swaps with positive USD in and out: 1,041,004 swaps.

**Scored days** are sampled days from 23 February 2026 (wallets live) with at least 1,000 SUCCESS swaps and a non-negative net wallet change. Of 43 such days, one (19 May) is set aside because the wallets paid out 1,978,657 NEAR that day. 42 days are scored: 828,471 swaps, USD 1,472,884,439.

### 4.3 Integrity and disclosure

Each download ("take") is one file whose sha256, time range, take time and status totals are recorded in [`data/census/manifest.jsonl`](data/census/manifest.jsonl). Raw rows are withheld pending confirmation that the partner token's terms allow their publication; every aggregate used here is published. The wallet series contains every day without gaps and can be re-read by anyone.

### 4.4 Known data-quality issues

- **Multi-deposit swaps.** On 20 March a SwapKit swap (deposit `0x809dD550817C368409a531385A376Bc5A190A467`) records USD 0.0083 in and 106,783 USDT out. Its four origin transactions and its signed `minAmountOut` of 102,512 USDT show a swap of about USD 106,000; the API recorded one deposit. The ledger keeps it as registered, which makes that day's residual negative (-30.9 bps). Section 7.6 measures its influence.
- **Small swaps.** Under USD 100 the USD values are noisy enough to make whole channel-band cells negative (Section 7.5). The registered C4 uses USD 1,000 to 100,000.
- **Sweep timing.** Revenue accrues continuously and is swept in batches, so a single day can over- or under-state accrual (Section 8.3).

---

## 5. Measurement and estimation

### 5.1 The fee ledger

For each SUCCESS swap *i* with USD input *x_i* and output *y_i*:

- **User cost** *c_i = x_i − y_i*.
- **NEAR-declared fee** *n_i = x_i · Σ fee_k / 10⁴* over `appFees` entries whose recipient is one of the three revenue wallets.
- **Distributor-declared fee** *d_i = x_i · Σ fee_k / 10⁴* over all other entries.
- **Residual** *e_i = c_i − n_i − d_i*: solver spread, destination network cost and any margin declared nowhere.

Aggregates by day, channel and size band are computed in SQL ([`queries/01_ledger.sql`](queries/01_ledger.sql)). Basis points are always relative to the summed USD input of the same set of swaps.

### 5.2 Swept revenue

For each UTC day *t*, the first block at or after 00:00 UTC is found by interpolation between known block headers, and `view_account` returns each wallet's native balance at that block. With *B(t)* the sum over the three wallets, the NEAR received on day *t* is *s(t) = B(t+1) − B(t)*. Valued at the day's NEAR price *p(t)*, swept revenue is *S(t) = s(t) · p(t)*.

**NEAR price.** *p(t)* is the median of `amountInUsd / amountInFormatted` over SUCCESS swaps that sell wNEAR for more than 1 NEAR on day *t* ([`queries/02_near_price.sql`](queries/02_near_price.sql)), so no outside price feed enters the analysis.

### 5.3 Estimators

With *D* the set of scored days in date order:

- **C1** = 1 − Σ_D n / Σ_D S
- **C2** = Spearman ρ over D of (S − n) and e, in dollars
- **C3** = Σ_D S / Σ_D c
- **C4** = (Σc / Σx) on the captive channel with the most volume ÷ (Σc / Σx) on the aggregator with the most volume, swaps of USD 1,000 to 100,000
- **C5** = mean over the last 15 days of S/x ÷ mean over the first 15 days of S/x

### 5.4 Uncertainty

Intervals are percentile bootstrap intervals over days: 2,000 resamples of the 42 scored days with replacement, each resample re-sorted by date before C5 is computed, quantiles 2.5% and 97.5%. The generator is seeded per claim, so intervals are identical on every run and in the browser. Days are six calendar days apart, which limits serial dependence between consecutive sampled days.

### 5.5 Software

TypeScript on Node 26; Athena SQL for the ledger; the computation of every published number is a pure function in [`packages/core/src/report.ts`](packages/core/src/report.ts), called by `npm run rebuild`, by the report page and by the browser terminal. 23 unit tests cover the readings and the verifier.

---

## 6. Results (confirmatory)

### 6.1 Where the user's cost goes

| Per USD 10,000 swapped, 42 scored days | USD | bps | Share of user cost |
|---|---|---|---|
| Users pay | 50.00 | 50.00 | 100% |
| Declared to distributors | 33.84 | 33.84 | 68% |
| Declared to NEAR | 3.59 | 3.59 | 7% |
| Declared to no one (residual) | 12.56 | 12.56 | 25% |
| **Received by NEAR's wallets** | **8.61** | **8.61** | **17%** |

### 6.2 Readings

| # | Claim | Reading | 95% interval | Verdict |
|---|---|---|---|---|
| C1 | Most of NEAR's revenue is undeclared | 0.583 | 0.417 to 0.686 | supported |
| C2 | The undeclared part is execution margin | 0.144 | −0.189 to 0.467 | rejected |
| C3 | Distributors capture more than NEAR | 0.172 | 0.129 to 0.222 | supported |
| C4 | Price holds only where flow is captive | 5.37 | 4.48 to 6.80 | supported |
| C5 | NEAR's take is rising | 4.19 | 2.33 to 7.03 | supported |

**C1.** NEAR's wallets received USD 8.61 per USD 10,000 against USD 3.59 declared, so 58% of what NEAR receives is named in no fee. The interval's lower end (42%) lies below the supported edge (50%), so C1 is supported by the registered rule with the least margin of the four supported claims.

**C2.** Days with more undeclared revenue are not days with more unexplained user cost (ρ = 0.14, rejected edge 0.20). The undeclared revenue is therefore not accounted for as execution margin taken on the same day's swaps.

**C3.** NEAR receives 17% of what users pay; distributors are declared 68%. The interval lies entirely inside the supported region.

**C4.** On swaps of USD 1,000 to 100,000, SwapKit (the largest captive channel) costs users 93.1 bps; Rango (the largest aggregator channel by volume in this band) costs 17.3 bps; ratio 5.37.

**C5.** Swept bps averaged over the last 15 scored days (11 Aug to 3 Nov) is 4.2 times the average over the first 15 (24 Feb to 25 May).

### 6.3 Channels

| Channel | Share of scored volume | User cost (bps) | Declared to distributors | Declared to NEAR | Residual |
|---|---|---|---|---|---|
| swapkit | 37.1% | 87.0 | 73.4 | 0.0 | 13.7 |
| new.intents-referral.near | 14.1% | 19.0 | 0.1 | 8.7 | 10.2 |
| no referral | 10.7% | 23.3 | 6.3 | 8.4 | 8.6 |
| lifi | 8.4% | 15.4 | 2.6 | 2.7 | 10.1 |
| rango | 7.8% | 19.5 | 10.8 | 1.3 | 7.4 |
| zodl | 4.7% | 97.8 | 65.7 | 1.4 | 30.7 |
| near-intents.intents-referral.near | 3.8% | 21.2 | 0.0 | 9.4 | 11.9 |

The largest channel declares nothing to NEAR. NEAR's declared fee comes mostly from the two channels named `intents-referral` and from swaps with no referral.

---

## 7. Exploratory analyses

*Everything in this section was chosen after Section 6 was computed. Source: [`data/published/robustness.json`](data/published/robustness.json), `npm run robustness`.*

### 7.1 A level shift in received-minus-declared revenue

The daily series (Appendix B) shows received revenue close to declared revenue until late August and well above it afterwards. We first split at 29 August, the first elevated scored day, **chosen by inspecting the series**:

| Scored days | Days | Volume (USD) | User cost | NEAR declared | Received | Undeclared share | NEAR received per USD 1M | Mean NEAR price |
|---|---|---|---|---|---|---|---|---|
| 24 Feb to 23 Aug | 30 | 1.00 B | 46.9 bps | 3.79 bps | 4.49 bps | 16% | 265 | 1.65 |
| 29 Aug to 3 Nov | 12 | 0.47 B | 56.6 bps | 3.16 bps | 17.33 bps | 82% | 473 | 3.93 |

Because the split date was chosen by eye, we test for a shift with a procedure that includes the search. For every split leaving at least 5 days on each side we compute the difference in the centre of the daily (received − declared) bps after versus before, take the largest, and compare it with the largest difference found in 10,000 random orderings of the same 42 days:

| Centre | Split found (first day after) | Difference | Permutation p |
|---|---|---|---|
| Mean | 4 Oct | 19.9 bps | 0.0011 |
| Median | 22 Sep | 13.9 bps | 0.0076 |

The shift is unlikely to be an artefact of searching (p < 0.01 under both statistics). Its location is not pinned to one day: the mean is pulled by 4 October (73.7 bps on a USD 19 million day) and the median places it at 22 September; the first elevated days are 29 August and 4 September. We describe it as a shift between late August and early October.

### 7.2 Units: dollars, NEAR and price

NEAR's price rose from a mean of USD 1.65 on the earlier scored days to 3.93 on the later ones, so the same NEAR is worth more dollars later. Three views separate price from quantity:

- **NEAR per dollar of volume** (price-free): 265 to 473 NEAR per USD 1 million, up 78% on scored days.
- **C5 in NEAR per dollar**: 1.68 (registered C5 in dollars: 4.19). Both exceed the supported edge of 1.25.
- **Every calendar day** (the full 313-day wallet series, independent of the sample):

| Month (2026) | Days | NEAR received | Per day |
|---|---|---|---|
| Feb (from 23rd) | 6 | 176,644 | 29,441 |
| Mar | 31 | 450,898 | 14,545 |
| Apr | 30 | 148,357 | 4,945 |
| May | 31 | 323,837 | 10,446 |
| Jun | 30 | 292,679 | 9,756 |
| Jul | 31 | 248,316 | 8,010 |
| Aug | 31 | 405,387 | 13,077 |
| Sep | 30 | 564,181 | 18,806 |
| Oct | 31 | 451,484 | 14,564 |
| Nov (to 8th) | 8 | 99,288 | 12,411 |

Per calendar day the wallets received 10,720 NEAR before 29 August and 16,063 after (+50%). In NEAR per day, September is the highest month and October equals March; most of the rise in dollar terms comes from the combination of more NEAR per dollar of volume and a higher NEAR price. February's first week includes the initial sweep after launch.

### 7.3 C2 without the volume factor

The registered C2 correlates dollar amounts, which both scale with daily volume (ρ of volume with the residual 0.81, with undeclared revenue 0.35). That shared factor biases ρ upward, toward support. Removing it by correlating bps of volume gives ρ = −0.19. The rejection is therefore robust to the measure's main bias.

### 7.4 Influence of single days

Recomputing each claim with one scored day removed:

| Claim | Range over 42 omissions | Most influential day | Verdict changes |
|---|---|---|---|
| C1 | 0.542 to 0.600 | 4 Oct | none (stays ≥ 0.50) |
| C3 | 0.155 to 0.177 | 4 Oct | none |
| C5 | 3.09 to 4.52 | 4 Oct | none |

### 7.5 C4 across size bands

| Band | Captive (bps) | Aggregator (bps) | Ratio | Note |
|---|---|---|---|---|
| Under USD 100 | SwapKit −80.2 | Rango 73.7 | −1.09 | Dominated by the multi-deposit record (Section 4.4); uninterpretable |
| USD 100 to 1,000 | SwapKit 92.5 | Rango 22.3 | 4.16 | |
| USD 1,000 to 100,000 (registered) | SwapKit 93.1 | Rango 17.3 | 5.37 | |
| Over USD 100,000 | SwapKit 80.2 | LI.FI 11.9 | 6.75 | Below the 200-swap gate (175 aggregator swaps) |

The ratio is above 4 in every interpretable band.

### 7.6 Sensitivity to named records and periods

| Variant | Days | C1 | C2 | C3 | C5 |
|---|---|---|---|---|---|
| Registered | 42 | 0.583 | 0.144 | 0.172 | 4.19 |
| Without the 20 Mar SwapKit under-USD-100 cell | 42 | 0.583 | 0.126 | 0.170 | 4.19 |
| Without 4 Oct | 41 | 0.542 | | 0.155 | 3.09 |
| Days before 29 Aug only | 30 | 0.155 | | 0.096 | 1.14 |

The last row matters for interpretation: on the earlier period alone C1 would be rejected and C5 open. The supported C1 and C5 are driven by the later period.

### 7.7 Source of the received NEAR

The latest 50 receipts into each wallet (4 to 10 November) were read from NearBlocks. All receipts into `fefundsadmin.sputnik-dao.near` (23,217 NEAR) and `buybacks.multisignature.near` (23,641 NEAR) are transfers from `intents.near`. Receipts into `1csfundsadmin.sputnik-dao.near` include 18,358 NEAR from `intents.near`, dust from other accounts, and outgoing transfers of 510,068 NEAR to `buybacks.multisignature.near`, which cancel in the summed balance. This check covers recent days only; it supports reading the received NEAR as Intents revenue and leaves the routing rule inside `intents.near` unattributed.

### 7.8 Who inside `intents.near` pays the received NEAR

*Days chosen after the shift was seen: three before it (11, 17, 23 August) and five after (29 August, 4 and 22 September, 4 October, 3 November). Source: [`data/published/inflows.json`](data/published/inflows.json), `npm run inflows -- <days>`.*

Every inbound transfer from `intents.near` to the wallets is a signed `native_withdraw` intent, and its signer is the account inside `intents.near` that paid. We read every such transfer on the eight days (282 transfers, NearBlocks receipt lists plus each transaction's signed intents from archival RPC) and split the NEAR by signer: the 1Click fee account (`5880ad2b…47dd`, the account swap records name in `appFees`) and all other accounts. On every day the two parts sum exactly to the change in the wallets' balance series, and no NEAR arrived from sources outside `intents.near`.

| Day | Transfers | Declared to NEAR (bps) | From the 1Click fee account (bps) | From other accounts (bps) | Other accounts |
|---|---|---|---|---|---|
| 11 Aug | 15 | 3.83 | 2.34 | 2.80 | 5 |
| 17 Aug | 21 | 3.76 | 2.47 | 4.33 | 10 |
| 23 Aug | 23 | 4.00 | 2.29 | 4.02 | 11 |
| 29 Aug | 21 | 1.00 | 0.98 | 10.58 | 19 |
| 4 Sep | 60 | 1.42 | 2.20 | 22.06 | 52 |
| 22 Sep | 81 | 2.18 | 2.14 | 16.20 | 68 |
| 4 Oct | 27 | 7.48 | 7.03 | 66.63 | 21 |
| 3 Nov | 33 | 2.90 | 2.19 | 8.32 | 27 |

Three readings follow.

1. **The declared part has a payer.** After the shift, the NEAR paid by the 1Click fee account is within 0.8 bps of the fee declared to NEAR on every day (0.98 against 1.00 on 29 August, 7.03 against 7.48 on 4 October). Before it, the account paid about 1.5 bps less than declared.
2. **The rise sits entirely in other accounts.** Their share went from 2.8 to 4.3 bps before the shift to 8.3 to 66.6 bps after it, and their number from 5 to 11 a day to 19 to 68.
3. **The other accounts are single-use and funded by the omnibus account.** Across the eight days 203 distinct other accounts paid; 2 appear on more than one day. For the three largest other accounts of each day we scanned the 40 blocks before the withdrawal for the transfer that funded them. After the shift, 13 of the 15 traced accounts were funded by `51e8f94d…7cbe`, the omnibus account through which every 1Click swap passes; the other two are the recurring account `143f2bb4…cfb31`, funded from other accounts. Before the shift, 2 of 9 traced accounts were funded by the omnibus account; the largest payers then were the two recurring accounts, funded from three other accounts or from none found within 40 blocks.

The received NEAR therefore has two paths: the account named in `appFees`, which tracks the declared fee, and a stream of fresh accounts filled by the 1Click omnibus account shortly before each withdrawal, which carries the undeclared part and all of its growth. Why the omnibus account funds them, and from which swaps, is outside the signed intents. Limits: eight days chosen by eye, funding traced for three accounts a day within 40 blocks, and the 1Click fee account identified by the `appFees` field (the Explorer API labels it a buyback wallet).

---

## 8. Threats to validity

### 8.1 Construct validity

- **Received NEAR as revenue.** The measure counts any net native-NEAR inflow to the three wallets. Inflows from sources other than `intents.near` would inflate it; the receipt checks (7.7, 7.8) found none of material size, and payout days are set aside by rule.
- **Declared fees.** `appFees` is what the swap record names. Fees charged by mechanisms outside `appFees` are by construction "undeclared" here; the study measures disclosure, and the word "undeclared" means "named in no `appFees` entry".
- **USD values** are the API's quote-time values; Section 4.4 documents one known failure.

### 8.2 Internal validity

- **Timing.** Sweeps lag accrual. C1 and C3 use totals over 42 days; single-day readings are reported as noisy. A change in sweep cadence would appear as alternating spikes and quiet days in the 313-day series; September and October show a sustained higher level.
- **Price.** Dollar measures move with NEAR's price; Section 7.2 reports NEAR-unit equivalents.
- **Launch effect.** The first scored days follow the launch of sweeping; C5's first window includes it.

### 8.3 Statistical conclusion validity

- 42 days give wide intervals for ratio measures (C5: 2.3 to 7.0). C1's interval crosses its edge.
- The bootstrap treats days as independent; days six apart reduce, and do not remove, dependence. A level shift (7.1) violates the stationarity a simple bootstrap assumes, which widens the true uncertainty of C1 and C5.
- Exploratory p-values (7.1) are computed once on one statistic family; no other break tests were run.

### 8.4 External validity

The sample ends on 3 November. The later period rests on 12 scored days. Results describe NEAR Intents in 2026 under its fee arrangements at the time, which can change without notice.

---

## 9. Discussion

**Who earns.** Distribution captures most of what users pay: two thirds of user cost is declared to distributors, led by SwapKit at 87 bps on 37% of volume, which declares nothing to NEAR. Price is set by where users arrive: captive channels charge four to seven times what aggregators charge for the same service.

**How much reaches NEAR.** NEAR receives 17% of user cost, about 2.4 times its declared fee. Until late August the two were close (received 4.5 bps, declared 3.8 bps). From late August to early October received revenue moved to a higher level (17.3 bps on the later scored days) while the declared fee stayed near 3 bps.

**What the undeclared revenue is.** The data rule out one simple account: it is not the same day's unexplained user cost (C2 rejected, more strongly once volume is removed). The receipts show it leaves `intents.near`, and Section 7.8 shows by whom: the declared part is paid by the account named in `appFees`, and the undeclared part by single-use accounts that the 1Click omnibus account funds shortly before each withdrawal. What produces it (a protocol fee outside `appFees`, a margin on conversion, solver payments, or treasury routing) is outside the signed intents.

**Implications.**
- For **holders**: NEAR's Intents revenue is larger than declared fees imply and grew sharply in autumn 2026. The growth sits in the part that is written down nowhere, so it can change without notice and without a change in any visible fee.
- For **analysts and dashboards**: revenue inferred from `appFees` understates what NEAR received by about 2.4 times over the scored days and by about 5.5 times after the shift.
- For **disclosure**: one public statement of the rule that routes revenue to the three wallets would turn C1 from a finding into an accounting identity.

---

## 10. Limitations and future work

1. **Attribution.** Section 7.8 traces the payers on eight days to the 1Click omnibus account. Linking each funding transfer to the swaps that produced it, on every day, needs a full index of `intents.near` beyond this study.
2. **Coverage.** One day in six; a full daily ledger would remove sampling error from C1, C3 and C5 and sharpen the shift's date.
3. **Horizon.** Twelve scored days after the shift. Re-running `npm run rebuild` with later days answers whether the level persists.
4. **Part I.** Settlement reliability (registered Q1 to Q5) is scored after 14 November 12:00 UTC and reported as its own section.
5. **Custody.** The account inside `intents.near` that accrues fees has one registered key; custody behind it is outside chain state.

---

## 11. Conclusion

Users of NEAR Intents pay about 50 bps per swap. Two thirds of it is declared to distributors, led by a captive channel that charges five times what aggregators charge. NEAR receives 17%, about 2.4 times what its declared fee names, and the difference comes from a stream no swap record describes. That stream was small until late August 2026 and has since become most of NEAR's Intents revenue. NEAR's revenue is therefore larger and faster-growing than disclosed fees suggest, and the part that grew is the part nobody has written down.

---

## Notes

¹ DefiLlama dimension adapters, `fees/near-intents/index.ts`, accessed 9 November 2026.

## Appendix A. Deviations from the registration

Listed in full in [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md), Amendment 2. In short: (1) "swept revenue on a day" is implemented as first block of day *t* to first block of day *t+1*; (2) days with a net payout are set aside, where the registration said outflows are "shown separately"; (3) C4's channels are chosen within the registered size band; (4) no threshold, measure or conclusion rule changed.

## Appendix B. Every sampled day

Basis points of the day's volume. "Reached wallets" is shown for days after the wallets went live.

| Day | Status | Swaps | Volume (USD M) | User cost | Distributors | NEAR declared | No declared fee | NEAR received (NEAR) | NEAR price | Reached wallets |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01-01 | before wallets | 18,165 | 11.9 | 62.83 | 47.40 | 1.90 | 13.53 | 0 | 1.542 |  |
| 2026-01-07 | before wallets | 21,647 | 40.9 | 59.27 | 32.52 | 6.86 | 19.88 | 0 | 1.758 |  |
| 2026-01-13 | before wallets | 21,869 | 41.4 | 75.66 | 39.67 | 5.85 | 30.14 | 0 | 1.774 |  |
| 2026-01-19 | before wallets | 25,723 | 36.2 | 79.97 | 40.87 | 7.11 | 31.98 | 0 | 1.570 |  |
| 2026-01-25 | before wallets | 15,573 | 32.2 | 75.56 | 59.62 | 2.99 | 12.94 | 0 | 1.474 |  |
| 2026-01-31 | before wallets | 21,218 | 34.0 | 74.27 | 57.27 | 3.35 | 13.65 | 2,836 | 1.215 |  |
| 2026-02-06 | before wallets | 31,293 | 56.1 | 62.66 | 40.39 | 4.86 | 17.41 | 71,100 | 1.004 |  |
| 2026-02-12 | before wallets | 20,408 | 30.9 | 65.13 | 35.90 | 6.24 | 22.99 | 11,758 | 0.961 |  |
| 2026-02-18 | before wallets | 15,457 | 27.6 | 52.05 | 39.78 | 1.75 | 10.52 | 1,947 | 1.043 |  |
| 2026-02-24 | scored | 16,469 | 31.3 | 78.74 | 56.96 | 4.38 | 17.40 | 8,326 | 0.974 | 2.59 |
| 2026-03-02 | scored | 20,287 | 30.2 | 67.77 | 43.48 | 8.66 | 15.63 | 15,186 | 1.285 | 6.47 |
| 2026-03-08 | scored | 14,187 | 14.0 | 51.15 | 36.90 | 5.00 | 9.25 | 3,477 | 1.222 | 3.03 |
| 2026-03-14 | scored | 12,494 | 14.2 | 62.53 | 41.84 | 4.30 | 16.39 | 4,978 | 1.311 | 4.61 |
| 2026-03-20 | scored | 17,110 | 25.1 | 4.38 | 31.21 | 4.11 | -30.93 | 5,935 | 1.334 | 3.15 |
| 2026-03-26 | scored | 21,268 | 26.6 | 53.20 | 37.61 | 3.10 | 12.49 | 5,506 | 1.230 | 2.54 |
| 2026-04-01 | scored | 21,843 | 47.8 | 54.31 | 39.11 | 1.97 | 13.23 | 8,638 | 1.204 | 2.17 |
| 2026-04-07 | scored | 19,956 | 36.1 | 58.33 | 37.95 | 3.03 | 17.35 | 8,204 | 1.250 | 2.84 |
| 2026-04-13 | scored | 22,062 | 32.6 | 51.92 | 32.52 | 5.00 | 14.40 | 11,721 | 1.390 | 5.00 |
| 2026-04-19 | scored | 20,957 | 23.3 | 62.24 | 34.83 | 6.82 | 20.58 | 8,446 | 1.347 | 4.88 |
| 2026-04-25 | scored | 12,590 | 11.1 | 58.86 | 32.52 | 2.90 | 23.45 | 3,196 | 1.410 | 4.07 |
| 2026-05-01 | scored | 19,132 | 22.9 | 60.32 | 42.52 | 4.72 | 13.08 | 10,286 | 1.300 | 5.84 |
| 2026-05-07 | scored | 19,282 | 28.3 | 51.07 | 33.95 | 3.62 | 13.50 | 8,198 | 1.487 | 4.30 |
| 2026-05-13 | scored | 17,384 | 24.6 | 51.48 | 36.76 | 2.37 | 12.35 | 4,248 | 1.606 | 2.77 |
| 2026-05-19 | payout, set aside | 21,180 | 29.8 | 42.10 | 25.80 | 3.75 | 12.55 | -1,978,657 | 1.630 | -1081.56 |
| 2026-05-25 | scored | 20,804 | 46.9 | 52.54 | 20.40 | 8.10 | 24.04 | 15,088 | 2.637 | 8.48 |
| 2026-05-31 | scored | 15,813 | 88.1 | 20.40 | 5.87 | 3.33 | 11.20 | 14,698 | 2.283 | 3.81 |
| 2026-06-06 | scored | 17,220 | 27.8 | 51.18 | 31.12 | 3.64 | 16.42 | 8,516 | 1.883 | 5.77 |
| 2026-06-12 | scored | 19,442 | 40.7 | 43.64 | 28.13 | 2.24 | 13.27 | 8,827 | 2.071 | 4.49 |
| 2026-06-18 | scored | 20,509 | 30.4 | 49.05 | 33.05 | 3.48 | 12.52 | 5,187 | 2.203 | 3.76 |
| 2026-06-24 | scored | 21,828 | 40.1 | 51.62 | 37.91 | 2.46 | 11.25 | 7,987 | 1.933 | 3.85 |
| 2026-06-30 | scored | 19,787 | 43.3 | 44.14 | 33.13 | 1.95 | 9.06 | 5,735 | 1.829 | 2.42 |
| 2026-07-06 | scored | 20,078 | 46.9 | 47.28 | 33.74 | 3.21 | 10.33 | 9,102 | 2.018 | 3.91 |
| 2026-07-12 | scored | 15,074 | 20.8 | 43.48 | 25.66 | 3.37 | 14.45 | 5,600 | 1.891 | 5.08 |
| 2026-07-18 | scored | 15,797 | 27.2 | 34.39 | 17.82 | 3.76 | 12.82 | 9,522 | 1.920 | 6.72 |
| 2026-07-24 | scored | 20,469 | 28.2 | 37.23 | 24.20 | 2.66 | 10.37 | 5,374 | 1.866 | 3.55 |
| 2026-07-30 | scored | 23,503 | 37.1 | 41.85 | 26.26 | 3.33 | 12.26 | 10,427 | 1.631 | 4.59 |
| 2026-08-05 | scored | 22,783 | 31.2 | 40.56 | 25.75 | 3.12 | 11.69 | 9,388 | 1.690 | 5.09 |
| 2026-08-11 | scored | 24,682 | 35.1 | 39.70 | 23.84 | 3.83 | 12.03 | 11,354 | 1.590 | 5.14 |
| 2026-08-17 | scored | 25,607 | 38.1 | 40.43 | 22.30 | 3.76 | 14.38 | 15,820 | 1.639 | 6.80 |
| 2026-08-23 | scored | 29,626 | 50.1 | 57.41 | 39.31 | 4.00 | 14.10 | 16,248 | 1.945 | 6.30 |
| 2026-08-29 | scored | 22,464 | 22.3 | 62.44 | 45.32 | 1.00 | 16.12 | 14,122 | 1.821 | 11.55 |
| 2026-09-04 | scored | 33,687 | 42.5 | 57.34 | 38.53 | 1.42 | 17.38 | 50,271 | 2.049 | 24.26 |
| 2026-09-10 | scored | 19,724 | 56.0 | 50.56 | 34.98 | 1.24 | 14.34 | 14,395 | 2.470 | 6.35 |
| 2026-09-16 | scored | 16,224 | 47.2 | 66.94 | 45.54 | 2.95 | 18.46 | 15,577 | 2.464 | 8.14 |
| 2026-09-22 | scored | 23,616 | 62.7 | 63.50 | 49.87 | 2.18 | 11.44 | 26,251 | 4.385 | 18.35 |
| 2026-09-28 | scored | 28,765 | 57.4 | 54.56 | 42.82 | 3.06 | 8.68 | 13,646 | 5.053 | 12.02 |
| 2026-10-04 | scored | 13,476 | 19.8 | 70.67 | 53.28 | 7.48 | 9.91 | 29,746 | 4.908 | 73.67 |
| 2026-10-10 | scored | 16,022 | 39.8 | 60.62 | 40.18 | 5.80 | 14.65 | 14,837 | 5.292 | 19.74 |
| 2026-10-16 | scored | 14,504 | 21.2 | 57.09 | 44.99 | 4.05 | 8.06 | 9,131 | 5.210 | 22.39 |
| 2026-10-22 | scored | 16,071 | 30.2 | 50.07 | 37.09 | 4.40 | 8.58 | 12,057 | 4.980 | 19.90 |
| 2026-10-28 | scored | 15,507 | 32.6 | 48.18 | 31.17 | 5.34 | 11.67 | 12,127 | 4.691 | 17.44 |
| 2026-11-03 | scored | 20,368 | 40.8 | 41.48 | 31.69 | 2.90 | 6.89 | 11,213 | 3.824 | 10.50 |

## Appendix C. Reproduction

```bash
git clone https://github.com/youvandra/Oriova && cd Oriova && npm install
npm run rebuild        # Section 6, prints every reading; writes data/published/readings.json
npm run robustness     # Section 7; writes data/published/robustness.json
npm run sensitivity -- 2026-03-20/swapkit/under_100
npm run sweeps -- 2026-11-01 2026-11-03   # re-reads wallet balances from a public archival node
```

Or in a browser: https://d2o8uz0046kzfu.cloudfront.net/terminal?run=rebuild

| File | sha256 (first 16) |
|---|---|
| `data/published/ledger.csv` | `8a76c2f76af71b5b` |
| `data/published/near_price.csv` | `6d566b352b0996c0` |
| `data/published/sweeps.jsonl` | `559ac93f4231c3b8` |
| `data/published/readings.json` | `32217aec79121b36` |
| `data/published/robustness.json` | `77d34f6001862584` |
| `data/published/corridors.csv` | `2739f172a66f8660` |

## Appendix D. Glossary

- **bps**: basis points, hundredths of a percent of the USD input.
- **Channel**: the swap's `referral`, or "no referral".
- **Captive channel**: a channel that is not an aggregator (LI.FI, Rango, CoW).
- **Declared fee**: an `appFees` entry on the swap record.
- **Residual**: user cost minus all declared fees.
- **Swept revenue / received**: net native NEAR gained by the three revenue wallets over a UTC day, in USD at the day's price.
- **Scored day**: sampled day from 23 Feb with at least 1,000 SUCCESS swaps and no net payout.
