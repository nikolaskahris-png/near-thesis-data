"""Save the web pages the text quotes, so every quote can be checked with no network.

    python scripts/quotes.py                  # fetch each page, save it under data/raw/sources/, write data/sources.json
    python scripts/quotes.py --import ID FILE # a page the script could not fetch, saved from a browser (Ctrl+S)
    python scripts/quotes.py --verify         # offline: each saved page has its SHA-256 and contains its quotes,
                                              # and each quote is still in README.md, THESIS.md or docs/DETAILS.md

A quote matches after the same normalisation on both sides: HTML tags, scripts and styles removed, entities
decoded, curly quotes, dashes and non-breaking spaces made plain, backticks and Markdown emphasis dropped,
whitespace collapsed, case ignored. A page saved from a browser is marked "saved from a browser" in
data/sources.json; one the script fetched is marked "fetched". Either way the bytes are kept as they arrived.

Read-only GET requests, no keys. Nothing here signs anything or writes to the chain.
"""
import argparse
import html
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lock_window as lw  # noqa: E402

REPO = lw.REPO
OUT_NAME = "sources.json"
RAW_DIR = Path("data") / "raw" / "sources"
DOCS = ("README.md", "THESIS.md", "docs/DETAILS.md")

# id -> (url, quotes as the text writes them)
SOURCES = {
    "sec_bitwise_424b3": (
        "https://www.sec.gov/Archives/edgar/data/0002067111/000121390026103106/ea0306486-424b3_bitwise.htm",
        ["is given to the NEAR Protocol treasury, which is currently managed by the NEAR Foundation",
         "70% of the transaction fee is burned"]),
    "sec_svrn_6k": (
        "https://www.sec.gov/Archives/edgar/data/0001869467/000091957426005810/p15060228_ex99-1.htm",
        ["more than 55.5 million"]),
    "near_intents_fees": (
        "https://docs.near-intents.org/resources/fees",
        ["Authenticated partners on the generic policy get a 50/50 revenue share by default",
         "Exceptions and custom agreements exist"]),
    "near_intents_confidential": (
        "https://docs.near-intents.org/integration/market-makers/confidential-intents.md",
        ["settles entirely on FAR via a `token_diff` intent, invisible to public indexers",
         "a permissioned instance of the NEAR protocol operated by a small validator set with no public networking"]),
    "tideline_thesis": (
        "https://raw.githubusercontent.com/ervhint/tideline-thesis/90a78e6a358315331dbb0c68548edcb736244a3e/THESIS.md",
        ["Since 27 Oct 2026 swaps settle on `intents.far`, which public indexers cannot see",
         "carried 85% of the USD counted on chain"]),
    "soldano_readme": (
        "https://raw.githubusercontent.com/soldanoandrea/near-thesis/13b580f37e97d04fa0403f5c1a785f962886bddd/README.md",
        ["20.95M NEAR of it reached the p2p-org and figment staking pools within five hops"]),
    "one_click_terms": (
        "https://docs.near-intents.org/near-intents/integration/distribution-channels/1click-terms-of-service",
        ["at any time on a prospective basis"]),
    "near_ai_staking": (
        "https://docs.near.ai/cloud/staking-for-inference/overview",
        ["network-wide, not a fixed setting"]),
    "near_blog_q2_2026": (
        "https://www.near.org/blog/the-state-of-near-q-2-2026",
        ["owned front-end captures 100% of its fees and routes them to NEAR buybacks"]),
    "near_blog_tokenomics": (
        "https://near.org/blog/evolving-near-tokenomics",
        ["No specific mechanism is guaranteed or committed to"]),
    "hackathon_rules": (
        "https://nearhackathon.com/HACKATHON.md",
        ["Earlier commits are baseline"]),
}

_TRANSLATE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                            "—": "-", "−": "-", " ": " ", " ": " ", " ": " ",
                            "`": "", "*": "", "​": ""})


def normalise(text):
    text = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", text)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(html.unescape(text)).translate(_TRANSLATE)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r" ([,.;:!?%)\]'])", r"\1", re.sub(r"([(\[]) ", r"\1", text))
    return text.strip().casefold()


def decode(raw):
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": lw.USER_AGENT, "Accept": "text/html,text/markdown,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise RuntimeError(f"no connection ({getattr(e, 'reason', e)})") from None


def ext_of(url, content_type=""):
    if url.endswith(".md") or "markdown" in content_type:
        return ".md"
    if "text/plain" in content_type:
        return ".txt"
    return ".html"


def missing_quotes(source_id, raw):
    page = normalise(decode(raw))
    return [q for q in SOURCES[source_id][1] if normalise(q) not in page]


def _load(root):
    path = root / "data" / OUT_NAME
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"about": "Copies of the web pages the text quotes; scripts/quotes.py --verify checks each quote "
                     "offline", "sources": {}}


def _save(root, doc):
    doc["sources"] = dict(sorted(doc["sources"].items()))
    (root / "data" / OUT_NAME).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                          encoding="utf-8", newline="\n")


def _record(root, source_id, raw, ext, how, now):
    raw_dir = root / RAW_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    for old in raw_dir.glob(source_id + ".*"):
        old.unlink()
    path = raw_dir / (source_id + ext)
    path.write_bytes(raw)
    url, quotes = SOURCES[source_id]
    return {"url": url, "path": path.relative_to(root).as_posix(), "sha256": lw.sha256(raw), "bytes": len(raw),
            "saved_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "how": how, "quotes": quotes}


def run(root, fetch=fetch, now=None, only=None):
    now = now or datetime.now(timezone.utc)
    doc, report = _load(root), []
    for sid, (url, _q) in SOURCES.items():
        if only and sid not in only:
            continue
        try:
            raw, ctype = fetch(url)
        except RuntimeError as e:
            report.append(f"NOT SAVED {sid}: {e}. Open {url} in a browser, press Ctrl+S (Web page, HTML only), "
                          f"then: python scripts/quotes.py --import {sid} <saved file>")
            continue
        miss = missing_quotes(sid, raw)
        if miss:
            report.append(f"NOT SAVED {sid}: the fetched page lacks {miss!r} (the page may be drawn by "
                          f"JavaScript). Save it from a browser instead: python scripts/quotes.py --import {sid} "
                          "<saved file>")
            continue
        doc["sources"][sid] = _record(root, sid, raw, ext_of(url, ctype), "fetched", now)
        report.append(f"SAVED {sid}: {len(raw):,} bytes")
    _save(root, doc)
    return report


def import_file(root, source_id, file, now=None):
    if source_id not in SOURCES:
        raise SystemExit(f"unknown id {source_id}; known: {', '.join(SOURCES)}")
    raw = Path(file).read_bytes()
    miss = missing_quotes(source_id, raw)
    if miss:
        raise SystemExit(f"NOT SAVED {source_id}: the file lacks {miss!r}")
    doc = _load(root)
    suffix = Path(file).suffix.lower()
    doc["sources"][source_id] = _record(root, source_id, raw, suffix if suffix in (".md", ".txt") else ".html",
                                        "saved from a browser", now or datetime.now(timezone.utc))
    _save(root, doc)
    return f"SAVED {source_id}: {len(raw):,} bytes, saved from a browser"


def verify(root):
    path = root / "data" / OUT_NAME
    if not path.exists():
        return [f"missing data/{OUT_NAME}: run python scripts/quotes.py with a network"], 0, 0
    doc = json.loads(path.read_text(encoding="utf-8"))
    docs = normalise("\n".join((root / d).read_text(encoding="utf-8") for d in DOCS))
    problems, pages, quotes = [], 0, 0
    for sid, (url, qs) in SOURCES.items():
        rec = doc["sources"].get(sid)
        for q in qs:
            if normalise(q) not in docs:
                problems.append(f"{sid}: quote no longer in {', '.join(DOCS)}: {q!r}")
        if rec is None:
            problems.append(f"{sid}: not saved ({url})")
            continue
        if rec["url"] != url or rec["quotes"] != qs:
            problems.append(f"{sid}: data/{OUT_NAME} lists another url or other quotes than SOURCES")
        p = root / rec["path"]
        if not p.exists():
            problems.append(f"{sid}: missing {rec['path']}")
            continue
        raw = p.read_bytes()
        if lw.sha256(raw) != rec["sha256"]:
            problems.append(f"{sid}: sha256 differs: {rec['path']}")
            continue
        for q in missing_quotes(sid, raw):
            problems.append(f"{sid}: {rec['path']} lacks {q!r}")
        pages += 1
        quotes += len(qs)
    for sid in doc["sources"]:
        if sid not in SOURCES:
            problems.append(f"{sid}: in data/{OUT_NAME} but not in SOURCES")
    return problems, pages, quotes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--import", dest="imp", nargs=2, metavar=("ID", "FILE"))
    parser.add_argument("--only", nargs="+", metavar="ID")
    args = parser.parse_args()
    if args.verify:
        problems, pages, quotes = verify(REPO)
        if problems:
            print("\n".join(problems))
            print("QUOTES VERIFY: FAIL")
            return 1
        print(f"OK: {quotes} quotes found in {pages} saved pages, and each is still in the text")
        return 0
    if args.imp:
        print(import_file(REPO, *args.imp))
        return 0
    report = run(REPO, only=args.only)
    print("\n".join(report))
    left = [r for r in report if r.startswith("NOT SAVED")]
    print(f"{len(report) - len(left)} saved, {len(left)} not saved")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
