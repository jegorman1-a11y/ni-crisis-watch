import datetime as dt
import unittest

from scripts.extended import TextParser
from scripts.security_watch import MI5, collect_security, parse_levels, parse_local_notices


MI5_PAGE = b"""
<h3>Current national threat level</h3>
<p>The threat to the UK (England, Wales, Scotland and Northern Ireland) from
all forms of terrorism is <strong>SEVERE</strong>.</p>
<h3>Current Northern Ireland-related Terrorism in Northern Ireland threat level</h3>
<p>The threat to Northern Ireland from Northern Ireland-related terrorism is
<strong>SUBSTANTIAL</strong>.</p>
<h3>National Threat Level</h3>
<table><tr><th>Date</th><th>Threat Level</th></tr>
<tr><td>30 April 2026</td><td>SEVERE</td></tr></table>
<h3>Northern Irish Related Terrorism in Northern Ireland Threat Level</h3>
<table><tr><th>Date</th><th>Threat Level</th></tr>
<tr><td>6 March 2024</td><td>SUBSTANTIAL</td></tr></table>
"""
PSNI_PAGE = b"""
<a href="/latest-news/nearby"><h3>Appeal for information in Co Down</h3></a>
<a href="/latest-news/nonlocal">Public safety notice in Fermanagh</a>
<a href="/latest-news/general">Recruitment starts in Bangor</a>
<a href="https://example.org/latest-news/fake">Security alert in Newcastle</a>
"""


class SecurityWatchTests(unittest.TestCase):
    def test_official_levels_and_dates(self):
        parser = TextParser()
        parser.feed(MI5_PAGE.decode())
        levels = parse_levels(parser.text())
        self.assertEqual(levels['uk'], {'level': 'SEVERE', 'changed_on': '2026-04-30'})
        self.assertEqual(levels['ni'], {'level': 'SUBSTANTIAL', 'changed_on': '2024-03-06'})

    def test_mismatched_history_date_is_omitted(self):
        parser = TextParser()
        parser.feed(MI5_PAGE.replace(b'<strong>SEVERE</strong>', b'<strong>CRITICAL</strong>').decode())
        self.assertEqual(parse_levels(parser.text())['uk'], {'level': 'CRITICAL', 'changed_on': None})

    def test_psni_filters_for_local_notices_and_official_links(self):
        notices = parse_local_notices(PSNI_PAGE.decode())
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['url'], 'https://www.psni.police.uk/latest-news/nearby')

    def test_failed_mi5_check_keeps_previous_verification_date(self):
        now = dt.datetime(2026, 11, 28, tzinfo=dt.timezone.utc)
        first = collect_security(lambda url: MI5_PAGE if url == MI5 else PSNI_PAGE, TextParser, {}, now)
        second = collect_security(lambda url: b'<title>Error</title>', TextParser, first, now + dt.timedelta(hours=2))
        self.assertEqual(second['threat']['status'], 'unavailable')
        self.assertEqual(second['threat']['verified_at'], first['threat']['verified_at'])
        self.assertEqual(second['threat']['levels'], first['threat']['levels'])
        self.assertEqual(second['police']['status'], 'unavailable')
