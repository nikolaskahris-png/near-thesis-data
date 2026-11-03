# Details

Companion to the [README](../README.md). Every marked figure here is checked against `data/numbers.json` in the same
way: `python scripts/build_numbers.py --check docs/DETAILS.md`.

## The three numbers

- **1.** Balance change of `buybacks.multisignature.near` + `1csfundsadmin.sputnik-dao.near` (the 1Click fund that
  collected fees until April 2026 and later moved its NEAR to the buybacks wallet; summing the two cancels that
  internal move) ÷ change of `total_supply` in the two block headers. wNEAR that the buybacks wallet and the
  front-end fund hold inside `intents.near` counts as held. The front-end fund is `fefundsadmin.sputnik-dao.near`
  (<!--n:n1.front_end_near_per_day-->4,985<!--/n--> NEAR a day): near-intents.org's fees, collected by the front
  end's operator. Balances are net: anything paid out is already subtracted.
- **2.** Mean over counted days of (fees of the day ÷ NEAR price at 12:00 UTC; mean price
  <!--n:n2.mean_price_usd-->$4.88<!--/n-->) ÷ new NEAR per day. Equilibrium
  price = fees per day ÷ new NEAR per day. At HSP-029's target rate (issuance × 16/25, the end of its ramp), the ceiling would be
  <!--n:n2.hsp029_max_coverage-->74.8%<!--/n--> and the equilibrium price <!--n:n2.hsp029_equilibrium_price_usd-->$3.64<!--/n-->.
- **3.** Every account that ever called `stake` on `stake.dao` is read with `get_farm_position` at the block:
  <!--n:n3.stakers_ever-->188<!--/n--> have entered the farm, <!--n:n3.stakers_left-->76<!--/n--> of them
  (<!--n:n3.left_share_of_ever-->40.4%<!--/n-->) have left. The active positions add up exactly to the farm's
  `total_farm_shares` (<!--n:n3.farm_total_near-->1,364,348<!--/n--> NEAR); the run fails otherwise.
  *Why the farm only:* NEAR AI Agents subscriptions are locks on the same contract, but their status does not
  follow their term: of <!--n:f7.locks_active-->43<!--/n--> locks marked Active, <!--n:f7.locks_active_within_term-->11<!--/n-->
  are within their term, and <!--n:f7.locks_past_end-->75<!--/n--> of all <!--n:f7.locks-->86<!--/n--> are past their
  `end_ns`. Counting the farm or an Active lock gives <!--n:n3.farm_or_active_lock_accounts-->145<!--/n--> accounts; the
  farm or any lock, <!--n:n3.farm_or_any_lock_accounts-->181<!--/n-->. The farm is the definition that adds up exactly;
  the rule was fixed in `PREREG.md` after measuring all three on 31 October.

## Investment view: HSP-029 and the staking yield

The staking yield is new NEAR per year not kept by `treasury.near`, divided by the validators' stake; validator
commissions and downtime lower it.

**At HSP-029's target rate** (1.6% a year instead of 2.5%: issuance ×16/25), what the wallets keep must grow
<!--n:iv.hsp029_wallets_multiple_with_front_end-->×3.9<!--/n--> (front-end fund included), or, with every fee kept,
fees <!--n:iv.hsp029_fees_multiple-->×1.3<!--/n-->. The proposal reaches that rate at the end of a 24-month linear
ramp that starts one quarter after ratification, and only once validators adopt it, so the target lies beyond this
view's 12-month horizon (proposal text on `vote.dao`, `get_proposal` 29).

## Contract-level admin scope

**Contract-level admin scope.** These do not set value; they say what the same signers can do to the contracts.

| Link | Who can change it | Signatures | Used |
|---|---|---|---|
| `intents.near` code | `ctl-intents.near` holds the Upgrader role on `intents.near`. On that controller the intents DAO adds a release, the <!--n:c.intents_code_updater_accounts-->1<!--/n--> account with the Updater role installs it, and <!--n:c.intents_code_downgrader_accounts-->2<!--/n--> accounts can roll back | <!--n:c.intents_code_add_release-->3 of 5<!--/n-->, then 1 account | <!--n:c.intents_code_changes-->20<!--/n--> code changes (<!--n:h.intents_code_downgrades-->1<!--/n--> downgrade), last <!--n:c.intents_code_last_change_utc-->2026-10-07<!--/n--> (v<!--n:c.intents_code_version-->0.4.5<!--/n-->) |
| User funds on `intents.near` | intents DAO proposals (`ft_force_withdraw`, `mt_force_transfer`, force lock/unlock) | DAO | <!--n:h.user_funds.approved_actions-->12<!--/n--> actions: force-withdraw <!--n:h.ft_force_withdraw-->9<!--/n-->, force-transfer <!--n:h.mt_force_transfer-->1<!--/n-->, the rest force lock or unlock (<!--n:h.user_funds.first-->2025-01-14<!--/n--> → <!--n:h.user_funds.last-->2026-06-10<!--/n-->) |
| Pause of `intents.near` features | intents DAO | DAO | <!--n:h.pause.approved_actions-->7<!--/n--> actions (<!--n:h.pause.first-->2026-01-15<!--/n--> → <!--n:h.pause.last-->2026-10-07<!--/n-->) |
| Roles on the map's contracts | the DAOs above | DAO | <!--n:h.roles.approved_actions-->58<!--/n--> actions, <!--n:h.intents_acl_grant_role-->12<!--/n--> role grants on `intents.near` |
| Farm contract (`stake.dao`) | either of its <!--n:c.farm_contract_full_access_keys-->2<!--/n--> full-access keys (upgrade, owner methods); <!--n:c.farm_contract_guardians-->5<!--/n--> guardians can pause | 1 key | keys unchanged since <!--n:h.keys.stake_dao.last_change-->2026-07-29<!--/n--> |

The history counts approved proposals by kind (<!--n:h.proposals_total-->390<!--/n--> proposals read in all); dates
are submission dates, because Sputnik DAO stores no approval time. For user funds the history records only the
mechanism and how often it was used: each proposal states its own reason, which this repository does not
characterize.

## Peers

**The same map for three peers.** *From their docs and press, not verified on their chains.*

| | NEAR | Hyperliquid (HYPE) | Aave (AAVE) | Jupiter (JUP) |
|---|---|---|---|---|
| Who buys the token | multisig <!--n:c.buybacks_confirmations-->2 of 4<!--/n--> | the L1 itself, from a system address with no private key | a finance committee multisig, 3 of 4 | the team |
| Rule or choice | choice ("No specific mechanism is guaranteed or committed to", [NEAR, Feb 2026](https://near.org/blog/evolving-near-tokenomics)) | protocol rule, 97–99% of fees | governance programme, $50M a year | 50% of revenue, team commitment |
| Where bought tokens go | held in the wallet, can be moved | locked; treated as burned after a validator vote (Dec 2025) | Ecosystem Reserve, not burned | locked 3 years; burns by DAO vote |
| How a rule changes | no buyback rule to change: the wallet's signers decide (issuance: nearcore release + <!--n:c.issuance_upgrade_stake_threshold-->4/5<!--/n--> of stake) | validators by stake | on-chain vote with a 3- or 10-day timelock | JUP DAO |

This compares mechanisms, not quality: Hyperliquid is an L1 with a built-in exchange, a different model.
Sources: [The Block](https://www.theblock.co/post/383091), [Aave docs](https://aave.com/docs/ecosystem/aave),
DefiLlama token rights pages for Aave and Jupiter.

## More figures behind the findings

- **Finding 3, all of 2026** (1 January to 1 November): the NEAR AI pool owner's NEAR went from
  <!--n:f4.y2026.owner_near_start-->1,795,378<!--/n--> to <!--n:f4.y2026.owner_near_end-->935,136<!--/n-->; its payments account swapped <!--n:f4.y2026.swaps_near_given-->237,732<!--/n--> NEAR for
  <!--n:f4.y2026.swaps_usd_received-->$481,611<!--/n-->. A separate line because it starts before the farm existed.
- **Finding 4:** outside the top 10 on 1 November, <!--n:n3.outside_top10_accounts-->102<!--/n--> accounts with <!--n:n3.outside_top10_near-->48,611<!--/n--> NEAR in all.
- **Finding 5:** at today's rate the largest position receives <!--n:f6.largest_units_per_day-->657.1<!--/n--> reward units a day.
- **Finding 9:** on average <!--n:ts.unminted_share_of_max_mean-->0.29%<!--/n--> of the maximum issuance is not minted (validators below full
  uptime); `treasury.near` paid out in <!--n:ts.months_with_outflows-->2<!--/n--> months of 2026, and its other net flow in the window of
  number 1 was <!--n:ts.window_other_net_near-->0.000<!--/n--> NEAR.

## Method

- **One window for every flow.** Issuance, wallets and fees are all measured between the first blocks at or after
  00:00 UTC of 2 October and 1 November 2026 (`scripts/lock_window.py`, `data/window_2026-10-02_2026-11-01.json`:
  each boundary block is saved with the block before it, and `prev_hash` proves nothing lies between them).
  Number 3, the control map and the NEAR AI flows are read at the window's end block.
- **treasury.near from balances.** Its share of new supply (<!--n:c.treasury_share_of_new_supply-->10.1%<!--/n-->)
  is its balance change ÷ the change of `total_supply`. The RPC's `protocol_reward_rate` field reads `0/1` at the
  end block, so it is saved but not used. HSP-029's author measured the same split independently, 10.13% over
  28 days, and reports the same `0/1` (proposal text on `vote.dao`). Against gross issuance (below) the share is
  <!--n:b.treasury_share_of_minted-->10.0%<!--/n-->: the protocol's 10%. The 10.1% is higher because new supply is net of gas burnt.
- **Issuance is net of gas burnt.** `total_supply(block) = total_supply(previous) + minted − balance_burnt of its
  new chunks` (nearcore 2.14.0, `core/primitives/src/block.rs`), and NEAR is minted only in the first block of an
  epoch. `scripts/burn.py` reads every epoch start in the window (<!--n:b.epochs-->101<!--/n-->): gross issuance
  <!--n:b.minted_near_per_day-->89,366<!--/n--> NEAR a day, gas burnt <!--n:b.burnt_near_per_day-->974<!--/n--> (<!--n:b.burnt_share_of_minted-->1.1%<!--/n-->), net
  <!--n:n1.new_near_per_day-->88,392<!--/n-->, exactly number 1. Gross issuance is <!--n:b.minted_share_of_max-->99.83%<!--/n--> of the 1/40 cap.
- **Issuance only over 30 days or more.** `total_supply` rises at the end of each epoch, so a single day can read
  far from the mean; over 30 days the error is about one epoch (about ±1%). The one exception is prediction 2,
  which covers 15 days (about ±2%).
- **DefiLlama figures are final only when they settle.** A day counts only if its fees are at least 20% of the
  window's median day. A figure is final only 48 hours or more after the window ends, and when a pull at least
  24 hours earlier gives the same fees and prices (DefiLlama fills recent days late and corrects old ones).
- **Private raw files.** Answers that list people's accounts (stakers and locks of `stake.dao`, DAO members,
  proposal texts, validators, voters) stay out of the repository; the public files keep their SHA-256 and the
  exact request. Each one has a redacted copy under `data/raw/redacted/` (number 3: the lists inside
  `data/stakers/`) with only the fields the computation reads and people as tags (`scripts/privacy.py`). Every
  number is computed from these copies, so the offline check recomputes all of them; with the originals present
  it also checks that they give the same copies, byte for byte. `--archival` re-fetches the originals.
- **No names.** In the current files an account of a person appears only as a tag: `sha256:` and the first 16
  hex characters of the SHA-256 of its account ID, so anyone can check a known account by hashing it. Tags are
  pseudonyms, not anonymity: the same accounts are public on chain and on NearBlocks. Until commit `7851eb5`
  (2 November 2026) the raw `stake.dao` responses, with account IDs, were in the repository; they remain in its
  git history. One exception:
  `PREREG.md` names the implicit account of the largest farm position, which prediction 1 needs. DAOs, contracts
  and validator pools are named by their account.

## Verify live

Five read-only calls to a public NEAR RPC, no key, in bash (Linux, macOS, or on Windows WSL or Git Bash;
PowerShell quotes differently). Each prints the contract's answer.

```
RPC=https://rpc.mainnet.fastnear.com
q() { curl -s $RPC -H 'Content-Type: application/json' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"query\",\"params\":{\"request_type\":\"call_function\",\"finality\":\"final\",\"account_id\":\"$1\",\"method_name\":\"$2\",\"args_base64\":\"$3\"}}" | python3 -c "import json,sys; print(bytes(json.load(sys.stdin)['result']['result']).decode())"; }

q intents.near fee e30=                                  # protocol fee in pips
q buybacks.multisignature.near get_num_confirmations e30= # signatures the buybacks wallet needs
q nearai.pool.near get_reward_fee_fraction e30=          # share of rewards the NEAR AI pool keeps
q stake.dao get_farm_pool eyJwcmljZV9pZCI6InByaWNlX1F6bVN2eGJacWRiVjBYYkc2VkQ2S2tiQiJ9   # farm total and reward rate
q social.near get eyJrZXlzIjpbInNhbWVyaWNlNzk3Ni5uZWFyL3RoZXNpcy9wcmVyZWcvMS8qKiJdfQ==   # the pre-registration record
```

At block 222,491,356 the saved answers (`data/raw/control/`) to the first three were `1`, `2` and
`{"numerator":100,"denominator":100}`; the fourth matches `data/raw/stakedao/`, and the fifth must contain the
SHA-256 in the README's [Pre-registration](../README.md#pre-registration). The base64 arguments are `{}`, `{"price_id":"price_QzmSvxbZqdbV0XbG6VD6KkbB"}` and
`{"keys":["samerice7976.near/thesis/prereg/1/**"]}`. Live answers can differ from the
locked block; that difference is the point of checking.

To re-measure numbers 1 and 3 at the locked end block, into a temporary folder, and compare with the saved
files (network, no keys, a few minutes; last line `REMEASURE: SAME`):

```
python scripts/remeasure.py
```

To re-fetch the locked blocks themselves from an archival RPC:

```
python scripts/control_map.py --verify --archival
python scripts/control_history.py --verify --archival
python scripts/treasury_flows.py --verify --archival
```

## Terms

| Term | Meaning here |
|---|---|
| Issuance, new NEAR | the change of `total_supply` between two block headers, per day: NEAR minted minus gas burnt |
| Coverage | NEAR the wallets kept ÷ new NEAR, over the same window |
| Dilution | total supply grows by <!--n:n1.new_near_per_day-->88,392<!--/n--> NEAR a day whatever the buybacks do, because bought NEAR is held, not burned; buybacks lower only the supply outside their wallets |
| Buybacks wallets | `buybacks.multisignature.near` + `1csfundsadmin.sputnik-dao.near`; they hold bought NEAR |
| Front-end fund | `fefundsadmin.sputnik-dao.near`: fees of the near-intents.org front end |
| Fees, revenue | DefiLlama's figures for NEAR Intents: what users pay, and the part DefiLlama counts as NEAR's |
| Take rate | revenue ÷ fees |
| bps, pip | 1 bps = 0.01%; 1 pip = 0.0001% (the unit of the `intents.near` fee) |
| k of n | k signatures out of n members are needed to act; for the two multisigs, n counts member keys |
| Farm | NEAR staked through `stake.dao` into the NEAR AI pool, paid in reward units |
| Reward unit | what the farm pays; NEAR AI Cloud turns it into credits off-chain |
| Locks | NEAR AI Agents subscriptions on the same contract, not counted in the farm |
| Window | 2 Oct → 1 Nov 2026, 00:00 UTC, blocks 218,126,921 → 222,491,356 |
| Provisional | a DefiLlama figure that has not yet settled ([Method](#method)) |

## Repository

| Path | What it is |
|---|---|
| `data/numbers.json` | every number in the README and this file, with its source file and that file's SHA-256 |
| `data/raw/` | every public RPC, NearBlocks and DefiLlama response, byte for byte |
| `data/raw/redacted/` | redacted copies of the responses that name people, which the numbers are computed from |
| `data/history.csv` | one row a day from the `daily` workflow (00:15 UTC): number 1 over the last 30 days |
| `data/upgrade_watch.csv` | one row a day: stake signalling the next protocol version |
| `scripts/` | one script per number or finding; each has `--verify` and a test in `tests/` |
| `docs/DETAILS.md` | this file: method, live checks, terms, layout |
| `PREREG.md` | the three predictions, anchored on chain |
| `docs/sign.html` | the page used once to sign the anchoring transaction |
| `AGENTS.md`, `CLAUDE.md` | the checking steps for automated reviewers (identical files) |

Data sources: FastNEAR RPC and archival RPC, NearBlocks API, DefiLlama (`api.llama.fi`, `coins.llama.fi`), and one
read of NEAR AI Cloud's farm setting in a signed-in session (`data/offchain/`). No API keys.
