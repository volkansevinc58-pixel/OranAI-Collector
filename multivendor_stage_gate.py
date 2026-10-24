"""Assert two distinct provider contracts; fail if a source is missing or mixed."""
import hashlib,json,sys
from pathlib import Path
from statsbomb_research_adapter import verify as verify_sb
from oranai_vnext_stager import verify as verify_of,Rejected as OFRejected
def sha(b):return hashlib.sha256(b).hexdigest()
def run():
 of=verify_of(Path("staging/next"))
 sb_path=Path("staging/statsbomb/11_90.json")
 if sb_path.is_symlink() or sb_path.stat().st_size>1000000:raise ValueError("SB_UNSAFE_FILE")
 b=json.loads(sb_path.read_text(encoding="utf-8"))
 sb=verify_sb(b)
 if of["records"]<1 or sb["records"]<1 or of["sources"]!=2 or sb["provider"]!="statsbomb_open_data":raise ValueError("BAD_PROVIDER_COUNTS")
 manifest={"schema":"oranai.multivendor.index.v1","provider_count":2,
           "openfootball":{"datasets":of["sources"],"records":of["records"],"manifest_sha256":of["manifest_sha256"]},
           "statsbomb":{"datasets":1,"records":sb["records"],"bundle_sha256":sb["bundle_sha256"],"file_sha256":sha(sb_path.read_bytes())},
           "rights":{"openfootball":"CC0_RESEARCH","statsbomb":"RESEARCH_LICENSE_REVIEW"},
           "production_import_eligible":False,"final_enabled":False,"persistent_storage":"NOT_CONFIRMED"}
 manifest["sha256"]=sha(json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
 out=Path("staging/multivendor_manifest.json")
 with out.open("x",encoding="utf-8") as f:json.dump(manifest,f,sort_keys=True,indent=2)
 return {"status":"PASS_STAGING_ONLY","providers":2,"datasets":3,"records":of["records"]+sb["records"],
         "manifest_sha256":manifest["sha256"],"production_import_eligible":False,"final_enabled":False,"sqlite_writes":0}
if __name__=="__main__":
 try:print(json.dumps(run(),sort_keys=True))
 except (ValueError,OSError,OFRejected,TypeError,KeyError) as e:
  print("FAIL_CLOSED",e,file=sys.stderr);raise SystemExit(1)
