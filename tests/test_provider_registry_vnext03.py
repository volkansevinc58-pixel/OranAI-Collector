import json,copy,unittest
from provider_contract import validate,load,RegistryRejected
from pathlib import Path
class RegistryTests(unittest.TestCase):
 def setUp(self):self.d=load(Path(__file__).resolve().parents[1]/'provider_registry_vnext03.json')
 def bad(self,change):
  d=copy.deepcopy(self.d);change(d)
  with self.assertRaises(RegistryRejected):validate(d)
 def test_17_sources(self):self.assertEqual(validate(self.d)['providers'],17)
 def test_2_stage_only(self):self.assertEqual(validate(self.d)['staging_enabled'],2)
 def test_final_locked(self):self.assertEqual(validate(self.d)['production_enabled'],0)
 def test_block_html_scrape(self):self.bad(lambda d:d['providers'][9].update(staging_fetch_enabled=True))
 def test_block_paid_auto(self):self.bad(lambda d:d['providers'][14].update(staging_fetch_enabled=True))
 def test_block_final(self):self.bad(lambda d:d['providers'][0].update(betting_final_enabled=True))
 def test_block_production(self):self.bad(lambda d:d['providers'][0].update(production_ingest_enabled=True))
 def test_block_duplicates(self):self.bad(lambda d:d['providers'][1].update(id='openfootball'))
 def test_block_unlisted(self):self.bad(lambda d:d['providers'][1].update(id='fake'))
 def test_block_missing(self):self.bad(lambda d:d['providers'].pop())
 def test_no_unlimited_claim(self):self.bad(lambda d:d.update(no_unlimited_free_claim=False))
 def test_block_new_final_flag(self):self.bad(lambda d:d.update(production_final_enabled=True))
 def test_api_status_only(self):self.assertEqual(self.d['providers'][4]['execution_policy'],'STATUS_PROBE_ONLY')
 def test_legacy_ro(self):self.assertEqual(self.d['providers'][-1]['stage'],'LEGACY_RO_ONLY')
 def test_mackolik_not_auto(self):self.assertFalse(self.d['providers'][9]['staging_fetch_enabled'])
 def test_rights_field(self):self.assertTrue(all(x['evidence'] for x in self.d['providers']))
 def test_no_secrets(self):self.assertTrue(all(x['credentials_in_registry'] is False for x in self.d['providers']))
if __name__=='__main__':unittest.main()
