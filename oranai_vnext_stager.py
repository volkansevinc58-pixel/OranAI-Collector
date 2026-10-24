"""ORAN AI: bounded 2-source staging, never a production database."""
import argparse,hashlib,json,re,sys
from datetime import datetime,timezone
from pathlib import Path
from staging_collect_openfootball import get,make_bundle,Rejected,url_for
ALLOW=("2025-26/en.1.json","2025-26/de.1.json")
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def filename(ds):
    if ds not in ALLOW:raise Rejected("NOT_ALLOWLISTED")
    return ds.replace("/","_").replace(".","-")+".json"
def validate_bundle(b,ds):
    if not isinstance(b,dict) or b.get("schema")!="oranai.source.bundle.v1" or b.get("dataset")!=ds or b.get("source_url")!=url_for(ds):raise Rejected("SOURCE_MISMATCH")
    if b.get("provider")!="openfootball_json" or b.get("license")!="CC0-1.0" or b.get("authority")!="RESEARCH_DATA_ONLY" or b.get("live_final_enabled") is not False:raise Rejected("AUTHORITY_FAIL")
    if b.get("source_timestamp")!="NOT_AVAILABLE" or b.get("price_data")!="NOT_AVAILABLE" or b.get("rejected_rows")!=0:raise Rejected("QUALITY_FAIL")
    copy=dict(b);h=copy.pop("bundle_sha256",None)
    if not isinstance(h,str) or sha(canonical(copy))!=h:raise Rejected("BUNDLE_HASH_FAIL")
    rs=b.get("records");n=b.get("source_row_count")
    if not isinstance(rs,list) or not rs or type(n)!=int or len(rs)!=n or n>4000:raise Rejected("ROW_COUNTS_FAIL")
    keys=set()
    for r in rs:
        if not isinstance(r,dict) or not isinstance(r.get("fixture_key"),str) or r["fixture_key"] in keys:raise Rejected("FIXTURE_INVALID")
        keys.add(r["fixture_key"])
        if r.get("kickoff_utc") is not None or r.get("source_event_id") is not None:raise Rejected("UNVERIFIED_ID")
        s=r.get("score_ft")
        if s is not None and not(isinstance(s,list) and len(s)==2 and all(type(x) is int and 0<=x<=40 for x in s)):raise Rejected("SCORE_FAIL")
        if r.get("match_status")!=("FT_REPORTED" if s is not None else "SCHEDULE_UNKNOWN"):raise Rejected("STATUS_FAIL")
    return n
def collect(*,approved=False,root=Path("staging/next"),fetcher=None,stamp=None):
    if not approved:raise Rejected("APPROVAL_REQUIRED")
    root=Path(root)
    if root.exists() or root.is_symlink():raise Rejected("STAGE_MUST_BE_NEW")
    root.mkdir(parents=True)
    stamp=stamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
    items=[];total=0
    for ds in ALLOW:
        raw=(fetcher or (lambda d:get(d,approved=True)))(ds)
        b=make_bundle(raw,ds,now=stamp)
        n=validate_bundle(b,ds)
        payload=json.dumps(b,ensure_ascii=False,sort_keys=True,indent=2).encode()
        out=root/filename(ds)
        with out.open("xb") as f:f.write(payload)
        items.append({"dataset":ds,"file":out.name,"rows":n,"file_sha256":sha(payload),"bundle_sha256":b["bundle_sha256"],"source_sha256":b["source_sha256"]})
        total+=n
    m={"schema":"oranai.stage.manifest.v1","collected_at_utc":stamp,"sources":len(items),"rows":total,"files":items,"authority":"STAGING_RESEARCH_ONLY","sqlite_written":False,"final_enabled":False,"durable_archive":"NOT_CONFIRMED"}
    m["sha256"]=sha(canonical(m))
    with (root/"manifest.json").open("xb") as f:f.write(json.dumps(m,sort_keys=True,indent=2).encode())
    return verify(root)
def verify(root):
    root=Path(root)
    m=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    h=m.pop("sha256",None)
    if not isinstance(h,str) or h!=sha(canonical(m)):raise Rejected("MANIFEST_HASH_FAIL")
    if m.get("schema")!="oranai.stage.manifest.v1" or m.get("authority")!="STAGING_RESEARCH_ONLY" or m.get("sqlite_written") is not False or m.get("final_enabled") is not False or m.get("durable_archive")!="NOT_CONFIRMED":raise Rejected("AUTHORITY_INVALID")
    if m.get("sources")!=len(ALLOW) or not isinstance(m.get("files"),list) or len(m["files"])!=len(ALLOW):raise Rejected("SOURCE_COUNT_FAIL")
    if {p.name for p in root.iterdir()}!={"manifest.json",*(filename(x) for x in ALLOW)}:raise Rejected("UNEXPECTED_FILE")
    total=0
    for row,ds in zip(m["files"],ALLOW):
        if row.get("dataset")!=ds or row.get("file")!=filename(ds):raise Rejected("FILE_MISMATCH")
        p=root/filename(ds)
        if p.is_symlink() or p.stat().st_size>4000000:raise Rejected("FILE_NOT_SAFE")
        raw=p.read_bytes()
        if sha(raw)!=row.get("file_sha256"):raise Rejected("FILE_HASH_FAIL")
        b=json.loads(raw)
        n=validate_bundle(b,ds)
        if n!=row.get("rows") or b.get("bundle_sha256")!=row.get("bundle_sha256") or b.get("source_sha256")!=row.get("source_sha256") or b.get("collected_at_utc")!=m.get("collected_at_utc"):raise Rejected("BUNDLE_MANIFEST_FAIL")
        total+=n
    if total!=m.get("rows"):raise Rejected("TOTAL_FAIL")
    return {"status":"PASS_STAGING_ONLY","sources":len(ALLOW),"records":total,"manifest_sha256":h,"sqlite_writes":0,"git_writes":0,"final_enabled":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--approved",action="store_true");p.add_argument("--verify-only",action="store_true");a=p.parse_args()
    try:
        data=verify(Path("staging/next")) if a.verify_only else collect(approved=a.approved)
        print(json.dumps(data,sort_keys=True));return 0
    except (Rejected,OSError,ValueError,TypeError,KeyError) as exc:
        print("HOLD_FAIL_CLOSED",str(exc),file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
