import json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from staging_collect_openfootball import make_bundle, get, url_for, Rejected

DATA={"matches":[
 {"round":"Matchday 1","date":"2025-08-16","time":"12:30","team1":"Aston Villa FC","team2":"Newcastle United FC","score":[0,0]},
 {"round":"Matchday 1","date":"2025-08-15","time":"20:00","team1":"Liverpool FC","team2":"Bournemouth FC","score":{"ft":[4,2],"ht":[1,0]}}
]}
DSET="2025-26/en.1.json"
class StageTest(unittest.TestCase):
 def sample(self):return json.dumps(DATA).encode()
 def test_allowlist(self):self.assertIn("raw.githubusercontent.com",url_for(DSET))
 def test_disallow_unknown(self):
  with self.assertRaises(Rejected):url_for("../../private.json")
 def test_get_needs_approval(self):
  with self.assertRaises(Rejected):get(DSET)
 def test_two_official_score_shapes(self):
  b=make_bundle(self.sample(),DSET,now="2026-10-18T11:00:00+00:00")
  self.assertEqual(len(b["records"]),2)
  self.assertEqual(b["rejected_rows"],0)
  self.assertEqual([x["score_ft"] for x in b["records"]],[[0,0],[4,2]])
  self.assertFalse(b["live_final_enabled"])
 def test_fixture_key_deterministic(self):
  a=make_bundle(self.sample(),DSET)
  b=make_bundle(self.sample(),DSET)
  self.assertEqual(a["records"][0]["fixture_key"],b["records"][0]["fixture_key"])
 def test_reject_bad_score(self):
  d={"matches":[dict(DATA["matches"][0],score=[-1,1])]}
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode(),DSET)
 def test_no_silent_duplicate(self):
  d={"matches":[DATA["matches"][0],DATA["matches"][0]]}
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode(),DSET)
 def test_missing_result_no_final(self):
  d={"matches":[dict(DATA["matches"][0],score=None)]}
  b=make_bundle(json.dumps(d).encode(),DSET)
  self.assertEqual(b["records"][0]["match_status"],"SCHEDULE_UNKNOWN")
 def test_timezone_must_be_utc(self):
  with self.assertRaises(Rejected):make_bundle(self.sample(),DSET,now="2026-10-18T14:00:00+03:00")
if __name__=="__main__":unittest.main()
