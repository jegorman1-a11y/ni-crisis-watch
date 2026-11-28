"""Collect published public security information from official sources."""
import datetime as dt
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit

MI5 = 'https://www.mi5.gov.uk/threats-and-advice/terrorism-threat-levels'
PSNI = 'https://www.psni.police.uk/latest-news'
LEVEL = r'(LOW|MODERATE|SUBSTANTIAL|SEVERE|CRITICAL)'
CURRENT = {
    'uk': r'Current national threat level\s+The threat to the UK\b[^.]{0,250}?\bis\s+',
    'ni': r'Current Northern Ireland.related Terrorism in Northern Ireland threat level\s+The threat to Northern Ireland\b[^.]{0,250}?\bis\s+',
}
HISTORY = {
    'uk': r'National Threat Level\s+Date\s+Threat Level',
    'ni': r'Northern Irish Related Terrorism in Northern Ireland Threat Level\s+Date\s+Threat Level',
}
LOCAL = re.compile(
    r'\b(?:county down|co\.? down|downpatrick|seaforde|newcastle|ballynahinch|'
    r'castlewellan|kilkeel|banbridge|newry|bangor|newtownards|donaghadee|comber)\b',
    re.I,
)
NOTICE = re.compile(
    r'\b(?:public safety|security alert|security incident|evacuation|police cordon|'
    r'public appeal|appeal for information|warning)\b', re.I,
)


def parse_levels(text):
    levels = {}
    for region, pattern in CURRENT.items():
        current = re.search(pattern + LEVEL + r'\b', text, re.I)
        if not current:
            raise ValueError(f'MI5 current level missing for {region}')
        level = current[1].upper()
        change = re.search(HISTORY[region] + r'\s+(\d{1,2} [A-Za-z]+ \d{4})\s+' + LEVEL + r'\b', text, re.I)
        changed_on = None
        if change and change[2].upper() == level:
            changed_on = dt.datetime.strptime(change[1], '%d %B %Y').date().isoformat()
        levels[region] = {'level': level, 'changed_on': changed_on}
    return levels


class PoliceLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None
        self.parts = []
        self.listing = {}

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        self.parts = []
        href = urlsplit(urljoin(PSNI, dict(attrs).get('href') or ''))
        valid = href.scheme == 'https' and href.netloc == 'www.psni.police.uk'
        self.href = href._replace(query='', fragment='').geturl() if valid and href.path.startswith('/latest-news/') and href.path.rstrip('/') != '/latest-news' else None

    def handle_data(self, data):
        if self.href:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != 'a' or not self.href:
            return
        title = ' '.join(''.join(self.parts).split())
        if title:
            self.listing[self.href] = title
        self.href = None


def parse_local_notices(content):
    parser = PoliceLinks()
    parser.feed(content)
    if not parser.listing:
        raise ValueError('No PSNI article links found')
    return [
        {'title': title, 'url': url}
        for url, title in parser.listing.items()
        if LOCAL.search(title) and NOTICE.search(title)
    ][:3]


def collect_security(get, parser_type, previous, now):
    checked = now.isoformat()
    try:
        parser = parser_type()
        parser.feed(get(MI5).decode('utf-8'))
        threat = {'status': 'ok', 'checked_at': checked, 'verified_at': checked,
                  'levels': parse_levels(parser.text())}
    except (OSError, ValueError) as exc:
        print(f'MI5 threat check: {type(exc).__name__}: {exc}')
        saved = previous.get('threat') or {}
        threat = {'status': 'unavailable', 'checked_at': checked,
                  'verified_at': saved.get('verified_at'), 'levels': saved.get('levels')}
    try:
        police = {'status': 'ok', 'checked_at': checked,
                  'items': parse_local_notices(get(PSNI).decode('utf-8'))}
    except (OSError, ValueError) as exc:
        print(f'PSNI public notices: {type(exc).__name__}: {exc}')
        police = {'status': 'unavailable', 'checked_at': checked, 'items': []}
    return {'threat': threat, 'police': police}
