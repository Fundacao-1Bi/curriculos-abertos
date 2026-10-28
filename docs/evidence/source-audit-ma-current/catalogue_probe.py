#!/usr/bin/env python3
"""Read public MA news/catalogue metadata, stopping at authentication redirects."""
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import quote,urlsplit,unquote
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-ma-current';RAW=ROOT/'data/raw/MA'
class StopAuthentication(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if urlsplit(newurl).hostname=='accounts.google.com':raise RuntimeError('Authentication redirect; stopped without supplying credentials')
  if urlsplit(newurl).scheme!='https':raise RuntimeError('Non-HTTPS redirect stopped')
  return super().redirect_request(req,fp,code,msg,headers,newurl)
class Visible(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.text=[];self.links=[];self.href=None;self.linktext=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t in ('script','style'):self.skip+=1
  if t=='a':self.href=a.get('href');self.linktext=[]
 def handle_endtag(self,t):
  if t in ('script','style') and self.skip:self.skip-=1
  if t=='a' and self.href:self.links.append({'label':' '.join(self.linktext).strip(),'url':self.href});self.href=None
 def handle_data(self,d):
  if not self.skip:self.text.append(d)
  if self.href:self.linktext.append(d)
def fetch(pair):
 label,url=pair;result={'label':label,'url':url,'at':datetime.now(timezone.utc).isoformat(),'actor_type':'automated'}
 try:
  with build_opener(StopAuthentication()).open(Request(url,headers={'User-Agent':'CurriculosAbertos/1.0 official-source research'}),timeout=40) as r:
   b=r.read(8*1024*1024);result.update(http_status=r.status,final_url=r.geturl(),content_type=r.headers.get('Content-Type'),bytes=len(b),response_sha256=hashlib.sha256(b).hexdigest())
  p=RAW/(result['response_sha256']+'.html');p.write_bytes(b);result['private_snapshot_path']=str(p.relative_to(ROOT))
  if 'application/json' in (result.get('content_type') or ''):
   data=json.loads(b);result['result_count']=len(data);result['items']=[{'id':e.get('id'),'title':e.get('title'),'url':e.get('url') or e.get('link'),'source_url':e.get('source_url')} for e in data]
   content=' '.join(e.get('content',{}).get('rendered','') for e in data)
  else:content=b.decode('utf-8','replace')
  h=Visible();h.feed(content);text=' '.join(' '.join(h.text).split());(RAW/(result['response_sha256']+'.txt')).write_text(text)
  result['relevant_links']=[e for e in h.links if any(k in unquote(e['url']).lower() for k in ('sugeda','drive.google','matriz','matrizes','curricul','pratica','prática'))]
  result['date_mentions']=re.findall(r'\b\d{2}/\d{2}/20\d{2}\b',text)[:20]
  needles=['Organizadores Curriculares','Guias da Prática Docente','matrizes curriculares','2026','SUGEDA']
  result['short_locators']=[{'needle':n,'found':n.lower() in text.lower()} for n in needles]
  result['status']='public_metadata_read'
 except Exception as e:result.update(status='not_acquired',error=f'{type(e).__name__}: {e}')
 return result
URLS=[
('GAEM news','https://www.educacao.ma.gov.br/seduc-realiza-formacao-dos-gaems-para-fortalecer-o-planejamento-do-ano-letivo-2026/'),
('Escutas news','https://www.educacao.ma.gov.br/seduc-realiza-2o-ciclo-de-escutas-e-dialogos-pedagogicos-com-professores-de-todo-o-maranhao/'),
('SUGEDA management','https://sites.google.com/edu.ma.gov.br/sugeda/gest%C3%A3o-escolar'),
('SUGEDA components','https://sites.google.com/edu.ma.gov.br/sugeda/ensino-m%C3%A9dio/componentes-curriculares'),
('SUGEDA EM','https://sites.google.com/edu.ma.gov.br/sugeda/ensino-m%C3%A9dio'),
]
for term in ['SUGEDA','prática docente','matrizes','educação digital']:
 for endpoint in ['search','pages']:
  URLS.append((f'Official {endpoint} {term}','https://www.educacao.ma.gov.br/wp-json/wp/v2/'+endpoint+'?search='+quote(term)+'&per_page=100'))
def main():
 OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
 with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(fetch,URLS))
 (OUT/'catalogue-access-and-government-chain.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{'label':e['label'],'status':e['status'],'links':len(e.get('relevant_links',[])),'results':e.get('result_count'),'error':e.get('error')} for e in results],ensure_ascii=False))
if __name__=='__main__':main()
