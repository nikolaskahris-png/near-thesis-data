# Pre-registration: three predictions, judged on 16 November 2026

This file does not change after it is anchored on NEAR mainnet. Its SHA-256 is written to
SocialDB (`social.near`) by `samerice7976.near` under the key `samerice7976.near/thesis/prereg/1`;
the transaction and a one-call check are in the README. Any correction goes in the README, never here.
The results will be published whatever they are, in the README and as a second SocialDB entry.

## Timing, stated plainly

- Prediction 2's window opened on 2026-11-01 00:00 UTC. This file was anchored after that, on the date
  of the anchoring transaction. At that time the project had read only the window's opening block
  (222,491,356, which is also the closing block of its locked 2026-10-02 to 2026-11-01 window). No balance
  or supply inside the window had been read.
- The three predictions were first written on 2026-10-26, in the project's private notes. On 2026-10-31, before any window opened, prediction 3 was narrowed to the farm alone,
  after measuring three possible definitions at block 222,343,159: 108 accounts in the farm, 142 with the
  farm or an Active Agents lock, 178 with the farm or any lock. On 2026-11-01 prediction 2's balance rule
  was written to match `scripts/daily.py`. These dates come from private notes and cannot be checked:
  the first public record of the predictions is this file.

## The predictions

Baseline: block 222,491,356 (2026-11-01 00:00 UTC), from `data/numbers.json` and `data/stakers/2026-11-01.json`.

| # | Prediction | Holds if | Baseline | Judged at |
|---|---|---|---|---|
| 1 | The largest account keeps at least 70% of the NEAR AI Cloud Credits farm | share ≥ 0.70 | 0.732951 (1,000,000 of 1,364,347.6 NEAR) | first block at or after 2026-11-16T12:00:00Z |
| 2 | Net inflows to the buybacks wallet stay below a quarter of new NEAR supply | ratio < 0.25 | 0.108265 (2026-10-02 to 2026-11-01) | from the first block at or after 2026-11-01T00:00:00Z to the first block at or after 2026-11-16T00:00:00Z |
| 3 | Fewer than 150 accounts have an active position in the NEAR AI Cloud Credits farm | count < 150 | 112 | first block at or after 2026-11-16T12:00:00Z |

"First block at or after T" means the first block whose header timestamp is at or after T (the rule of
`scripts/lock_window.py`), and the block before it has a timestamp before T.

## Exact rules

**Prediction 1.** At the judging block, on `stake.dao`:
`get_farm_position({"account_id": "340ebdb82c9d1fc93625eb4f5565c32aaf6565b07f7ce49976efe2bd69d7321e", "product_id": "prod_33Kp14MGUJa2QA"}).staked_near_amount`
divided by
`get_farm_pool({"price_id": "price_QzmSvxbZqdbV0XbG6VD6KkbB"}).total_farm_shares`.
The account is the largest farm position at the baseline block. At that block the active positions add up
to `total_farm_shares` exactly (difference 0 yoctoNEAR). If the position is closed or missing, its share is 0.

**Prediction 2.** Balance of `buybacks.multisignature.near` at a block = `view_account.amount` plus the
wNEAR it holds inside `intents.near`
(`mt_balance_of({"account_id": "buybacks.multisignature.near", "token_id": "nep141:wrap.near"})`).
Ratio = (balance at the end block − balance at the start block) ÷ (`total_supply` in the end block's header
− `total_supply` in the start block's header). Outflows are already netted in the balance change and are not
subtracted again. This is the buybacks wallet alone, not `1csfundsadmin` or `fefundsadmin`.

**Prediction 3.** Accounts listed from every `stake` receipt ever sent to `stake.dao` (NearBlocks receipts
API, `method=stake`, all pages). Counted: accounts whose
`get_farm_position({"account_id": <account>, "product_id": "prod_33Kp14MGUJa2QA"})` at the judging block has
status `Active` and `staked_near_amount` > 0. Check: the counted positions add up to
`get_farm_pool({"price_id": "price_QzmSvxbZqdbV0XbG6VD6KkbB"}).total_farm_shares`; if they do not, the
prediction is void. NEAR AI Agents locks are not counted.

**Void, for any of the three.** The data cannot be read from a NEAR archival RPC (and, for prediction 3,
NearBlocks) by 2026-11-18 00:00 UTC, or the farm's product or price on `stake.dao` is replaced or archived.
A void prediction is reported as void, never as a pass.

## How demanding they are

- **1** fails if the largest account withdraws about 149,856 NEAR or other accounts add about 64,224 NEAR
  (at the baseline). It has already been below 70% once in the tracked snapshots: 58.9% on 2026-10-15.
- **2** fails only if the buybacks wallet's net inflows more than double against new supply. The highest
  monthly figure we measured, for this wallet together with `1csfundsadmin`, is 15.3% (September 2026).
- **3** needs 38 new active accounts in 15 days to fail. The half-month increases we measured since August
  were 30, 5, 22, 15, 11 and 13.

Predictions 2 and 3 ask for the recent trend to continue; their failing would be strong evidence against
the thesis, their passing weak evidence for it. Prediction 1 is the closest to its threshold.
