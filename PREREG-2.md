# Pre-registration 2: when HSP-027's protocol version takes effect

This file does not change after it is anchored on NEAR mainnet. Its SHA-256 is written to SocialDB
(`social.near`) by `samerice7976.near` under the key `samerice7976.near/thesis/prereg/2`, the same way as
`PREREG.md` (key `.../prereg/1`). Any correction goes in the README, never here. The results will be
published whatever they are, in the README, before the hackathon's deadline (2026-11-14 23:59 UTC).

## Why these two

The thesis says a passed vote is not yet a rule: a House of Stake proposal changes nothing on chain by itself,
and takes effect only when validators holding 4/5 of stake run a nearcore release that contains it.
HSP-027 (remove the developer gas rebate, `vote.dao` proposal 27) passed on 2026-07-03. It is protocol
version 87 in nearcore 2.14.0 (`ProtocolFeature::RemoveGasRewards => 87`). These two predictions test whether
that last step happens on the release's own schedule.

## What was known when this was written (2026-11-03, before 2026-11-04 00:00 UTC)

- nearcore 2.14.0 was released on GitHub on 2026-10-26, marked `CODE_YELLOW_MAINNET`, `PROTOCOL_UPGRADE: TRUE`.
- Its mainnet voting schedule (`core/primitives/src/version.rs`, `get_protocol_upgrade_schedule`): version 87
  from `2026-11-04 00:00:00`, version 88 from `2026-11-06 00:00:00`. The same file says the upgrade happens
  1–2 epochs after the set date.
- The last record of `data/upgrade_watch.csv` (2026-11-03 06:50 UTC, block 222,834,559): protocol version in
  effect 86; in 300 sampled blocks, producers holding 93.4% of block producers' stake were seen and none signalled
  version 87, because voting had not opened.
- Which release each validator runs is not visible on chain before voting opens.

## The predictions

| # | Prediction | Holds if | Probability stated now | Judged at |
|---|---|---|---|---|
| 4 | Protocol version 87 (HSP-027) is in effect on NEAR mainnet | `protocol_version` ≥ 87 | 0.85 | first block at or after 2026-11-06T00:00:00Z |
| 5 | Protocol version 88 is in effect on NEAR mainnet | `protocol_version` ≥ 88 | 0.75 | first block at or after 2026-11-08T00:00:00Z |

Numbering continues from `PREREG.md` (predictions 1–3).

## Exact rules

- **Judging block:** the first block whose header timestamp is at or after the time given, with the block
  before it timestamped before that time (the rule of `scripts/lock_window.py`).
- **Protocol version in effect:** the field `protocol_version` of JSON-RPC `EXPERIMENTAL_protocol_config`
  with `block_id` set to the judging block's height, from an archival NEAR mainnet RPC
  (`archival-rpc.mainnet.fastnear.com`). The response is saved byte for byte with its SHA-256.
- **Void:** only if no archival RPC can answer for the judging block by 2026-11-13 00:00 UTC.
- **Score:** each prediction holds or fails. The Brier score, (probability − outcome)², with outcome 1 if it
  holds and 0 if it fails, is reported for each and as their mean.
- **Reported regardless of the predictions:** the first block with `protocol_version` ≥ 87, its time, and the
  days from 2026-07-03 (HSP-027 passed) to that block.
