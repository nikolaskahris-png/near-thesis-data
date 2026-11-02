"""Tests for scripts/check_sources.py with a simulated network (no real requests)."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_sources as cs  # noqa: E402


def fake_fetch(total_supply=cs.REF_TOTAL_SUPPLY, amount=cs.REF_AMOUNT, down=()):
    def fetch(url, body=None, timeout=25):
        if any(d in url for d in down):
            return None, b"", 1, "URLError: unreachable"
        if body is None:
            return 200, b"{}", 1, None
        p = body["params"]
        if body["method"] == "block":
            res = {"header": {"total_supply": total_supply}}
        elif p.get("finality") == "final":
            res = {"block_height": 1, "amount": "1"}
        else:
            res = {"amount": amount, "block_height": cs.REF_BLOCK}
        return 200, json.dumps({"jsonrpc": "2.0", "id": "x", "result": res}).encode(), 1, None
    return fetch


class CheckSourcesTest(unittest.TestCase):
    def run_main(self, fetch):
        out = io.StringIO()
        with mock.patch.object(cs, "fetch", fetch), mock.patch.object(sys, "argv", ["x"]), \
                redirect_stdout(out):
            cs.main()
        return out.getvalue()

    def test_all_sources_and_reference_values(self):
        text = self.run_main(fake_fetch())
        self.assertIn("total_supply MATCHES reference", text)
        self.assertIn("amount MATCHES reference", text)
        self.assertIn("=== Result: 9/9 core checks passed", text)

    def test_wrong_archival_value_and_unreachable_source_are_counted(self):
        text = self.run_main(fake_fetch(total_supply="1", down=("api.llama.fi",)))
        self.assertIn("total_supply DIFFERS FROM reference", text)
        self.assertIn("=== Result: 7/9 core checks passed", text)

    def test_rpc_error_is_reported(self):
        def fetch(url, body=None, timeout=25):
            return 200, json.dumps({"error": {"name": "HANDLER_ERROR"}}).encode(), 1, None
        with mock.patch.object(cs, "fetch", fetch):
            ok, res, _ = cs.rpc(cs.RPC, "block", {})
        self.assertFalse(ok)
        self.assertIn("RPC error", res)


if __name__ == "__main__":
    unittest.main()
