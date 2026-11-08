# Pre-registration 3: do the buybacks keep coming in the 30 days from 9 November?

This file does not change after it is anchored on NEAR mainnet. Its SHA-256 is written to SocialDB
(`social.near`) by `samerice7976.near` under the key `samerice7976.near/thesis/prereg/3`, the same way as
`PREREG.md` and `PREREG-2.md`. It is anchored before 2026-11-09 00:00 UTC, when the window opens. Any
correction goes in the README, never here. The results will be published whatever they are, in the README.

## Why these three

The thesis rests on one flow: fees paid on NEAR Intents reach the buybacks wallets, and the wallets keep them.
The rating's Avoid rule fires when that flow stops. Of predictions 1–5, only prediction 2 touches it, and only
from above (inflows below a quarter of new supply over 15 days). None tests whether the flow continues. These
three do, over a full 30-day window, each with a stated probability, so they can fail and are scored.

There is also a reason to measure from this date. NEAR Intents' docs describe FAR as "a permissioned instance of
the NEAR protocol operated by a small validator set with no public networking", and say of a confidential swap:
"The swap settles entirely on FAR via a `token_diff` intent, invisible to public indexers."
([docs](https://docs.near-intents.org/integration/market-makers/confidential-intents.md), read 2026-11-08; the page
says nothing about fees or dates). Confidential Intents have run since February 2026. A public repository
([Tideline](https://github.com/ervhint/tideline), read 2026-11-08) cites an email from NEAR Intents dated
2026-11-06: the private path becomes the main one on 9 November and public intents wind down later, with no date.
It is the only source for that date; we have not seen the email. Whatever happens, predictions 6 and 7 read only
balances on the public chain. Prediction 8 asks whether DefiLlama, the public source of the fee and revenue
figures for NEAR Intents, still has them for every day.

## What was known when this was written (2026-11-08)

- Window 2026-10-02 → 2026-11-01 (final): the buybacks wallets kept **9,569.750 NEAR a day**
  (`n1.buybacks_near_per_day`; 9,569.7498 before rounding), 10.8% of the NEAR issued in the window. The mean
  NEAR price over its 30 days was **$4.879062** (`coins.llama.fi`, the rule below). Kept in USD: **$46,691.40 a day**.
  (`numbers.json` shows $46,692, `iv.buybacks_kept_usd_per_day`, because it multiplies by the price rounded to $4.8791.)
- The same measure by calendar month, in USD a day (`f2.buybacks_kept_usd_per_day`): April $6,270 · May $13,157 ·
  June $15,892 · July $10,286 · August $15,598 · September $44,174 · October $46,857. The largest fall from one
  month to the next was June → July, −35%; none was half or more.
- The latest 30-day window in `data/history.csv` (2026-10-08 → 2026-11-07): 10,151.215 NEAR a day;
  $48,009 a day in `data/rating.csv` (provisional: DefiLlama may still revise those days).
- DefiLlama volume for NEAR Intents, a day: September $160.1M, October $128.6M (−20%).
- No code requires the buybacks. Each of the two wallets moves NEAR with 2 of its 4 signers.

## The predictions

| # | Prediction | Holds if | Probability stated now | Judged at |
|---|---|---|---|---|
| 6 | The buybacks wallets keep at least half of what they kept in the 2 October → 1 November window, in USD | kept ≥ $23,345.70 a day | 0.70 | window end, 2026-12-09 00:00 UTC |
| 7 | They keep at least as much as in the 2 October → 1 November window, in USD | kept ≥ $46,691.40 a day | 0.35 | window end, 2026-12-09 00:00 UTC |
| 8 | DefiLlama has fees and revenue for NEAR Intents for every day of the window | 30 of 30 days counted | 0.65 | fetched at or after 2026-12-11 00:00 UTC |

Numbering continues from `PREREG-2.md` (predictions 4–5). Prediction 7 can hold only if 6 holds.

## Exact rules

- **Window:** 2026-11-09 00:00 UTC → 2026-12-09 00:00 UTC, 30 days. Each boundary is the first block whose
  header timestamp is at or after that time, with the block before it timestamped before it (the rule of
  `scripts/lock_window.py`). It is the row dated 2026-12-09 of `data/history.csv`.
- **The buybacks wallets:** native NEAR of `buybacks.multisignature.near` and of
  `1csfundsadmin.sputnik-dao.near`, plus the wNEAR (`nep141:wrap.near`) that `buybacks.multisignature.near` holds
  inside `intents.near` (`mt_balance_of`), plus any account declared in `scripts/daily.py` `LOCKS`, from its
  declaration on. NEAR and wNEAR only; other tokens do not count. Read with JSON-RPC `view_account` and
  `call_function` at the two boundary blocks, from an archival NEAR mainnet RPC
  (`archival-rpc.mainnet.fastnear.com`). This is `buybacks_per_day` in `scripts/daily.py`.
- **Kept, NEAR a day:** (sum at the end block − sum at the start block − what `treasury.near` sent to these accounts
  inside the window, as native NEAR, wNEAR or wNEAR inside `intents.near`) ÷ 30. A transfer from the protocol
  treasury is not a fee and does not count. Each such transfer, if any, is listed with its transaction hash.
- **Kept, USD a day:** kept NEAR a day × the mean NEAR price over the window: `coingecko:near` from
  `coins.llama.fi`, the price within 3 hours of 12:00 UTC of each of the 30 days (the rule of `scripts/fees.py`),
  averaged over the days that have one. The baseline $46,691.40 is computed the same way. Every response is saved
  byte for byte with its SHA-256.
- **Prediction 8:** DefiLlama `summary/fees/near-intents` (`dataType=dailyFees` and `dataType=dailyRevenue`) and
  `summary/dexs/near-intents`, with the price above, fetched at or after 2026-12-11 00:00 UTC (48 hours after the
  window). Holds if all 30 days are counted by `scripts/fees.py`'s rule (each day has fees, revenue, volume and a
  price; volume above zero; fees at least a fifth of the median over the window's days with fees and volume above zero) and revenue is above zero on
  each day. One fetch is enough: the question is whether the days exist, not their final values.
- **Void:** 6 and 7, only if no archival RPC can answer for both boundary blocks by 2026-12-16 00:00 UTC, or fewer
  than 25 of the 30 days have a price; 8, only if DefiLlama's API does not answer by 2026-12-16 00:00 UTC.
- **Score:** each prediction holds or fails. The Brier score, (probability − outcome)², with outcome 1 if it holds
  and 0 if it fails, is reported for each and as the mean over all predictions judged, 4 to 8.
- **Reported regardless of the predictions:** kept NEAR a day and its share of the NEAR issued in the window, the
  front-end fund (`fefundsadmin.sputnik-dao.near`) measured the same way, and what the three wallets kept as a share
  of DefiLlama's revenue for the window.

## What each result would mean

If 6 fails, the flow the thesis is built on more than halved, and the rating's Avoid test in USD (at or below
April's $6,270 a day) is the next to watch. If 6 holds and 7 fails, the flow continued but fell. If 7 holds, it held
or grew. If 8 fails while 6 holds, the fees still reach the wallets but the public dataset no longer has every day:
balances on the chain are then the only check left.
