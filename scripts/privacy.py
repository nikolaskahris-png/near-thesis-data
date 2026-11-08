"""Redacted copies of private raw files, so every number recomputes offline.

Some raw answers list people's accounts (DAO members, proposal texts, validators,
signers, counterparties). The originals stay in data/private/ (not committed). For each
one, the script that saved it also writes a redacted copy under data/raw/redacted/:
only the fields its computation reads, with every account that is not a known contract
or DAO replaced by a tag, sha256: + the first 16 hex characters of SHA-256(account ID).
Anyone can check a known account by hashing it.

The computation always reads the redacted copy, so a reader without data/private/ runs
exactly the same code. With the originals present, --verify also checks that they give
the same redacted copy, byte for byte.
"""
import hashlib
import json
import re
from pathlib import Path

ACCOUNT_RE = re.compile(r"^(?:[a-z0-9][a-z0-9_-]*\.)*[a-z0-9_-]+\."
                        r"(?:near|dao|tg|sweat|aurora|kaiching|hos|testnet)$|^[0-9a-f]{64}$")
TAG_PREFIX = "sha256:"


def tag(acct):
    """Public tag of an account ID. A tag is returned unchanged."""
    if acct.startswith(TAG_PREFIX):
        return acct
    return TAG_PREFIX + hashlib.sha256(acct.encode()).hexdigest()[:16]


def redact(obj, public):
    """Replace every account-like string not in `public` with its tag (keys too)."""
    if isinstance(obj, dict):
        return {redact(k, public): redact(v, public) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v, public) for v in obj]
    if isinstance(obj, str) and obj not in public and ACCOUNT_RE.match(obj):
        return tag(obj)
    return obj


def dumps(obj):
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode()


def redacted_rel(private_rel):
    """data/private/<x> -> data/raw/redacted/<x>"""
    if not private_rel.startswith("data/private/"):
        raise ValueError(f"not a private path: {private_rel}")
    return "data/raw/redacted/" + private_rel[len("data/private/"):]


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def write_redacted(root, files, project):
    """For every private file present, write its redacted copy and record it in `files`."""
    for key, f in files.items():
        if not f.get("private"):
            continue
        src = Path(root) / f["path"]
        if not src.exists():
            raise SystemExit(f"cannot redact {f['path']}: original absent")
        data = project(key, src.read_bytes())
        rel = redacted_rel(f["path"])
        out = Path(root) / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        f["redacted"] = {"path": rel, "sha256": sha256(data)}


def check_files(root, files, project):
    """Check public files, redacted copies and, when present, the private originals.
    Returns (problems, number of private originals absent)."""
    root = Path(root)
    problems, absent = [], 0
    for key, f in files.items():
        p = root / f["path"]
        if f.get("private"):
            r = f.get("redacted")
            if not r:
                problems.append(f"no redacted copy recorded for {key}")
                continue
            rp = root / r["path"]
            if not rp.exists():
                problems.append(f"missing redacted copy {r['path']}")
                continue
            if sha256(rp.read_bytes()) != r["sha256"]:
                problems.append(f"sha256 mismatch: {r['path']}")
            if not p.exists():
                absent += 1
                continue
            if sha256(p.read_bytes()) != f["sha256"]:
                problems.append(f"sha256 mismatch: {f['path']}")
            elif project(key, p.read_bytes()) != rp.read_bytes():
                problems.append(f"redacted copy does not match its original: {key}")
        elif not p.exists():
            problems.append(f"missing raw file {f['path']}")
        elif sha256(p.read_bytes()) != f["sha256"]:
            problems.append(f"sha256 mismatch: {f['path']}")
    return problems, absent


def read(root, f):
    """Bytes the computation reads for one file: the redacted copy if private."""
    return (Path(root) / (f["redacted"]["path"] if f.get("private") else f["path"])).read_bytes()


def status_line(what, absent):
    """One line for --verify. Exit code stays 0 when everything that exists checks out."""
    if absent:
        return (f"OK: {what} recomputes offline from public files and redacted copies "
                f"(PUBLIC_REDACTED); {absent} private original(s) not in git for privacy, so their "
                f"match with the redacted copies was not checked here (--archival re-fetches them)")
    return (f"OK: {what} recomputes offline from public files and redacted copies, and the "
            f"private originals give the same redacted copies")
