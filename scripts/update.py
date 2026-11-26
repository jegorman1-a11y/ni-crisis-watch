#!/usr/bin/env python3
"""Collect public, linked updates; never infer 'all clear' from an unreachable feed."""
import datetime as dt
import email.utils
import html
import json
import os
import pathlib
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / 'data' / 'live.json'
UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC)
FEEDS = [
    {'id':'met-ni', 'name':'Met Office · Northern Ireland warnings', 'url':'https://weather.metoffice.gov.uk/public/data/PWSCache/WarningsRSS/Region/ni', 'site':'https://weather.metoffice.gov.uk/warnings-and-advice/uk-warnings', 'kind':'warnings'},
    {'id':'ukhsa', 'name':'UK Health Security Agency announcements', 'url':'https://www.gov.uk/government/organisations/uk-health-security-agency.atom', 'site':'https://www.gov.uk/government/organisations/uk-health-security-agency', 'kind':'news'},
    {'id':'ni-health', 'name':'NI Department of Health announcements', 'url':'https://www.health-ni.gov.uk/news/feed', 'site':'https://www.health-ni.gov.uk/news', 'kind':'news'},
    {'id':'ni-education', 'name':'NI Department of Education announcements', 'url':'https://www.education-ni.gov.uk/news/feed', 'site':'https://www.education-ni.gov.uk/news', 'kind':'news'},
]
NS = {'a':'http://www.w3.org/2005/Atom', 'dc':'http://purl.org/dc/elements/1.1/'} 

def get_bytes(url):
    req=urllib.request.Request(url,headers={'User-Agent':'NICrisisWatch/1.0 (+public-information-dashboard)','Accept':'application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.5'})
    with urllib.request.urlopen(req,timeout=16) as r:
        data=r.read(1300000)
        return data

def clean(s):
    s=re.sub(r'<[^>]+>',' ', s or '')
    return re.sub(r'\s+',' ',html.unescape(s)).strip()[:300]

def item_date(s):
    if not s: return None
    try:
        d=dt.datetime.fromisoformat(s.strip().replace('Z','+00:00'))
    except ValueError:
        try: d=email.utils.parsedate_to_datetime(s)
        except (ValueError,TypeError): return None
    if d.tzinfo is None: d=d.replace(tzinfo=UTC)
    return d.astimezone(UTC).isoformat().replace('+00:00','Z')

def child_text(root,paths):
    for p in paths:
        t=root.findtext(p,namespaces=NS)
        if t: return t.strip()
    return ''

def parse_feed(content):
    root=ET.fromstring(content)
    items=[]
    is_atom=root.tag.endswith('feed')
    elems=root.findall('a:entry',NS) if is_atom else root.findall('.//item')
    for item in elems[:30]:
        if is_atom:
            link=next((x.attrib.get('href','') for x in item.findall('a:link',NS) if x.attrib.get('rel','alternate')=='alternate'), '')
            if not link: link=next((x.attrib.get('href','') for x in item.findall('a:link',NS)), '')
        else: link=child_text(item,['link'])
        title=clean(child_text(item,['a:title','title']))
        published=item_date(child_text(item,['a:updated','a:published','pubDate','dc:date']))
        desc=clean(child_text(item,['a:summary','a:content','description']))
        if not title or not link or not link.startswith('https://'): continue
        # Don't put future-dated items or older than 30 days in the live feed.
        if published:
            age=(NOW-dt.datetime.fromisoformat(published.replace('Z','+00:00'))).total_seconds()
            if age < -7200 or age > 30*86400: continue
        items.append({'title':title[:160],'summary':desc[:240],'published':published,'url':link})
    return items

def collect(previous):
    old={x['id']:x for x in previous.get('sources',[])}
    sources=[]
    all_items=[]
    for feed in FEEDS:
        source={k:feed[k] for k in ('id','name','site','kind')}
        source['checked_at']=NOW.isoformat().replace('+00:00','Z')
        try:
            records=parse_feed(get_bytes(feed['url']))
            source.update(status='ok',last_success=source['checked_at'],item_count=len(records))
            for record in records:
                record['source_id']=feed['id']; record['source']=feed['name'];record['category']=feed['kind'];all_items.append(record)
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError, OSError) as exc:
            # Retain the previous success time but mark data unavailable; never claim zero alerts.
            source.update(status='unavailable',last_success=old.get(feed['id'],{}).get('last_success'),item_count=None,problem=type(exc).__name__)
        sources.append(source)
    all_items.sort(key=lambda i:i.get('published') or '',reverse=True)
    # Duplicate removal based on source URL; do not treat items as verified real-world events.
    seen=set();unique=[]
    for item in all_items:
        if item['url'] not in seen: unique.append(item);seen.add(item['url'])
    return {'schema':1,'generated_at':NOW.isoformat().replace('+00:00','Z'),'mode':'automatic source headlines, not independently verified emergency alerts','sources':sources,'items':unique[:35], 'data_note':'Publication dates are provided by source feeds. A successful fetch does not confirm absence of threats. Check original notices and local coverage.'}

def main():
    previous={}
    if OUT.exists():
        try: previous=json.loads(OUT.read_text())
        except (ValueError,OSError): pass
    updated=collect(previous)
    OUT.parent.mkdir(exist_ok=True,parents=True)
    rendered=json.dumps(updated,indent=2,ensure_ascii=False)+'\n'
    OUT.write_text(rendered)
    print('Sources:',[(s['id'],s['status'],s['item_count']) for s in updated['sources']]);print('Items:',len(updated['items']))

if __name__=='__main__': main()
