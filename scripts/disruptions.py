"""Collect official TrafficWatchNI notices for the operations overview."""
import hashlib
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit

TRAFFIC_URL = 'https://www.trafficwatchni.com/twni/'
FEEDS = {
    'incidents': 'https://rss.trafficwatchni.com/trafficwatchni_incidents_rss.xml',
    'roadworks': 'https://rss.trafficwatchni.com/trafficwatchni_roadworks_rss.xml',
}


def parse_traffic(content, kind, clean):
    root = ET.fromstring(content)
    channel = root.find('channel')
    if root.tag != 'rss' or channel is None or not channel.findtext('title'):
        raise ValueError('Unexpected TrafficWatchNI feed')
    notices = {}
    for item in channel.findall('item'):
        title = clean(item.findtext('title') or '')
        if not title:
            raise ValueError('TrafficWatchNI notice has no title')
        summary = clean(item.findtext('description') or '')
        raw_link = (item.findtext('link') or '').strip()
        link = urljoin(TRAFFIC_URL, raw_link)
        if urlsplit(link).hostname not in {'www.trafficwatchni.com', 'trafficwatchni.com'} or not link.startswith('https://'):
            link = TRAFFIC_URL
        guid = (item.findtext('guid') or '').strip()
        identity = hashlib.sha256((guid or title.casefold()).encode()).hexdigest()[:24]
        notices[identity] = {
            'id': kind + ':' + identity, 'title': title, 'summary': summary, 'url': link,
        }
    return list(notices.values())


def collect_traffic(get, clean):
    sources = {}
    for kind, url in FEEDS.items():
        try:
            sources[kind] = {'status': 'ok', 'items': parse_traffic(get(url), kind, clean)}
        except (OSError, ValueError, ET.ParseError) as exc:
            print(f'TrafficWatchNI {kind}: {type(exc).__name__}: {exc}')
            sources[kind] = {'status': 'unavailable', 'items': []}
    return sources
