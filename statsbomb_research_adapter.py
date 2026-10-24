"""StatsBomb Open Data: independent research-only match-source adapter.

Not betting-production authorized. No DB writes, no model features, no FINAL.
A specific immutable upstream commit is allowlisted. Output is NOT compatible
with the OpenFootball production-import format by design.
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys,urllib.request,urllib.error
from datetime import date,datetime,timezone
from pathlib import Path

UPSTREAM_COMMIT="4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
DATASET="data/matches/11/90.json"
UPSTREAM="https://raw.githubusercontent.com/hudl/open-data/"+UPSTREAM_COMMIT+"/"+DATASET
MAX_BYTES=1000000
MAX_ROWS=2000
class Rejected(ValueError):pass
class _NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise Rejected("REDIRECT_BLOCKED")
def canonical(x):
 return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")
def sha(x):return hashlib.sha256(x).hexdigest()
def fetch(*,approved=False,opener=None):
 if not approved:raise Rejected("APPROVAL_REQUIRED")
 req=urllib.request.Request(UPSTREAM,headers={"Accept":"application/json","User-Agent":"ORAN-AI-Research-Staging/0.1"})
 try:
  with (opener or urllib.request.build_opener(_NoRedirect())).open(req,timeout=15) as response:
   if response.status!=200:raise Rejected("BAD_HTTP_STATUS")
   raw=response.read(MAX_BYTES+1)
 except urllib.error.HTTPError as e:
  raise Rejected("ACCESS_BLOCKED" if e.code in (403,429) else "HTTP_FAILURE") from None
 except (urllib.error.URLError,TimeoutError,OSError):
  raise Rejected("NETWORK_FAILURE") from None
 if len(raw)>MAX_BYTES:raise Rejected("SOURCE_TOO_LARGE")
 return raw
def make_bundle(raw,*,stamp=None):
 if not isinstance(raw,bytes) or not 3<=len(raw)<=MAX_BYTES:raise Rejected("INVALID_SOURCE_SIZE")
 try:data=json.loads(raw.decode("utf-8-sig"))
 except (ValueError,UnicodeError):raise Rejected("BAD_JSON") from None
 if not isinstance(data,list) or not 1<=len(data)<=MAX_ROWS:raise Rejected("BAD_ROW_COUNT")
 at=stamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
 try:
  dt=datetime.fromisoformat(at.replace("Z","+00:00"))
  if dt.utcoffset() is None or dt.utcoffset().total_seconds()!=0:raise ValueError()
 except ValueError:raise Rejected("NON_UTC_CAPTURE") from None
 output=[];seen=set()
 for index,row in enumerate(data):
  if not isinstance(row,dict):raise Rejected("BAD_MATCH_ROW")
  match_id=row.get("match_id")
  if type(match_id)!=int or match_id<=0 or match_id in seen:raise Rejected("BAD_OR_DUPLICATE_MATCH_ID")
  seen.add(match_id)
  day=row.get("match_date")
  if not isinstance(day,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",day):raise Rejected("BAD_DATE")
  try:date.fromisoformat(day)
  except ValueError:raise Rejected("IMPOSSIBLE_DATE") from None
  home=row.get("home_team",{}).get("home_team_name") if isinstance(row.get("home_team"),dict) else None
  away=row.get("away_team",{}).get("away_team_name") if isinstance(row.get("away_team"),dict) else None
  if not all(isinstance(x,str) and 2<=len(x.strip())<=120 and not any(ord(c)<32 for c in x) for x in (home,away)):raise Rejected("BAD_TEAM")
  if home.strip().casefold()==away.strip().casefold():raise Rejected("SAME_TEAM")
  home_goals,away_goals=row.get("home_score"),row.get("away_score")
  if not all(type(x)==int and 0<=x<=40 for x in (home_goals,away_goals)):raise Rejected("BAD_SCORE")
  comp=row.get("competition");season=row.get("season")
  if not isinstance(comp,dict) or comp.get("competition_id")!=11 or not isinstance(season,dict) or season.get("season_id")!=90:raise Rejected("UNEXPECTED_COMPETITION")
  output.append({"source_match_id":str(match_id),"match_date":day,"home_team":home.strip(),"away_team":away.strip(),
                 "score_reported":[home_goals,away_goals],"kickoff_utc":None,"source_timezone":"NOT_PROVEN",
                 "identity_scope":"STATS_BOMB_ONLY","prematch_eligible":False,"final_eligible":False})
 result={"schema":"oranai.statsbomb.research.v1","provider":"statsbomb_open_data","dataset":DATASET,"source_url":UPSTREAM,
         "upstream_commit":UPSTREAM_COMMIT,"source_sha256":sha(raw),"collected_at_utc":at,
         "record_count":len(output),"records":output,"rights":"RESEARCH_ONLY_REVIEW_LICENSE_PDF",
         "attribution":"StatsBomb Open Data: https://github.com/hudl/open-data",
         "source_timestamp":"NO_PREMATCH_PROOF","price_data":"NONE","production_import_eligible":False,"final_enabled":False}
 result["bundle_sha256"]=sha(canonical(result))
 return result
def verify(bundle):
 if not isinstance(bundle,dict) or bundle.get("schema")!="oranai.statsbomb.research.v1" or bundle.get("provider")!="statsbomb_open_data" or bundle.get("dataset")!=DATASET or bundle.get("source_url")!=UPSTREAM or bundle.get("upstream_commit")!=UPSTREAM_COMMIT:raise Rejected("SOURCE_MISMATCH")
 if bundle.get("rights")!="RESEARCH_ONLY_REVIEW_LICENSE_PDF" or bundle.get("production_import_eligible") is not False or bundle.get("final_enabled") is not False or bundle.get("source_timestamp")!="NO_PREMATCH_PROOF" or bundle.get("price_data")!="NONE":raise Rejected("RIGHTS_OR_FINAL_VIOLATION")
 tmp=dict(bundle);signature=tmp.pop("bundle_sha256",None)
 if not isinstance(signature,str) or sha(canonical(tmp))!=signature:raise Rejected("HASH_FAIL")
 records=bundle.get("records")
 if not isinstance(records,list) or not 1<=len(records)<=MAX_ROWS or bundle.get("record_count")!=len(records):raise Rejected("COUNT_FAIL")
 ids=set()
 for r in records:
  if not isinstance(r,dict) or not re.fullmatch(r"[1-9][0-9]*",str(r.get("source_match_id",""))) or r["source_match_id"] in ids:raise Rejected("RECORD_ID_FAIL")
  ids.add(r["source_match_id"])
  if r.get("prematch_eligible") is not False or r.get("final_eligible") is not False or r.get("kickoff_utc") is not None:raise Rejected("PREMATCH_LEAK")
  if not isinstance(r.get("score_reported"),list) or len(r["score_reported"])!=2 or not all(type(x)==int and 0<=x<=40 for x in r["score_reported"]):raise Rejected("SCORE_FAIL")
 return {"status":"RESEARCH_STAGING_PASS","provider":"statsbomb_open_data","records":len(records),
         "bundle_sha256":signature,"production_import_eligible":False,"final_enabled":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--approved",action="store_true");p.add_argument("--verify-only",action="store_true")
 p.add_argument("--output",default="staging/statsbomb/11_90.json");a=p.parse_args()
 try:
  path=Path(a.output)
  if str(path).replace("\\","/")!="staging/statsbomb/11_90.json":raise Rejected("OUTPUT_PATH_BLOCKED")
  if a.verify_only:
   result=verify(json.loads(path.read_text(encoding="utf-8")))
  else:
   if not a.approved:raise Rejected("APPROVAL_REQUIRED")
   bundle=make_bundle(fetch(approved=True))
   result=verify(bundle)
   path.parent.mkdir(parents=True,exist_ok=True)
   with path.open("x",encoding="utf-8") as f:json.dump(bundle,f,ensure_ascii=False,sort_keys=True,indent=2)
  print(json.dumps(result,sort_keys=True));return 0
 except (Rejected,ValueError,TypeError,OSError) as exc:
  print("FAIL_CLOSED",exc,file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
