import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import gatwick

class GatwickTests(unittest.TestCase):
    def test_unavailable_never_implies_no_delays(self):
        with patch('gatwick.urllib.request.urlopen', side_effect=OSError('offline')):
            result = gatwick.collect()
        self.assertEqual(result['status'], 'unavailable')
        self.assertIsNone(result['delay_count'])
        self.assertIsNone(result['cancellation_count'])
        self.assertIsNone(result['metar'])
        self.assertTrue(result['official_flights_url'].startswith('https://www.gatwickairport.com/'))

if __name__ == '__main__': unittest.main()
