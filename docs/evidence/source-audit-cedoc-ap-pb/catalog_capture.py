from pathlib import Path
import urllib.request,json,hashlib,datetime,concurrent.futures,re,html
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
files=list(OUT.glob('*-validation.json'))
def run(p):
 r=json.loads(p.read_text());req=urllib.request.Request(r['catalogPage'],headers={'User-Agent':'CurriculosAbertos source validation/1.0'})
 with urllib.request.urlopen(req,timeout=60) as res:
  payload=res.read(4*1024*1024);record={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requested_url':r['catalogPage'],'effective_url':res.url,'http_status':res.status,'content_type':res.headers.get('content-type'),'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
 dest=ROOT/'data/raw'/r['uf']/(r['source_id']+'-catalog.html');dest.write_bytes(payload);record['private_snapshot']=str(dest.relative_to(ROOT));text=payload.decode('utf-8');plain=html.unescape(re.sub('<[^>]*>',' ',text));plain=re.sub(r'\s+',' ',plain)
 keys=['Data de publicação:','Local de publicação:','Instituição(ões) relacionada(s):','Data de Acesso à Fonte:','Tamanho:','Tipo Licença:'];snippets=[]
 for key in keys:
  n=plain.find(key)
  if n>=0:snippets.append({'label':key,'literal_context':plain[n:n+210]})
 record['catalog_field_evidence']=snippets;record['originalSource_url_present_in_html']=r['originalSource'] in html.unescape(text);r['catalog_capture']=record;p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r['source_id'],record)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,files))
