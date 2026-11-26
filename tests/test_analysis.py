import unittest
import datetime as dt
from scripts.analyse import assess, classify, BASELINE
NOW=dt.datetime(2026,11,26,12,tzinfo=dt.timezone.utc)
class TestAnalysis(unittest.TestCase):
 def test_preparedness_is_not_implementation(self):
  feed={'sources':[{'id':'a','status':'ok'}], 'items':[{'source_id':'a','title':'Pandemic lockdown preparedness exercise planned','summary':'','published':'2026-11-26T11:00:00Z','url':'https://example.com'}]}
  self.assertEqual(classify(feed,NOW),[])
 def test_single_feed_does_not_change_forecast(self):
  feed={'sources':[{'id':'a','status':'ok'}],'items':[{'source_id':'a','title':'Major power outage reported across the region','summary':'','published':'2026-11-26T11:00:00Z','url':'https://example.com'}]}
  result=assess(feed,{},NOW)
  self.assertEqual(result['forecast'][2]['year'],BASELINE['infrastructure'][0])
 def test_stale_report_not_escalation(self):
  feed={'sources':[{'id':'a','status':'ok'}],'items':[{'source_id':'a','title':'Major power outage reported across the region','summary':'','published':'2026-10-01T11:00:00Z','url':'https://example.com'}]}
  self.assertEqual(classify(feed,NOW),[])
 def test_failed_source_not_all_clear(self):
  feed={'generated_at':'2026-11-26T11:00:00Z','sources':[{'id':'a','status':'unavailable'}],'items':[]}
  result=assess(feed,{},NOW)
  self.assertTrue(result['warnings'])
if __name__=='__main__':unittest.main()
