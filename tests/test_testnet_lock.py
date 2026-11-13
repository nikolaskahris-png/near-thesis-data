"""Tests for scripts/testnet_lock.py: rule (b) on a real testnet account, recomputed from the saved responses."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import daily  # noqa: E402
import lock_window as lw  # noqa: E402
import testnet_lock as tl  # noqa: E402


class TestnetLock(unittest.TestCase):
    def test_committed_result_recomputes(self):
        res, problems = tl.compute()
        self.assertEqual(problems, [])
        self.assertEqual(json.dumps(res, indent=1) + "\n", (REPO / tl.OUT).read_text(encoding="utf-8"))

    def test_the_real_account_is_sealed(self):
        res, _ = tl.compute()
        self.assertEqual((res["access_keys"], res["code_hash"], res["global_contract"]),
                         (0, daily.EMPTY_CODE_HASH, None))
        self.assertTrue(res["sealed"])

    def test_saved_files_match_their_sha256(self):
        res, _ = tl.compute()
        for rel, digest in res["files"].items():
            self.assertEqual(lw.sha256((REPO / rel).read_bytes()), digest)

    def test_the_same_account_with_its_key_back_is_not_sealed(self):
        res, _ = tl.compute()
        acc = json.loads((REPO / next(iter(res["files"]))).read_bytes())["result"]
        key = {"public_key": "ed25519:K", "access_key": {"nonce": 0, "permission": "FullAccess"}}
        self.assertFalse(daily.lock_sealed(acc, [key], account=tl.ACCOUNT))


if __name__ == "__main__":
    unittest.main()
