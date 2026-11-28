"""Refresh weekly respiratory hospital figures from PHA and HPSC."""
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import os
import re
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from extended import ROOT, TextParser, get, read_saved_data

OUT = ROOT / 'data' / 'respiratory-admissions.json'
PHA = 'https://www.publichealth.hscni.net'
PHA_INDEX = PHA + '/protecting-our-health/health-surveillance-data/respiratory-infections-data/respiratory-surveillance'
HPSC_INDEX = 'https://www.hpsc.ie/a-z/acuterespiratoryinfection/surveillance/integratedreports'
NORTH = 'Northern Ireland'
IRELAND = 'Republic of Ireland'
NUMBER = r'(\d[\d,]*|one|zero)'
COUNTS = ('influenza', 'rsv', 'covid')


def html(url):
    return get(url, max_bytes=10_000_000).decode('utf-8')


def plain(source):
    parser = TextParser()
    parser.feed(source)
    return parser.text()


def links(source, base, host, pattern):
    found = {}
    for href in re.findall(r'(?:href|src)=["\']([^"\']+)["\']', source, re.I):
        url = urljoin(base, href)
        u = urlsplit(url)
        match = re.fullmatch(pattern, u.path, re.I)
        if u.scheme == 'https' and u.netloc == host and match:
            found[(int(match[2]), int(match[1])) if match.lastindex == 2 else int(match[1])] = url
    if not found:
        raise ValueError('Official report link missing')
    return found[max(found)]


def require(pattern, text):
    match = re.search(pattern, text, re.I)
    if not match:
        raise ValueError('Expected admissions wording missing')
    return match


def count(value):
    if value.lower() in {'zero', 'one'}:
        return int(value.lower() == 'one')
    return int(value.replace(',', ''))


def parse_ni(source, url):
    text = plain(source)
    heading = require(r'Week (\d{1,2}):\s*\d{1,2} [A-Za-z]+ \d{4}\s*[-–]\s*(\d{1,2} [A-Za-z]+ \d{4})', text)
    week = int(heading[1])
    end = dt.datetime.strptime(heading[2], '%d %B %Y').date()
    totals = require(r'There were ' + NUMBER + r' new community.acquired emergency hospital admissions during week (\d{1,2}), compared with ' + NUMBER + r' in week (\d{1,2})', text)
    breakdown = require(r'Of the admissions reported in week (\d{1,2}),\s*([^.]*)\.', text)
    if week != int(totals[2]) or week != int(breakdown[1]):
        raise ValueError('PHA periods disagree')
    parts = breakdown[2]
    influenza = sum(count(value) for value in re.findall(NUMBER + r'\s+(?:were\s+)?(?:influenza|flu)\b', parts, re.I))
    rsv = count(require(NUMBER + r'\s+(?:were\s+)?RSV\b', parts)[1])
    covid = count(require(NUMBER + r'\s+(?:were\s+)?COVID-19\b', parts)[1])
    if influenza + rsv + covid != count(totals[1]):
        raise ValueError('PHA breakdown does not match the reported total')
    previous_week = (end - dt.timedelta(days=7)).isocalendar().week
    return {'area': NORTH, 'period_end': end.isoformat(), 'influenza': influenza,
            'rsv': rsv, 'covid': covid, 'total': count(totals[1]),
            'previous': count(totals[3]) if previous_week == int(totals[4]) else None,
            'definition': 'Community-acquired emergency admissions', 'source': 'PHA bulletin', 'url': url}


def parse_ie(source, url):
    text = plain(source)
    heading = require(r'ISO Week (\d{1,2}) \d{4}\s*\(\d{2}/\d{2}/\d{4}\s*[-–]\s*(\d{2}/\d{2}/\d{4})\)', text)
    end = dt.datetime.strptime(heading[2], '%d/%m/%Y').date()
    week = int(heading[1])
    counts = {}
    for field, disease in zip(COUNTS, ('influenza', 'RSV', 'COVID-19')):
        hit = require(r'There (?:were|was) \d[\d,]* ' + disease + r' cases[^.]{0,220}?\band ' +
                      NUMBER + r' hospitalisations? notified in week (\d{1,2})\b', text)
        if int(hit[2]) != week:
            raise ValueError('HPSC reporting periods disagree')
        counts[field] = count(hit[1])
    return {'area': IRELAND, 'period_end': end.isoformat(), **counts,
            'definition': 'Hospitalisations notified that week', 'source': 'HPSC bulletin', 'url': url}


def northern_ireland():
    url = links(html(PHA_INDEX), PHA_INDEX, 'www.publichealth.hscni.net',
                r'/sites/default/files/reports/\d{4}-\d{2}/Respiratory-Surveillance-Report[-_]w?(\d{1,2})_(\d{4})\.html')
    return parse_ni(html(url), url)


def ireland():
    url = links(html(HPSC_INDEX), HPSC_INDEX, 'file.hpsc.ie',
                r'/uploads/acuterespiratoryinfection/surveillancereports/(\d+)\.html')
    return parse_ie(html(url), url)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(ZoneInfo('Europe/London')).date().isoformat()
    previous = read_saved_data(OUT)
    if previous.get('checked_day') == today and os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        return
    saved = {row['area']: row for row in read_saved_data(ROOT / 'data' / 'public-health.json').get('admissions', [])}
    saved.update({row['area']: row for row in previous.get('rows', [])})
    rows = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [(area, pool.submit(provider)) for area, provider in ((NORTH, northern_ireland), (IRELAND, ireland))]
        for area, task in tasks:
            try:
                row = task.result()
                if not saved.get(area, {}).get('period_end', '') <= row['period_end'] <= today:
                    raise ValueError('Older or future reporting period')
                rows.append({**row, 'status': 'ok'})
            except (OSError, ValueError) as exc:
                print(f'Respiratory admissions, {area}: {exc}')
                if area in saved:
                    rows.append({**saved[area], 'status': 'saved'})
    OUT.write_text(json.dumps({'checked_at': now.isoformat(), 'checked_day': today, 'rows': rows},
                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
