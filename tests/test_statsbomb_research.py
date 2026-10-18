import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from statsbomb_research_adapter import make_bundle,verify,fetch,Rejected,DATASET
def sample():
 return json.dumps([{"match_id":3773386,"match_date":"2020-10-31",
    "home_team":{"home_team_name":"Deportivo Alavés"},
    "away_team":{"away_team_name":"Barcelona"},"home_score":1,"away_score":1,
    "competition":{"competition_id":11},"season":{"season_id":90}}]).encode()
class Tests(unittest.TestCase):
 def test_valid(self):
  d=make_bundle(sample(),stamp="2026-10-18T12:00:00+00:00")
  self.assertEqual(verify(d)["records"],1)
  self.assertFalse(d["production_import_eligible"])
  self.assertIsNone(d["records"][0]["kickoff_utc"])
 def test_approval(self):
  with self.assertRaises(Rejected):fetch()
 def test_signature(self):
  d=make_bundle(sample());d["records"][0]["score_reported"]=[10,0]
  with self.assertRaises(Rejected):verify(d)
 def test_duplicate(self):
  d=json.loads(sample());d.append(d[0])
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode())
 def test_bad_competition(self):
  d=json.loads(sample());d[0]["competition"]["competition_id"]=9
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode())
 def test_bad_score(self):
  d=json.loads(sample());d[0]["home_score"]=-1
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode())
 def test_bad_team(self):
  d=json.loads(sample());d[0]["home_team"]["home_team_name"]=""
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode())
 def test_non_utc_stamp(self):
  with self.assertRaises(Rejected):make_bundle(sample(),stamp="2026-10-18T15:00:00+03:00")
 def test_no_prematch_promotion(self):
  d=make_bundle(sample());d["production_import_eligible"]=True
  with self.assertRaises(Rejected):verify(d)
 def test_wrong_id(self):
  d=json.loads(sample());d[0]["match_id"]=True
  with self.assertRaises(Rejected):make_bundle(json.dumps(d).encode())
if __name__=="__main__":unittest.main()
