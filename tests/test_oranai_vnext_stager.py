import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from oranai_vnext_stager import collect,verify,filename,ALLOW,Rejected
def src(ds):
    return json.dumps({"matches":[
        {"round":"Matchday 1","date":"2025-08-15","team1":"Liverpool FC","team2":"Bournemouth FC","score":{"ft":[4,2]}},
        {"round":"Matchday 1","date":"2025-08-16","team1":"Aston Villa FC","team2":"Newcastle United FC","score":[0,0]}]}).encode()
class Contract(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/"stage"
    def runstage(self,fetch=src):return collect(approved=True,root=self.p,fetcher=fetch,stamp="2026-10-18T12:00:00+00:00")
    def test_approval(self):
        with self.assertRaises(Rejected):collect(root=self.p,fetcher=src)
    def test_two_sources(self):
        r=self.runstage();self.assertEqual((r["sources"],r["records"]),(2,4));self.assertEqual(verify(self.p),r)
        b=json.loads((self.p/filename(ALLOW[0])).read_text())
        self.assertEqual([x["score_ft"] for x in b["records"]],[[4,2],[0,0]])
    def test_tamper_manifest(self):
        self.runstage();p=self.p/"manifest.json";b=json.loads(p.read_text());b["rows"]=999;p.write_text(json.dumps(b))
        with self.assertRaises(Rejected):verify(self.p)
    def test_tamper_data(self):
        self.runstage();p=self.p/filename(ALLOW[0]);b=json.loads(p.read_text());b["records"][0]["score_ft"]=[15,0];p.write_text(json.dumps(b))
        with self.assertRaises(Rejected):verify(self.p)
    def test_fail_closed_partial(self):
        def bad(d):return src(d) if d==ALLOW[0] else b"invalid"
        with self.assertRaises(Rejected):self.runstage(fetch=bad)
        self.assertFalse((self.p/"manifest.json").exists())
    def test_no_implicit_overwrite(self):
        self.runstage()
        with self.assertRaises(Rejected):self.runstage()
    def test_reject_duplicate(self):
        def bad(d):
            v=json.loads(src(d));v["matches"].append(v["matches"][0]);return json.dumps(v).encode()
        with self.assertRaises(Rejected):self.runstage(fetch=bad)
    def test_no_fake_final(self):
        r=self.runstage();self.assertFalse(r["final_enabled"]);self.assertEqual(r["sqlite_writes"],0)
if __name__=="__main__":unittest.main()
