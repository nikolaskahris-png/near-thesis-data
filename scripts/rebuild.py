"""One command: rebuild every number, chart input and text check from the committed raw files.

Runs, in order, with no network and no keys:
  1. every test (tests/, including the dashboard's)
  2. every script's offline --verify, then numbers.json rebuilt from them must be identical
  3. the validators' vote samples (data/upgrade_watch/)
  4. every marked number in README.md, docs/DETAILS.md and THESIS.md against numbers.json
  5. PREREG.md against its anchored SHA-256

The dashboard (dashboard/) draws every chart from data/numbers.json and the data files
checked in steps 2-3, so a pass here means every chart is rebuilt from the raw responses.
The last line is REBUILD: PASS or REBUILD: FAIL.

Usage:
    python scripts/rebuild.py            # run every step
    python scripts/rebuild.py --list     # print the steps without running them
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable

STEPS = [
    ("tests", [PY, "-m", "unittest", "discover", "-s", "tests"]),
    ("numbers rebuild from raw files", [PY, "scripts/build_numbers.py", "--verify"]),
    ("validators' vote samples", [PY, "scripts/upgrade_watch.py", "--verify"]),
    ("README.md numbers", [PY, "scripts/build_numbers.py", "--check", "README.md"]),
    ("docs/DETAILS.md numbers", [PY, "scripts/build_numbers.py", "--check", "docs/DETAILS.md"]),
    ("THESIS.md numbers", [PY, "scripts/build_numbers.py", "--check", "THESIS.md"]),
    ("PREREG.md anchored hash", [PY, "scripts/check_prereg.py", "--file"]),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        for name, cmd in STEPS:
            print(f"{name}: python {' '.join(cmd[1:])}")
        return 0
    failed = []
    for i, (name, cmd) in enumerate(STEPS, 1):
        t0 = time.monotonic()
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip().splitlines()
        last = out[-1] if out else ""
        ok = r.returncode == 0
        print(f"[{i}/{len(STEPS)}] {'PASS' if ok else 'FAIL'}  {name} ({time.monotonic() - t0:.1f}s)  {last}")
        if not ok:
            failed.append(name)
            print("\n".join("    " + line for line in out[-20:]))
    print("REBUILD: PASS" if not failed else "REBUILD: FAIL (" + ", ".join(failed) + ")")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
