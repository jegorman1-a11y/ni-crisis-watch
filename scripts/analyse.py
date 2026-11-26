#!/usr/bin/env python3
"""Conservative, reproducible public-feed triage and history. Not an LLM or an emergency alert service."""
import datetime as dt
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
ARCHIVE = DATA / 'archive'
UTC = dt.timezone.utc
BASELINE = {'lockdown': (3, 10), 'restrictions': (9, 27), 'infrastructure': (27, 67)}
LABELS = {'lockdown':'Nationwide stay-at-home orders','restrictions':'Narrower public-health restrictions', 'infrastructure':'Serious local infrastructure disruption'}
# Detection rules are intentionally narrow. These identify candidate developments, not verified facts.
RULES = [
 ('restrictions','public-health directive',r'\b(?:mandatory|ordered|imposed|enacted|introduced|takes effect)\b.{0,100}\b(?:isolation|quarantine|restrictions|school closures)\b', 2),
 ('lockdown','stay-at-home restriction',r'\b(?:imposed|ordered|enacted|introduced|announced)\b.{0,70}\b(?:stay.at.home|lockdown|movement restriction)\b', 4),
 ('infrastructure','critical service outage',r'\b(?:major|widespread|national|regional)\b.{0,75}\b(?:power outage|water outage|supply interruption|electricity failure)\b', 2),
 ('infrastructure','emergency warning',r'\b(?:red weather warning|severe weather warning|major incident declared|critical infrastructure attack)\b', 1),
]

def load(path, default):
 try: return json.loads(path.read_text(encoding='utf-8'))
 except (OSError, ValueError): return default

def iso_now(): return dt.datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00','Z')

def parse_date(s):
 try: return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
 except (ValueError,AttributeError): return None

def eligible(item, now):
 published=parse_date(item.get('published'))
 return bool(published and -dt.timedelta(hours=2) <= now-published <= dt.timedelta(days=3))

def classify(live, now=None):
 now=now or dt.datetime.now(UTC)
 ok={s['id']:s for s in live.get('sources',[]) if s.get('status')=='ok'}
 signals=[]
 for item in live.get('items',[]):
  if item.get('source_id') not in ok or not eligible(item,now): continue
  title=item.get('title',''); summary=item.get('summary','')
  # headline alone must contain a meaningful event predicate, not a speculative article.
  if re.search(r'\b(?:exercise|simulation|preparedness|consultation|scenario|could|may|plan to|training)\b',title,re.I): continue
  for risk,label,pattern,weight in RULES:
   if re.search(pattern,title,re.I):
    signals.append({'risk':risk,'label':label,'weight':weight,'title':title[:170], 'source':item.get('source',''), 'source_id':item.get('source_id',''), 'url':item.get('url',''), 'published':item.get('published'), 'evidence_level':'candidate — requires original-source verification'})
    break
 return signals

def assess(live, previous, now=None):
 now=now or dt.datetime.now(UTC)
 signals=classify(live,now)
 available={s.get('id') for s in live.get('sources',[]) if s.get('status')=='ok'}
 by_risk={key:[] for key in BASELINE}
 for s in signals: by_risk[s['risk']].append(s)
 forecasts=[]
 for key,(p12,p5) in BASELINE.items():
  evidence=by_risk[key]
  # Automatic probability adjustments require two independent, relevant, primary feeds
  # describing a matching actual event. The present set of feeds may rarely meet this.
  independent={e['source_id'] for e in evidence}
  corroborated=len(independent)>=2 and sum(e['weight'] for e in evidence)>=4
  bump=(1 if key!='lockdown' else 0) if corroborated else 0
  rationale=('Provisional +1pp 12-month / +2pp five-year adjustment from two independent official feed signals. '
             'This is a heuristic, not a calibrated probability or independently verified incident.' if bump else
             'Baseline retained: no qualifying corroborated, explicit activation evidence in retrieved feeds. A missing feed is not an all-clear.')
  forecasts.append({'id':key,'name':LABELS[key], 'year':min(100,p12+bump),'five':min(100,p5+2*bump),
                    'previous_year':next((f['year'] for f in previous.get('forecast',[]) if f.get('id')==key),p12),
                    'previous_five':next((f['five'] for f in previous.get('forecast',[]) if f.get('id')==key),p5),
                    'rationale':rationale,'method':'bounded rules-based planning heuristic',
                    'evidence':evidence[:5], 'review_required':bool(bump)})
 fingerprint=hashlib.sha256(json.dumps([{'url':s['url'],'risk':s['risk']} for s in signals],sort_keys=True).encode()).hexdigest()[:16]
 warnings=[]
 if len(available)<len(live.get('sources',[])):
  warnings.append('Some sources are unavailable; conclusions are limited to retrieved material.')
 if not signals: warnings.append('No qualifying candidate escalation detected in the connected headline feeds; this is not confirmation of no risk.')
 return {'schema':2,'generated_at':iso_now(),'source_generated_at':live.get('generated_at'),
  'mode':'automated conservative headline triage, not a verified intelligence judgement',
  'coverage':'Connected public announcement feeds only; NOT comprehensive WHO, legislation, procurement, NCSC or utilities monitoring.',
  'methodology':'Rule-based narrow headline predicates; corroboration from independent official feeds required for limited numerical changes. No automated LLM inference. Numbers are illustrative and uncalibrated.',
  'signals':signals[:20], 'signal_fingerprint':fingerprint, 'source_count':len(live.get('sources',[])), 'sources_available':len(available),
  'forecast':forecasts,'warnings':warnings}

def write_json(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 live=load(DATA/'live.json',{})
 if not live.get('generated_at'): raise SystemExit('No collected live data: run scripts/update.py first')
 previous=load(DATA/'assessment.json',{})
 assessment=assess(live,previous)
 write_json(DATA/'assessment.json',assessment)
 today=dt.datetime.now(UTC).date().isoformat()
 reportlist=load(DATA/'reports.json',{'schema':1,'reports':[]})
 old=reportlist.get('reports',[])
 weekday=dt.datetime.now(UTC).weekday()
 material=bool(assessment['signals']) and assessment['signal_fingerprint'] != previous.get('signal_fingerprint')
 # Each Monday publishes the weekly record once. Other days publish only new candidate escalations.
 existing_today=any(r.get('date')==today and r.get('type')=='weekly' for r in old)
 type_='weekly' if weekday==0 and not existing_today else 'alert' if material else None
 if type_:
  rid=f'{today}-{type_}-{assessment["signal_fingerprint"][:7]}'
  if not any(x['id']==rid for x in old):
   report={'id':rid,'date':today,'type':type_,'generated_at':assessment['generated_at'],
       'title':('Weekly risk summary' if type_=='weekly' else 'Potential new escalation — review required'),
       'assessment':assessment,'sources':live.get('sources',[]),
       'disclaimer':'Machine-generated from selected feeds. Signals are unverified candidates. Consult original official sources.'}
   path=ARCHIVE/f'{rid}.json';write_json(path,report)
   old.insert(0,{'id':rid,'date':today,'type':type_,'title':report['title'], 'path':f'data/archive/{rid}.json','signal_count':len(assessment['signals'])})
   write_json(DATA/'reports.json',{'schema':1,'reports':old[:365]})
   print('Published archive:',rid)
 else:
  if not (DATA/'reports.json').exists():write_json(DATA/'reports.json',{'schema':1,'reports':[]})
 print('Signals:',len(assessment['signals']),'Available sources:',assessment['sources_available'],'Forecast:',[(x['id'],x['year'],x['five']) for x in assessment['forecast']])

if __name__=='__main__':main()
