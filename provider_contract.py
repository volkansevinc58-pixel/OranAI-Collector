"""ORAN AI unified source contract. No networking or live data writes."""
import json,hashlib,re,sys
from pathlib import Path
class RegistryRejected(ValueError):pass
IDS={'openfootball','statsbomb_open','football_data_uk','football_data_org','api_football','thesportsdb','sportmonks','soccerstats','forebet','mackolik','clubelo','understat','fbref','kaggle','opta','wyscout','legacy_collector'}
KEYS={'id','title','adapter','role','access','execution_policy','evidence','stage','staging_fetch_enabled','production_ingest_enabled','betting_final_enabled','credentials_in_registry'}
ADAPTERS={'openfootball_json','statsbomb_json','csv','rest_api','html','csv_or_html','manual_dataset','licensed_api','legacy_readonly'}
STAGES={'ACTIVE_STAGING','RESEARCH_STAGING','STATUS_PROBE_ONLY','MANUAL_ONLY','DISABLED_PENDING_RIGHTS','DISABLED_PAID','LEGACY_RO_ONLY'}
def canonical(d):return json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def validate(d):
 if not isinstance(d,dict) or d.get('schema')!='oranai.providers.registry.v1' or d.get('product')!='ORAN AI' or d.get('official_stages')!=31 or d.get('task_count')!=15 or d.get('production_final_enabled') is not False or d.get('no_unlimited_free_claim') is not True:raise RegistryRejected('GOVERNANCE_FAIL')
 rows=d.get('providers')
 if not isinstance(rows,list) or len(rows)!=17 or d.get('active_stage_ids')!=['openfootball','statsbomb_open']:raise RegistryRejected('SCOPE_FAIL')
 ids=set();enabled=set()
 for r in rows:
  if not isinstance(r,dict) or set(r)!=KEYS:raise RegistryRejected('FIELDS_FAIL')
  k=r['id']
  if not isinstance(k,str) or not re.fullmatch(r'[a-z][a-z0-9_]+',k) or k in ids:raise RegistryRejected('ID_FAIL')
  ids.add(k)
  if r['adapter'] not in ADAPTERS or r['stage'] not in STAGES:raise RegistryRejected('STAGE_FAIL')
  if any(not isinstance(r[f],str) or not r[f] for f in ('title','role','access','execution_policy','evidence')):raise RegistryRejected('FIELDS_EMPTY')
  if r['production_ingest_enabled'] is not False or r['betting_final_enabled'] is not False or r['credentials_in_registry'] is not False:raise RegistryRejected('PRODUCTION_BLOCKED')
  if type(r['staging_fetch_enabled']) is not bool:raise RegistryRejected('BOOL_FAIL')
  if r['staging_fetch_enabled']:
   if (k,r['adapter'],r['stage']) not in {('openfootball','openfootball_json','ACTIVE_STAGING'),('statsbomb_open','statsbomb_json','RESEARCH_STAGING')}:raise RegistryRejected('UNAUTHORIZED_GET')
   enabled.add(k)
 if ids!=IDS or enabled!={'openfootball','statsbomb_open'}:raise RegistryRejected('ID_SET_FAIL')
 if d.get('data_contracts')!={'openfootball':'oranai.source.bundle.v1','statsbomb_open':'oranai.statsbomb.research.v1'}:raise RegistryRejected('CONTRACT_FAIL')
 return {'status':'PASS_SCOPED','providers':len(rows),'staging_enabled':len(enabled),'production_enabled':0,'sha256':hashlib.sha256(canonical(d)).hexdigest()}
def load(path):
 p=Path(path)
 if p.is_symlink() or not p.is_file() or p.stat().st_size>150000:raise RegistryRejected('UNSAFE_FILE')
 d=json.loads(p.read_text(encoding='utf-8'));validate(d);return d
if __name__=='__main__':
 try:print(json.dumps(validate(load(Path(__file__).with_name('provider_registry_vnext03.json'))),sort_keys=True))
 except (RegistryRejected,ValueError,OSError) as e:print('FAIL_CLOSED',e,file=sys.stderr);raise SystemExit(1)
