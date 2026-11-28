#!/usr/bin/env python3
"""Source-first dashboard enrichment. No prices/headlines are invented on failure."""
import datetime as dt
import email.utils
import html
from html.parser import HTMLParser
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'extended.json'
NOW=dt.datetime.now(dt.timezone.utc)
HEAD={'User-Agent':'NI-Crisis-Watch/2.0 (personal public-data dashboard)','Accept':'application/json, text/html, application/xml, text/xml, */*'}

class TextParser(HTMLParser):
 def __init__(self): super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','noscript'):self.skip+=1
  elif tag in ('p','h1','h2','h3','h4','td','th','tr','div','li','span','br'):self.parts.append(' ')
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript'):self.skip=max(0,self.skip-1)
  elif tag in ('p','h1','h2','h3','h4','td','th','tr','div','li'):self.parts.append(' ')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
 def text(self):return re.sub(r'\s+',' ',html.unescape(' '.join(self.parts))).strip()

def get(url,max_bytes=2000000):
 req=urllib.request.Request(url,headers=HEAD)
 with urllib.request.urlopen(req,timeout=17) as res:
  return res.read(max_bytes)

def is_recent(when,days=8):
 return bool(when and -600 <= (NOW-when).total_seconds() <= days*86400)

def parse_rss(data,source):
 root=ET.fromstring(data)
 result=[]
 entries=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
 for e in entries:
  def field(names):
   for name in names:
    t=e.find(name)
    if t is not None and t.text:return t.text.strip()
   return ''
  title=field(['title','{http://www.w3.org/2005/Atom}title'])
  link=field(['link'])
  if not link:
   le=e.find('{http://www.w3.org/2005/Atom}link')
   if le is not None:link=le.get('href','')
  pub=field(['pubDate','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated'])
  when=None
  try:when=email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
  except (ValueError,TypeError,OverflowError):
   try:when=dt.datetime.fromisoformat(pub.replace('Z','+00:00')).astimezone(dt.timezone.utc)
   except (ValueError,TypeError):pass
  if title and link.startswith('https://') and is_recent(when):
   result.append({'title':html.unescape(re.sub('<[^>]*>','',title))[:170], 'url':link,'source':source,'published_at':when.isoformat()})
 return result

CRISIS_TOPIC = re.compile(
 r'\b(?:power cut|outage|water supply|burst main|flood(?:ing)?|storm|weather warning|'
 r'cyber[- ]?(?:attack|incident)|ransomware|public health|outbreak|pandemic|'
 r'hospital disruption|emergency services|state of emergency|government response|'
 r'emergency legislation|lockdown|evacuation|road closure|travel disruption|'
 r'rail strike|transport strike)\b', re.I)


def collect_news():
 feeds={
 'UK': [('BBC UK','https://feeds.bbci.co.uk/news/uk/rss.xml'),('BBC Politics','https://feeds.bbci.co.uk/news/politics/rss.xml')],
 'Northern Ireland':[('BBC Northern Ireland','https://feeds.bbci.co.uk/news/northern_ireland/rss.xml'),('BBC NI Politics','https://feeds.bbci.co.uk/news/northern_ireland/northern_ireland_politics/rss.xml')],
 'Republic of Ireland':[('RTÉ News','https://www.rte.ie/feeds/rss/?index=/news/'),('Google News / Ireland','https://news.google.com/rss/search?q='+urllib.parse.quote('Ireland politics when:3d site:rte.ie OR site:irishtimes.com')+'&hl=en-IE&gl=IE&ceid=IE:en')]
 }
 out={};priority={};health={}
 for region,items in feeds.items():
  stories=[];health[region]=[]
  for label,url in items:
   try:
    parsed=parse_rss(get(url),label)
    health[region].append({'source':label,'status':'ok','count':len(parsed)})
    stories+=parsed
   except Exception as exc:health[region].append({'source':label,'status':'unavailable','reason':str(exc)[:90]})
  seen=set();unique=[]
  for item in sorted(stories,key=lambda s:s['published_at'],reverse=True):
   key=re.sub(r'[^a-z0-9]+','',item['title'].lower())[:90]
   if key not in seen:seen.add(key);unique.append(item)
  out[region]=unique[:5]
  priority[region]=[item for item in unique if CRISIS_TOPIC.search(item['title'])][:5]
 return {'stories':out,'priority':priority,'sources':health,'note':'Five most recent eligible feed items, not an independently ranked top-five; politics stories included where available. Only dated stories from the last eight days.'}

def collect_weather():
 out={}
 for name,lat,lon in [('County Down',54.27,-5.83),('London',51.5072,-0.1276)]:
  args={'latitude':lat,'longitude':lon,'daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max','timezone':'Europe/London','forecast_days':16}
  url='https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(args)
  try:
   data=json.loads(get(url))
   d=data['daily'];days=[]
   for i,day in enumerate(d['time']):
    days.append({'date':day,'max_c':d['temperature_2m_max'][i],'min_c':d['temperature_2m_min'][i],'rain_pct':d['precipitation_probability_max'][i],'wind_kmh':d['wind_speed_10m_max'][i],'weather_code':d['weather_code'][i]})
   if len(days)<7:raise ValueError('Incomplete forecast')
   out[name]={'status':'ok','days':days,'checked_at':NOW.isoformat(),'source':'Open-Meteo composite forecast','source_url':'https://open-meteo.com/','note':'Model-based 16-day outlook; especially uncertain beyond day 7. Not an official Met Office warning.'}
  except Exception as exc:out[name]={'status':'unavailable','days':[],'reason':str(exc)[:90],'source_url':'https://weather.metoffice.gov.uk/'}
 return out

def extract_prices(oil_text,petrol_text):
 prices={'source':'Consumer Council for Northern Ireland','oil_url':'https://www.consumercouncil.org.uk/home-heating/price-checker','forecourt_url':'https://www.consumercouncil.org.uk/ni-fuel-checker','oil':None,'petrol':None,'diesel':None,'status':'unavailable'}
 # All values must have their own nearby unmistakable label and printed date.
 if oil_text:
  date=re.search(r'Average home heating oil price in Northern Ireland on\s+(\d{1,2}\s+\w+\s+20\d\d)',oil_text,re.I)
  segment=oil_text[date.end():date.end()+350] if date else ''
  m=re.search(r'900\s*litres\s*average\s*£\s*([\d,]+\.\d{2})',segment,re.I)
  if date and m:
   val=float(m.group(1).replace(',',''))
   if 200<=val<=2500:prices['oil']={'value':val,'unit':'£ / 900 litres (NI average)','observed_date':date.group(1)}
 if petrol_text:
  for fuel in ('petrol','diesel'):
   match=re.search(r'\b'+fuel+r'\b\s*Average\s+price\s+(\d{2,3}(?:\.\d+)?)\s*p\s+(\d{1,2}\s+\w+\s+20\d\d)',petrol_text,re.I)
   if match and 75<float(match.group(1))<300:
    prices[fuel]={'value':float(match.group(1)),'unit':'pence / litre (NI average)','observed_date':match.group(2)}
 if all(prices.get(k) for k in ('oil','petrol','diesel')):prices['status']='ok'
 elif any(prices.get(k) for k in ('oil','petrol','diesel')):prices['status']='partial'
 return prices

def read_saved_data(path, key=None):
 try:
  data=json.loads(path.read_text(encoding='utf-8'))
  if isinstance(data,dict):
   prices=data.get(key) if key else data
   if isinstance(prices,dict):return prices
 except (OSError,ValueError):
  pass
 return {}


def usable_price(item, fuel):
 if not isinstance(item,dict):return None
 try:
  observed=dt.datetime.strptime(item['observed_date'],'%d %B %Y').date()
  value=item['value']
  if type(value) not in (int,float):return None
  if fuel=='oil':
   valid=200<=value<=2500 and item['unit']=='£ / 900 litres (NI average)'
   max_age=10
  else:
   valid=75<value<300 and item['unit']=='pence / litre (NI average)'
   max_age=3
  age=(NOW.date()-observed).days
  return observed if valid and 0<=age<=max_age else None
 except (KeyError,ValueError,TypeError):
  return None


def collect_prices():
 def text_from(url):
  try:
   parser=TextParser();parser.feed(get(url).decode('utf-8','replace'));return parser.text()
  except Exception as exc:
   print(f'Fuel source {url}: {type(exc).__name__}: {exc}')
   return ''
 prices=extract_prices(text_from('https://www.consumercouncil.org.uk/home-heating/price-checker'),text_from('https://www.consumercouncil.org.uk/ni-fuel-checker'))
 previous=read_saved_data(OUT,'fuel')
 seed=read_saved_data(ROOT/'data'/'fuel-baseline.json')
 for fuel in ('oil','petrol','diesel'):
  candidates=[]
  for item in (prices[fuel],previous.get(fuel),seed.get(fuel)):
   observed=usable_price(item,fuel)
   if observed:candidates.append((observed,item))
  if not candidates:
   prices[fuel]=None
   continue
  observed,item=max(candidates,key=lambda candidate:candidate[0])
  prior=previous.get(fuel)
  prior_date=usable_price(prior,fuel)
  change=prior.get('change') if prior_date==observed else item.get('change')
  if prior_date and prior_date<observed:
   change=round(item['value']-prior['value'],2)
  prices[fuel]={**item,'saved':item is not prices[fuel],'change':change}
 count=sum(prices[fuel] is not None for fuel in ('oil','petrol','diesel'))
 prices['status']=['unavailable','partial','partial','ok'][count]
 return prices


def main():
 from disruptions import collect_traffic
 from security_watch import collect_security
 def clean_notice(value):
  parser=TextParser();parser.feed(value)
  return parser.text()[:400]
 out={'generated_at':NOW.isoformat(),'weather':collect_weather(),'news':collect_news(),'fuel':collect_prices(),'traffic':collect_traffic(get,clean_notice),'security':collect_security(get,TextParser,read_saved_data(OUT,'security'),NOW)}
 OUT.parent.mkdir(exist_ok=True,parents=True)
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Extended source statuses:',[(k,v['status']) for k,v in out['weather'].items()],out['fuel']['status'])
 print('Regional story counts:',{k:len(v) for k,v in out['news']['stories'].items()})
if __name__=='__main__':main()
