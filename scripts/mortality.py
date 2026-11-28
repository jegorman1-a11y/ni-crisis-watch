"""Refresh all-cause death registrations from official publications."""
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import os
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from extended import ROOT, TextParser, get, read_saved_data

OUT = ROOT / 'data' / 'mortality.json'
SEED = ROOT / 'data' / 'public-health.json'
NISRA = 'https://www.nisra.gov.uk'
ONS = 'https://www.ons.gov.uk/visualisations/weeklydeathsdashboard/'
NRS = 'https://www.nrscotland.gov.uk/publications/deaths-registered-weekly-in-scotland/'
CSO = 'https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/VSQ01/JSON-stat/2.0/en'
AREAS = ('Northern Ireland', 'United Kingdom', 'England and Wales', 'Scotland', 'Republic of Ireland')
DAY = r'\d{1,2} [A-Za-z]+ \d{4}'
NUMBER = r'\d[\d,]*'
MONTHS = ('January–March', 'April–June', 'July–September', 'October–December')


def match(pattern, text):
    found = re.search(pattern, text, re.I)
    if not found:
        raise ValueError('Expected source wording missing: ' + pattern)
    return found


def page(url):
    parser = TextParser()
    parser.feed(get(url).decode('utf-8'))
    return parser.text()


def number(value):
    return int(value.replace(',', ''))


def ending(value):
    return dt.datetime.strptime(value, '%d %B %Y').date()


def reading(area, period_end, count, source, url, expected=None, period=None):
    return {'area': area, 'period_end': period_end.isoformat(),
            'period': period or f'Week ending {period_end.day} {period_end:%B %Y}',
            'registered': count, 'expected': expected, 'source': source, 'url': url}


def northern_ireland():
    listing = get(NISRA + '/news').decode('utf-8')
    paths = re.findall(r'href=["\'](/news/weekly-registered-deaths-[\w-]+)["\']', listing)
    candidates = []
    for path in paths:
        suffix = re.search(r'week-ending-(\d{1,2}-[a-z]+-\d{4})$', path)
        if suffix:
            candidates.append((ending(suffix[1].replace('-', ' ')), path))
    if not candidates:
        raise ValueError('NISRA weekly release link missing')
    date, path = max(candidates)
    url = urljoin(NISRA, path)
    text = page(url)
    week = match(r'weekly registered deaths:\s*(' + NUMBER + r')\s+for week ending (' + DAY + ')', text)
    total = match(r'total deaths registered in Northern Ireland in the week ending .*? was (' + NUMBER + ')', text)
    expected = match(r'number of expected deaths for week \d+ was estimated at (' + NUMBER + ')', text)
    if ending(week[2]) != date or number(week[1]) != number(total[1]):
        raise ValueError('NISRA headline and registration totals disagree')
    return [reading(AREAS[0], date, number(total[1]), 'NISRA', url, number(expected[1]))]


def ons():
    text = page(ONS)
    headline = match(r'Deaths registered and expected deaths England and Wales, week ending \w+ (' + DAY +
                     r') \(Week \d+ of \d{4}\) Deaths registered (' + NUMBER + ')', text)
    date = ending(headline[1])
    count = number(headline[2])
    comparison = re.search(r'Comparison with expected deaths.{0,150}?\b(' + NUMBER +
                           r') (fewer|more) than expected', text[headline.end():headline.end()+300], re.I)
    expected = None
    if comparison:
        difference = number(comparison[1])
        expected = count + difference if comparison[2].lower() == 'fewer' else count - difference
    uk = match(r'Deaths by country Week ending \w+ (' + DAY + r').{0,700}?\bUK Deaths registered (' + NUMBER + ')', text)
    if ending(uk[1]) != date:
        raise ValueError('ONS totals refer to different weeks')
    return [reading(AREAS[1], date, number(uk[2]), 'ONS UK total', ONS),
            reading(AREAS[2], date, count, 'ONS', ONS, expected)]


def scotland():
    text = page(NRS)
    total = match(r'total number of deaths registered in Scotland in week \d+ of (\d{4})\s*'
                  r'\([^)]*? to (\d{1,2} [A-Za-z]+)\) was (' + NUMBER + ')', text)
    date = ending(total[2] + ' ' + total[1])
    count = number(total[3])
    comparison = re.search(r'This is (' + NUMBER + r'), or [\d.]+%, (higher|lower) than (?:the )?expected',
                           text[total.end():total.end()+160], re.I)
    expected = None
    if comparison:
        difference = number(comparison[1])
        expected = count - difference if comparison[2].lower() == 'higher' else count + difference
    return [reading(AREAS[3], date, count, 'National Records of Scotland', NRS, expected)]


def ireland():
    cube = json.loads(get(CSO))
    ids, sizes = cube['id'], cube['size']
    if len(ids) != 3 or len(sizes) != 3:
        raise ValueError('Unexpected CSO dataset dimensions')
    selections, quarters = {}, {}
    for dimension in ids:
        category = cube['dimension'][dimension]['category']
        index = category['index']
        labels = category['label']
        for key, label in labels.items():
            if label.strip().casefold() in {'deaths', 'deaths registered', 'both sexes'}:
                selections[dimension] = index[key]
            quarter = re.fullmatch(r'(\d{4})\s*[- ]?Q([1-4])', key, re.I)
            if quarter:
                quarters[(int(quarter[1]), int(quarter[2]))] = (dimension, index[key])
    for (year, quarter), (dimension, position) in sorted(quarters.items(), reverse=True):
        indices = {**selections, dimension: position}
        offset = 0
        for key, size in zip(ids, sizes):
            offset = offset * size + indices[key]
        values = cube['value']
        count = values.get(str(offset)) if isinstance(values, dict) else values[offset]
        if type(count) is int and count > 0:
            # date() avoids locale-specific parsing of the API's quarter codes.
            end = dt.date(year, 12, 31) if quarter == 4 else dt.date(year, quarter*3+1, 1) - dt.timedelta(days=1)
            return [reading(AREAS[4], end, count, 'Central Statistics Office', 'https://data.cso.ie/table/VSQ01',
                            period=f'Quarterly · {MONTHS[quarter-1]} {year}')]
    raise ValueError('No valid CSO registration quarter')


def collect(previous, seed, today):
    saved = {item['area']: item for item in seed}
    saved.update({item['area']: item for item in previous})
    results = {}
    providers = {northern_ireland: AREAS[:1], ons: AREAS[1:3], scotland: AREAS[3:4], ireland: AREAS[4:]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {pool.submit(fn): areas for fn, areas in providers.items()}
        for task, areas in tasks.items():
            try:
                rows = task.result()
                for row in rows:
                    area = row['area']
                    if (row['period_end'] > today or row['period_end'] < saved.get(area, {}).get('period_end', '')
                            or row['registered'] <= 0 or (row['expected'] is not None and row['expected'] <= 0)):
                        raise ValueError(f'Invalid or older period from {area}')
                for row in rows:
                    results[row['area']] = {**row, 'status': 'ok'}
            except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                print(f'Mortality check for {", ".join(areas)}: {exc}')
                for area in areas:
                    if area in saved:
                        results[area] = {**saved[area], 'status': 'saved'}
    return [results[area] for area in AREAS if area in results]


def main():
    now = dt.datetime.now(dt.timezone.utc)
    today = now.astimezone(ZoneInfo('Europe/London')).date().isoformat()
    previous = read_saved_data(OUT)
    if previous.get('checked_day') == today and os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        return
    seed = read_saved_data(SEED).get('mortality', [])
    rows = collect(previous.get('rows', []), seed, today)
    OUT.write_text(json.dumps({'checked_at': now.isoformat(), 'checked_day': today, 'rows': rows},
                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
