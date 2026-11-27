import importlib.util
import pathlib
import unittest

P=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'extended.py'
spec=importlib.util.spec_from_file_location('extended',P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ExtendedTests(unittest.TestCase):
 def test_price_strict(self):
  oil='Average home heating oil price in Northern Ireland on 26 November 2026 300 litres average £296.62 500 litres average £485.36 900 litres average £861.68'
  pump='Petrol Average price 146.7p 26 November 2026 Diesel Average price 179.0p 26 November 2026'
  p=m.extract_prices(oil,pump)
  self.assertEqual(p['oil']['value'],861.68)
  self.assertEqual(p['petrol']['value'],146.7)
  self.assertEqual(p['diesel']['value'],179.0)
 def test_mislabelled_price_absent(self):
  p=m.extract_prices('900 litres £861.68', 'Diesel average price free today')
  self.assertEqual(p['status'],'unavailable')
 def test_rss_future_excluded(self):
  xml=b'<rss><channel><item><title>Tomorrow news</title><link>https://example.org/x</link><pubDate>Fri, 25 Dec 2026 12:00:00 GMT</pubDate></item></channel></rss>'
  self.assertEqual(m.parse_rss(xml,'test'),[])
 def test_weather_labels(self):
  self.assertFalse(m.is_recent(None))
if __name__=='__main__':unittest.main()
