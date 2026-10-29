from pathlib import Path
import concurrent.futures,datetime,hashlib,json,urllib.request,urllib.error
ROOT=Path.cwd();OUT=ROOT/'var/private-evidence/pe-ei-provenance-peer';OUT.mkdir(parents=True,exist_ok=True)
URLS=[('cee114current','https://www.cee.pe.gov.br/wp-content/uploads/2025/10/PARECER-114-2018.pdf'),('see-media-curriculo','https://portal.educacao.pe.gov.br/wp-json/wp/v2/media?search=curriculo&per_page=100&_fields=id,date,link,title,source_url'),('see-posts-curriculo','https://portal.educacao.pe.gov.br/wp-json/wp/v2/posts?search=curr%C3%ADculo&per_page=100&_fields=id,date,link,title,content'),('see-posts-alfabetizada','https://portal.educacao.pe.gov.br/wp-json/wp/v2/posts?search=alfabetizada&per_page=100&_fields=id,date,link,title,content')]
def fetch(v):
 key,url=v;result={'key':key,'requested_url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 Curriculum source verification'}),timeout=25)as r:
   raw=r.read(10*1024*1024+1);assert len(raw)<=10*1024*1024;result.update(http_status=r.status,final_url=r.url,content_type=r.headers.get('Content-Type'),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());p=OUT/(key+('.pdf'if raw.startswith(b'%PDF')else'.json'if raw[:1]in[b'[',b'{']else'.html'));p.write_bytes(raw);result['private_snapshot']=str(p.relative_to(ROOT))
 except Exception as e:result['error']=str(e)
 return result
if __name__=='__main__':
 results=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(fetch,URLS));(OUT/'fetch-log.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False,indent=2))
