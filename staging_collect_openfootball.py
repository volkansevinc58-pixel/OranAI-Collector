"""ORAN AI staging-only OpenFootball adapter (not a live prediction engine).

No network on import, approved allowlist GET only, no SQLite / git writes.
Bundle contract interoperates with REV7 desktop verify_bundle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

BASE = "https://raw.githubusercontent.com/openfootball/football.json/master/"
DATASETS = {"2025-26/en.1.json", "2025-26/de.1.json", "2025-26/es.1.json", "2025-26/it.1.json"}
PROVIDER = "openfootball_json"
SOURCE_LIMIT = 2_000_000

class Rejected(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Rejected("REDIRECT_BLOCKED")

def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def url_for(dataset):
    if dataset not in DATASETS:
        raise Rejected("SOURCE_NOT_ALLOWLISTED")
    return BASE + dataset

def get(dataset, *, approved=False, opener=None):
    if not approved:
        raise Rejected("EXPLICIT_APPROVAL_REQUIRED")
    req = urllib.request.Request(url_for(dataset), headers={"User-Agent":"ORAN-AI-Staging/0.7", "Accept":"application/json"})
    try:
        with (opener or urllib.request.build_opener(NoRedirect())).open(req, timeout=15) as resp:
            if resp.status != 200:
                raise Rejected("HTTP_NOT_200")
            raw = resp.read(SOURCE_LIMIT + 1)
    except urllib.error.HTTPError as exc:
        raise Rejected("ACCESS_BLOCKED" if exc.code in (403,429) else "HTTP_FAILURE") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise Rejected("NETWORK_FAILURE") from None
    if len(raw) > SOURCE_LIMIT:
        raise Rejected("SOURCE_TOO_LARGE")
    return raw

def team(value):
    if not isinstance(value, str):
        raise Rejected("BAD_TEAM")
    value = " ".join(value.strip().split())
    if not 2 <= len(value) <= 120 or any(ord(c) < 32 for c in value):
        raise Rejected("BAD_TEAM")
    return value

def make_bundle(raw, dataset, *, now=None):
    url = url_for(dataset)
    if not isinstance(raw, bytes) or not 2 <= len(raw) <= SOURCE_LIMIT:
        raise Rejected("BAD_SOURCE_BYTES")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise Rejected("BAD_JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
        raise Rejected("BAD_SOURCE_SCHEMA")
    matches = data["matches"]
    if not 1 <= len(matches) <= 4000:
        raise Rejected("BAD_MATCH_COUNT")
    stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        capture = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if capture.utcoffset() is None or capture.utcoffset().total_seconds() != 0:
            raise ValueError()
    except ValueError:
        raise Rejected("NON_UTC_CAPTURE") from None
    records, seen = [], set()
    for index, match in enumerate(matches):
        if not isinstance(match, dict):
            raise Rejected(f"BAD_ROW_{index}")
        when = match.get("date")
        if not isinstance(when,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",when):
            raise Rejected(f"BAD_DATE_{index}")
        try: date.fromisoformat(when)
        except ValueError: raise Rejected(f"INVALID_DATE_{index}") from None
        home, away = team(match.get("team1")), team(match.get("team2"))
        if home.casefold() == away.casefold():
            raise Rejected(f"SAME_TEAM_{index}")
        rnd = match.get("round") or ""
        if not isinstance(rnd, str) or len(rnd)>80:
            raise Rejected(f"BAD_ROUND_{index}")
        score = match.get("score")
        if score is None:
            result = None
        elif isinstance(score, dict):
            result = score.get("ft")
        elif isinstance(score, list):
            result = score
        else:
            raise Rejected(f"BAD_SCORE_{index}")
        if result is not None and not (isinstance(result,list) and len(result)==2 and all(type(v) is int and 0<=v<=40 for v in result)):
            raise Rejected(f"BAD_FINAL_SCORE_{index}")
        identity = {"provider":PROVIDER, "dataset":dataset, "date":when, "home":home,"away":away,"round":rnd}
        fixture_key = digest(canonical(identity))
        if fixture_key in seen:
            raise Rejected(f"DUPLICATE_{index}")
        seen.add(fixture_key)
        records.append({"fixture_key":fixture_key,"date":when,"home":home,"away":away,"round":rnd,
                        "score_ft":result,"match_status":"FT_REPORTED" if result is not None else "SCHEDULE_UNKNOWN",
                        "kickoff_utc":None,"source_event_id":None})
    bundle = {"schema":"oranai.source.bundle.v1","provider":PROVIDER,"dataset":dataset,
              "source_url":url,"license":"CC0-1.0","collected_at_utc":stamp,
              "source_sha256":digest(raw),"source_row_count":len(matches),"rejected_rows":0,
              "records":records,"source_timestamp":"NOT_AVAILABLE","price_data":"NOT_AVAILABLE",
              "authority":"RESEARCH_DATA_ONLY","live_final_enabled":False}
    bundle["bundle_sha256"] = digest(canonical(bundle))
    return bundle

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--dataset",required=True)
    parser.add_argument("--approved",action="store_true")
    parser.add_argument("--source-file",type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        url_for(args.dataset)
        if not args.approved:
            raise Rejected("APPROVAL_REQUIRED")
        if args.output.is_absolute() or len(args.output.parts)!=2 or args.output.parts[0]!="staging" or not re.fullmatch(r"[a-z0-9_-]+\.json", args.output.name):
            raise Rejected("OUTPUT_OUTSIDE_STAGING")
        if args.source_file is None:
            raw=get(args.dataset,approved=True)
        else:
            if not args.source_file.is_file() or args.source_file.stat().st_size>SOURCE_LIMIT:
                raise Rejected("INVALID_OFFLINE_SOURCE")
            raw=args.source_file.read_bytes()
        bundle=make_bundle(raw,args.dataset)
        args.output.parent.mkdir(exist_ok=True)
        with args.output.open("x",encoding="utf-8") as f:
            json.dump(bundle,f,ensure_ascii=False,sort_keys=True,indent=2)
        print(json.dumps({"status":"STAGED_ONLY","matches":len(bundle["records"]),
                          "bundle_sha256":bundle["bundle_sha256"],"output":str(args.output),
                          "sqlite_writes":0,"git_writes":0}))
        return 0
    except (Rejected, OSError, ValueError) as exc:
        print("HOLD_FAIL_CLOSED:",exc,file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
