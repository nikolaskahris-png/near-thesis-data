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

The staking yield is gross NEAR minted per year (before gas is burnt, since validators are paid from minting)
minus what `treasury.near` keeps, divided by the validators' stake; validator commissions and downtime lower it.

**At HSP-029's target rate** (1.6% a year instead of 2.5%: issuance ×16/25), what the wallets keep must grow
<!--n:iv.hsp029_wallets_multiple_with_front_end-->×3.9<!--/n--> (front-end fund included), or, with every fee kept,
fees <!--n:iv.hsp029_fees_multiple-->×1.3<!--/n-->. The proposal reaches that rate at the end of a 24-month linear
ramp that starts 90 days after ratification, and only once validators adopt it; year by year:
[Issuance to 2031](#issuance-to-2031) (proposal text on `vote.dao`, `get_proposal` 29).

## Issuance to 2031

`scripts/longrun.py`, called by `build_numbers.py`; every figure is an `lr.` key in `data/numbers.json` with its
assumptions. Rules: today, at most 1/40 of supply a year (A); HSP-029, `cap(t) = 2.5% − 0.9% × min(t, 24) / 24`, t in
months from activation, applied every epoch (B), from <!--n:lr.activation_utc-->2027-02-14 16:48 UTC<!--/n-->, 90 days after `vote.dao`'s timelock
ends; B late starts six months later (<!--n:lr.activation_late_utc-->2027-08-16 07:48 UTC<!--/n-->). Held at the window's level: actual ÷ maximum issuance
(<!--n:lr.k-->0.9855<!--/n-->), the epoch length (<!--n:lr.epoch_days-->0.2970<!--/n--> days) and what is kept a day. No price, volume or fee is forecast.

| 1 January | Path | Issuance a day | Buybacks wallets | With the front-end fund | All fees, in NEAR |
|---|---|---|---|---|---|
| 2028 | A | <!--n:lr.issuance_per_day.A.2028-->90,968<!--/n--> | <!--n:lr.required_growth.buybacks.A.2028-->+589%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.A.2028-->×9.5<!--/n-->) | <!--n:lr.required_growth.with_front_end.A.2028-->+381%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.A.2028-->×6.3<!--/n-->) | <!--n:lr.required_growth.all_fees.A.2028-->+93%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.A.2028-->×2.1<!--/n-->) |
| 2028 | B | <!--n:lr.issuance_per_day.B.2028-->76,482<!--/n--> | <!--n:lr.required_growth.buybacks.B.2028-->+494%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.B.2028-->×8.0<!--/n-->) | <!--n:lr.required_growth.with_front_end.B.2028-->+315%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.B.2028-->×5.3<!--/n-->) | <!--n:lr.required_growth.all_fees.B.2028-->+66%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.B.2028-->×1.8<!--/n-->) |
| 2028 | B late | — | <!--n:lr.required_growth.buybacks.B_late.2028-->+549%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.B_late.2028-->×8.9<!--/n-->) | <!--n:lr.required_growth.with_front_end.B_late.2028-->+353%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.B_late.2028-->×5.8<!--/n-->) | <!--n:lr.required_growth.all_fees.B_late.2028-->+81%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.B_late.2028-->×2.0<!--/n-->) |
| 2029 | A | <!--n:lr.issuance_per_day.A.2029-->93,242<!--/n--> | <!--n:lr.required_growth.buybacks.A.2029-->+186%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.A.2029-->×9.7<!--/n-->) | <!--n:lr.required_growth.with_front_end.A.2029-->+135%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.A.2029-->×6.4<!--/n-->) | <!--n:lr.required_growth.all_fees.A.2029-->+44%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.A.2029-->×2.2<!--/n-->) |
| 2029 | B | <!--n:lr.issuance_per_day.B.2029-->61,230<!--/n--> | <!--n:lr.required_growth.buybacks.B.2029-->+135%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.B.2029-->×6.4<!--/n-->) | <!--n:lr.required_growth.with_front_end.B.2029-->+94%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.B.2029-->×4.2<!--/n-->) | <!--n:lr.required_growth.all_fees.B.2029-->+19%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.B.2029-->×1.4<!--/n-->) |
| 2029 | B late | — | <!--n:lr.required_growth.buybacks.B_late.2029-->+150%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.B_late.2029-->×7.3<!--/n-->) | <!--n:lr.required_growth.with_front_end.B_late.2029-->+106%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.B_late.2029-->×4.8<!--/n-->) | <!--n:lr.required_growth.all_fees.B_late.2029-->+26%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.B_late.2029-->×1.6<!--/n-->) |
| 2031 | A | <!--n:lr.issuance_per_day.A.2031-->97,948<!--/n--> | <!--n:lr.required_growth.buybacks.A.2031-->+75%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.A.2031-->×10.2<!--/n-->) | <!--n:lr.required_growth.with_front_end.A.2031-->+58%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.A.2031-->×6.7<!--/n-->) | <!--n:lr.required_growth.all_fees.A.2031-->+22%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.A.2031-->×2.3<!--/n-->) |
| 2031 | B | <!--n:lr.issuance_per_day.B.2031-->61,108<!--/n--> | <!--n:lr.required_growth.buybacks.B.2031-->+56%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.B.2031-->×6.4<!--/n-->) | <!--n:lr.required_growth.with_front_end.B.2031-->+41%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.B.2031-->×4.2<!--/n-->) | <!--n:lr.required_growth.all_fees.B.2031-->+9%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.B.2031-->×1.4<!--/n-->) |
| 2031 | B late | — | <!--n:lr.required_growth.buybacks.B_late.2031-->+56%<!--/n--> a year (<!--n:lr.required_multiple.buybacks.B_late.2031-->×6.4<!--/n-->) | <!--n:lr.required_growth.with_front_end.B_late.2031-->+41%<!--/n--> a year (<!--n:lr.required_multiple.with_front_end.B_late.2031-->×4.2<!--/n-->) | <!--n:lr.required_growth.all_fees.B_late.2031-->+9%<!--/n--> a year (<!--n:lr.required_multiple.all_fees.B_late.2031-->×1.4<!--/n-->) |

Supply on 1 January 2031: <!--n:lr.supply.A.2031-01-01-->1,452,150,344<!--/n--> NEAR under A, <!--n:lr.supply.B.2031-01-01-->1,415,564,200<!--/n--> under B. Staking yield before
commission under B, holding the staked share: <!--n:lr.yield_gross.B.2028-->4.2%<!--/n--> in 2028, <!--n:lr.yield_gross.B.2029-->3.3%<!--/n--> in 2029, <!--n:lr.yield_gross.B.2031-->3.2%<!--/n--> in 2031 (today
<!--n:iv.staking_yield_gross-->5.0%<!--/n-->).

**Cross-check with the proposal.** NEAR not issued under HSP-029, from activation: <!--n:lr.not_issued_B.2y-->12.24M<!--/n--> in two years and
<!--n:lr.not_issued_B.6y-->66.35M<!--/n--> in six, against the proposal's <!--n:lr.hsp029_proposal.2y-->11.80M<!--/n--> and <!--n:lr.hsp029_proposal.6y-->66.10M<!--/n--> (<!--n:lr.not_issued_B_vs_proposal.2y-->+3.7%<!--/n-->, <!--n:lr.not_issued_B_vs_proposal.6y-->+0.4%<!--/n-->), which start
from an earlier block and supply. `build_numbers.py` fails if either differs by more than 10%.

**April to October, measured.** What the wallets kept a day: <!--n:lr.history.2026-04_2026-10.kept_multiple-->×2.9<!--/n-->; all fees in NEAR:
<!--n:lr.history.2026-04_2026-10.fees_near_multiple-->×0.5<!--/n-->; take rate: <!--n:lr.history.2026-04_2026-10.take_rate_multiple-->×4.2<!--/n-->; share of revenue the wallets kept:
<!--n:lr.history.2026-04_2026-10.kept_share_multiple-->×1.3<!--/n-->. Six months are not annualized.

## The control map: other links

The links of the [control map](../README.md#the-control-map-who-can-change-each-link) that do not decide value directly.

| Link | Today | Who can change it | Signatures | Used |
|---|---|---|---|---|
| 1Click fund (`1csfundsadmin.sputnik-dao.near`) | counted with the buybacks wallet in number 1 | DAO: transfers / its own rules | <!--n:c.wallet_1cs_transfer-->2 of 4<!--/n--> / <!--n:c.wallet_1cs_rules-->2 of 4<!--/n--> | — |
| House of Stake voting (`vote.dao`) | decides what reaches a vote | owner `hos-root.sputnik-dao.near`; <!--n:c.hsp_reviewers-->5<!--/n--> reviewers choose what is put to a vote | <!--n:c.hsp_owner_rules-->3 of 5<!--/n--> | reviewers, council or guardians changed <!--n:h.voting.approved_actions-->5<!--/n--> times (<!--n:h.voting.first-->2026-02-09<!--/n--> → <!--n:h.voting.last-->2026-07-22<!--/n-->) |
| NEAR AI pool rewards (`nearai.pool.near`) | the pool keeps <!--n:c.nearai_pool_reward_fee-->100%<!--/n--> of staking rewards | its owner, a DAO with no access keys | <!--n:c.nearai_pool_owner_transfer-->2 of 3<!--/n--> | <!--n:h.staking.approved_actions-->57<!--/n--> staking actions by the owner |
| NEAR AI credits rate (`stake.dao` `edit_price`) | <!--n:f6.units_per_near_year-->0.24<!--/n--> reward units per staked NEAR per year | one catalog manager of the pool, named by the owner's DAO (<!--n:h.catalog_manager_added-->1<!--/n--> proposal) | 1 | changed <!--n:f6.rate_changes-->1<!--/n--> time: <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, <!--n:f6.change1.ratio-->×2.0<!--/n-->, without a proposal |

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

## The NEAR AI farm

The NEAR AI farm is a signal, not a lever (README, number 3). The figures behind it:

**Since the farm opened, the NEAR held by the NEAR AI pool's owner changed by <!--n:f4.since_stake_dao.owner_near_change-->-401,848<!--/n--> NEAR.**
From the creation of `stake.dao` (<!--n:f4.stake_dao_start_utc-->2026-07-28<!--/n-->; first `stake` call <!--n:f4.first_stake_utc-->2026-07-30<!--/n-->) to
block 222,491,356 (`scripts/treasury_flows.py`, `data/treasury_flows.json`), the owner, a DAO that acts only
through proposals:

- approved unstaking <!--n:f4.since_stake_dao.unstaked_near-->425,334<!--/n--> NEAR and sending out
  <!--n:f4.since_stake_dao.near_sent_out-->423,980<!--/n--> NEAR (<!--n:f4.since_stake_dao.near_to_payments_account-->280,338<!--/n--> to its own
  payments account) and <!--n:f4.since_stake_dao.usdc_sent_out-->$365,000<!--/n--> in USDC;
- held <!--n:f4.since_stake_dao.owner_near_start-->1,336,984<!--/n--> → <!--n:f4.since_stake_dao.owner_near_end-->935,136<!--/n--> NEAR, liquid and in
  every pool;
- through its payments account, swapped <!--n:f4.since_stake_dao.swaps_near_given-->139,546<!--/n--> NEAR for
  <!--n:f4.since_stake_dao.swaps_usd_received-->$296,652<!--/n--> in <!--n:f4.since_stake_dao.swaps-->7<!--/n--> swaps on NEAR Intents (mean price
  <!--n:f4.since_stake_dao.swaps_mean_price_usd-->$2.13<!--/n-->).

In the same period users' stake in the farm reached <!--n:n3.farm_total_near-->1,364,348<!--/n--> NEAR. The two are separate figures,
not a net: users' stake can be withdrawn, and the purpose of each payment is not measured.

**The same account has been the largest in the farm since <!--n:f5.largest_same_account_since-->2026-08-15<!--/n-->, with between
<!--n:f5.largest_share.2026-10-15-->58.9%<!--/n--> and <!--n:f5.largest_share.2026-08-15-->76.9%<!--/n--> of it.** First block of the 1st and the
15th (`scripts/stakers.py`):

| | 1 Aug | 15 Aug | 1 Sep | 15 Sep | 1 Oct | 15 Oct | 1 Nov |
|---|---|---|---|---|---|---|---|
| Active accounts | <!--n:f5.stakers_active.2026-08-01-->16<!--/n--> | <!--n:f5.stakers_active.2026-08-15-->46<!--/n--> | <!--n:f5.stakers_active.2026-09-01-->51<!--/n--> | <!--n:f5.stakers_active.2026-09-15-->73<!--/n--> | <!--n:f5.stakers_active.2026-10-01-->88<!--/n--> | <!--n:f5.stakers_active.2026-10-15-->99<!--/n--> | <!--n:f5.stakers_active.2026-11-01-->112<!--/n--> |
| Largest account's share | <!--n:f5.largest_share.2026-08-01-->36.2%<!--/n--> | <!--n:f5.largest_share.2026-08-15-->76.9%<!--/n--> | <!--n:f5.largest_share.2026-09-01-->76.1%<!--/n--> | <!--n:f5.largest_share.2026-09-15-->75.7%<!--/n--> | <!--n:f5.largest_share.2026-10-01-->74.1%<!--/n--> | <!--n:f5.largest_share.2026-10-15-->58.9%<!--/n--> | <!--n:f5.largest_share.2026-11-01-->73.3%<!--/n--> |

On 1 August the largest was another account. The largest of 1 November held <!--n:f5.largest_near.2026-10-15-->500,000<!--/n--> NEAR
on 15 October and <!--n:f5.largest_near.2026-11-01-->1,000,000<!--/n--> on 1 November; its lower share on 15 October came from other
accounts' new stake.

**The credits rate is a setting, changed once by one account** (`scripts/farm_rate.py`, `data/farm_rate.json`).
The farm pays reward units; the contract has no USD conversion. The rate went from
<!--n:f6.change1.units_per_near_year_before-->0.12<!--/n--> to <!--n:f6.change1.units_per_near_year_after-->0.24<!--/n--> units per staked NEAR a year (<!--n:f6.change1.ratio-->×2.0<!--/n-->) on <!--n:f6.change1.utc-->2026-09-29 14:21 UTC<!--/n-->, through
<!--n:f6.edit_price_receipts_all_time-->1<!--/n--> `edit_price` call, the only one in the contract's history, signed by the pool's catalog
manager without a proposal of the owner's DAO. NEAR AI Cloud pays <!--n:f6.usd_per_reward_unit-->$1.00<!--/n--> of credits per unit (an off-chain
setting read on 2026-11-01 in a signed-in session, saved in `data/offchain/`), so the largest position receives
<!--n:f6.largest_usd_per_day-->$657.1<!--/n--> of credits a day; whether the credits are used is not visible. At the staking
yield of <!--n:iv.staking_yield_gross-->5.0%<!--/n-->, a staked NEAR earns as much in credits as in a validator's rewards (before
commission) at a NEAR price of <!--n:iv.farm_breakeven_price_usd-->$4.84<!--/n-->; with the rate before its only change, at
<!--n:iv.farm_breakeven_price_before_usd-->$2.42<!--/n-->. The mean NEAR price was <!--n:f2.mean_price_usd.2026-08-->$1.74<!--/n--> in August,
<!--n:f2.mean_price_usd.2026-09-->$3.28<!--/n--> in September and <!--n:f2.mean_price_usd.2026-10-->$4.89<!--/n--> in October: the
rate does not follow the price, and the one change moved the break-even to about October's price.

**NEAR AI Agents subscriptions are a separate product.** They are locks on `stake.dao`: <!--n:f7.locks-->86<!--/n--> locks
from <!--n:f7.lock_accounts-->83<!--/n--> accounts; NEAR in Active locks is <!--n:f7.active_lock_near_vs_farm-->1.1%<!--/n--> of the farm. Why
they are kept out of number 3: [details](#the-three-numbers).

## treasury.near payments

**`treasury.near` receives 10% of the maximum issuance; in 2026 it paid out
<!--n:ts.year_out_near-->30,171,200<!--/n--> NEAR, all in April and May.** `scripts/treasury_spend.py` reproduces its reward to the yocto at
<!--n:ts.rule_exact-->101<!--/n--> of the <!--n:ts.rule_epochs-->101<!--/n--> epoch starts in the window: floor(floor(supply × Δt / (40 × 365 days)) / 10),
10% of the maximum issuance (<!--n:ts.share_of_minted-->10.03%<!--/n--> of what is minted, as validators below full uptime receive less).
In 2026 it received <!--n:ts.year_treasury_in_near-->2,700,599<!--/n--> NEAR and <!--n:ts.year_out_near-->30,171,200<!--/n--> left it: <!--n:ts.out_near.2026-04-->9,800,000<!--/n--> in April and
<!--n:ts.out_near.2026-05-->20,371,200<!--/n--> in May, none in the window of number 1. Its balance went from <!--n:ts.balance_start_near-->28,996,906<!--/n--> to
<!--n:ts.balance_end_near-->1,526,304<!--/n-->. `scripts/treasury_exits.py` locates each of the <!--n:te.steps-->73<!--/n--> balance steps to the block and reads
the <!--n:te.transactions_read-->8<!--/n--> transactions of 1 NEAR or more (`data/treasury_exits.json`):

| Date (UTC) | Receiver | NEAR | Transfers |
|---|---|---|---|
| 2026-04-15 | `ecotreasury5.multisignature.near` | <!--n:te.to.ecotreasury5.amount-->4,900,000<!--/n--> | <!--n:te.to.ecotreasury5.transfers-->1<!--/n--> |
| 2026-04-15 | `ecotreasury4.multisignature.near` | <!--n:te.to.ecotreasury4.amount-->4,900,000<!--/n--> | <!--n:te.to.ecotreasury4.transfers-->1<!--/n--> |
| 2026-05-13 | one implicit account, `sha256:e630d735067c39fe` | <!--n:te.to.sha256_e630d735.amount-->20,371,200<!--/n--> | <!--n:te.to.sha256_e630d735.transfers-->5<!--/n--> |
| 2026-04-15 | `foundation.near` | <!--n:te.to.foundation.amount-->3<!--/n--> (3 NEAR came back to `treasury.near` 153 seconds later) | <!--n:te.to.foundation.transfers-->1<!--/n--> |

Each payment is a `confirm` on the multisig (<!--n:c.treasury_confirmations-->2 of 4<!--/n--> keys). Multisig, DAO and institutional
receivers are named; other accounts are shown as tags ([Method](#method)). The purpose of each payment is not on chain and is
not characterized here.

## More figures behind the findings

- **The pool owner, all of 2026** (1 January to 1 November): the NEAR AI pool owner's NEAR went from
  <!--n:f4.y2026.owner_near_start-->1,795,378<!--/n--> to <!--n:f4.y2026.owner_near_end-->935,136<!--/n-->; its payments account swapped <!--n:f4.y2026.swaps_near_given-->237,732<!--/n--> NEAR for
  <!--n:f4.y2026.swaps_usd_received-->$481,611<!--/n-->. A separate line because it starts before the farm existed.
- **The farm:** outside the top 10 on 1 November, <!--n:n3.outside_top10_accounts-->102<!--/n--> accounts with <!--n:n3.outside_top10_near-->48,611<!--/n--> NEAR in all.
- **The credits rate:** at today's rate the largest position receives <!--n:f6.largest_units_per_day-->657.1<!--/n--> reward units a day.
- **treasury.near:** on average <!--n:ts.unminted_share_of_max_mean-->0.29%<!--/n--> of the maximum issuance is not minted (validators below full
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
| Ceiling | coverage if NEAR kept every fee DefiLlama records (number 2) |
| Equilibrium price | the NEAR price at which a day's fees (or revenue) buy as many NEAR as are issued that day |
| 1Click | the NEAR Intents swap service whose fees reach the 1Click fund and the buybacks wallet |
| Admin | a role in a Sputnik DAO that can change the DAO's rules |
| House of Stake, HSP | NEAR's governance on `vote.dao`; an HSP is one of its proposals |
| veNEAR | voting weight of NEAR locked in House of Stake |
| Epoch | the protocol period at whose start NEAR is minted; 101 in the window |
| Window | 2 Oct → 1 Nov 2026, 00:00 UTC, blocks 218,126,921 → 222,491,356 |
| Final, provisional | a DefiLlama figure is final once a fetch at least 24 hours after an earlier one changes no day of the window; until then it is provisional ([Method](#method)) |

## Repository

| Path | What it is |
|---|---|
| `data/numbers.json` | every number in the README and this file, with its source file and that file's SHA-256 |
| `data/raw/` | every public RPC, NearBlocks and DefiLlama response, byte for byte |
| `data/raw/redacted/` | redacted copies of the responses that name people, which the numbers are computed from |
| `data/history.csv` | one row a day from the `daily` workflow (00:15 UTC): number 1 over the last 30 days |
| `data/upgrade_watch.csv` | one row a day: stake signalling the next protocol version |
| `dashboard/` | static page (`index.html`, `app.js`, `style.css`, no libraries) that reads every figure from `data/`; `tests/test_dashboard.py` fails if it shows a number written by hand |
| `scripts/` | one script per number or finding; each has `--verify` and a test in `tests/` |
| `docs/DETAILS.md` | this file: method, live checks, terms, layout |
| `PREREG.md` | the three predictions, anchored on chain |
| `PREREG-2.md` | predictions 4 and 5 (protocol versions 87 and 88), anchored on chain on 3 November |
| `docs/sign.html`, `docs/sign-2.html` | the pages used once each to sign the two anchoring transactions |
| `AGENTS.md`, `CLAUDE.md` | the checking steps for automated reviewers (identical files) |

Data sources: FastNEAR RPC and archival RPC, NearBlocks API, DefiLlama (`api.llama.fi`, `coins.llama.fi`), and one
read of NEAR AI Cloud's farm setting in a signed-in session (`data/offchain/`). No API keys.
