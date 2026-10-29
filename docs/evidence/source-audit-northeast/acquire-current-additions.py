#!/usr/bin/env python3
import pathlib,urllib.request,json,hashlib,datetime,time,concurrent.futures
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
entries=[('pi-computacao-em','PI','https://seduc.pi.gov.br/download/diretrizes/Curriculo_de_Computacao___EM.pdf'),('ce-matrizes-2026-original','CE','https://www.seduc.ce.gov.br/wp-content/uploads/sites/37/2025/12/Matrizes-Curriculares-2026-V2.pdf'),('ce-matrizes-2026-migrated','CE','https://www.ce.gov.br/seduc/wp-content/uploads/sites/63/2025/12/Matrizes-Curriculares-2026-V2.pdf'),('ce-atos-index','CE','https://legislacao.cee.ce.gov.br/legislacao/resolucoes/conselho-estadual-de-educacao/'),('ce-matrizes-news','CE','https://www.ce.gov.br/seduc/2025/12/17/seduc-divulga-matrizes-curriculares-2026/')]
def fetch(e):
 sid,uf,url=e;attempts=[]
 for n in range(2):
  a={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':url}
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:
    b=r.read(60*1024*1024);a.update(http_status=r.status,content_type=r.headers.get('Content-Type'),final_url=r.url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
   pdf=b.startswith(b'%PDF-');p=R/f'data/raw/{uf}/{sid}{".pdf" if pdf else ".html"}';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);a['local_path']=str(p.relative_to(R));a['is_pdf']=pdf
   if pdf:a.update(pages=len(f.open(p)),metadata=f.open(p).metadata)
   attempts.append(a);break
  except Exception as err:a['error']=str(err);attempts.append(a)
 return {'candidate_id':sid,'uf':uf,'attempts':attempts}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:results=list(ex.map(fetch,entries))
(O/'current-additions-acquisition.json').write_text(json.dumps({'actor_type':'automated','results':results},ensure_ascii=False,indent=2)+'\n')
for r in results:print(r['candidate_id'],r['attempts'][-1].get('pages'),r['attempts'][-1].get('error'),flush=True)
