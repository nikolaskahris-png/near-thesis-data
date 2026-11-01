# near-thesis-data

[![verify](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml/badge.svg)](https://github.com/nikolaskahris-png/near-thesis-data/actions/workflows/verify.yml)

Work in progress for NEAR HACKATHON (1–14 November 2026), Investment Thesis track.

Research into data sources was done between 22 and 31 October 2026, before any code. All code and data in this repository start with its first commit.

License: MIT.

## Pre-registration

Three predictions, judged on 16 November 2026, are in [`PREREG.md`](PREREG.md). The file was anchored on
NEAR mainnet before judging: its SHA-256 is stored in SocialDB (`social.near`) under the key
`samerice7976.near/thesis/prereg/1`, written by transaction
[`8fZ8VTUyM1UjnybqPd1QCQi4c3y75dDRGR5TjkNGgnPL`](https://nearblocks.io/txns/8fZ8VTUyM1UjnybqPd1QCQi4c3y75dDRGR5TjkNGgnPL)
from `samerice7976.near`. The transaction was included in block 222,606,824 (2026-11-01 18:30:38 UTC)
and executed by `social.near` in block 222,606,825 (18:30:39 UTC). `PREREG.md` has not changed since.

Anchored SHA-256: `d3f48ed9172b1785b4dcf290b84e9a06c870b8b9b5481c6d40e51a4605b1d494`

Check it:

```
python scripts/check_prereg.py --file     # no network: PREREG.md against the anchored SHA-256
python scripts/check_prereg.py            # 4 read-only RPC calls: SocialDB record, transaction, its blocks
python scripts/check_prereg.py --verify   # no network: the same checks from the saved responses
```

The second command compares three things: the file's SHA-256, the record stored in SocialDB now, and the
record inside the transaction's own arguments. It also checks the signer and that no receipt failed.
The `verify` badge above runs the first command on every push.
