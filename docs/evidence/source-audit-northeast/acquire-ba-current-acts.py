import pathlib,json,datetime,urllib.request,hashlib,time
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sources=[('ba-resolucao-266-2025-computacao','https://www.ba.gov.br/conselhodeeducacao/sites/site-cee/files/2026-04/Resolu%C3%A7%C3%A3o%20CEE%20BA%20n%C2%BA%20266%202025%20-%20PARA%20PUBLICIZA%C3%87%C3%83O.pdf',21),('ba-resolucao-125-2024-historia','https://www.ba.gov.br/conselhodeeducacao/sites/site-cee/files/2025-02/RESOLUCAO_CEE_N_125_2024_HISTORIA_DA_BAHIA.pdf',2)];result=[];total=0
for sid,url,expected in sources:
 p=R/'data/raw/BA'/f'{sid}.pdf';attempts=[]
 for n in range(2):
  a={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':url,'method':'OrdinaryHTTPSGET of literal PDF link discovered in official CEE public catalogue; no credentials, TLS bypass or session replication.'}
  try:
   with urllib.request.urlopen(url,timeout=35) as r:
    a.update(http_status=r.status,content_type=r.headers.get('Content-Type'),content_length=r.headers.get('Content-Length'),final_url=r.url);b=r.read(8*1024*1024+1);assert b.startswith(b'%PDF-') and len(b)<=8*1024*1024;assert total+len(b)<=8*1024*1024,'Total acquisition bound8MiB'
   d=pymupdf.open(stream=b,filetype='pdf');assert len(d)==expected and not d.needs_pass
   if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(b).hexdigest(),'Refuse overwrite of different snapshot'
   else:p.write_bytes(b)
   total+=len(b);a.update(result='acquired_and_pdf_validated',bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),pdf_pages=len(d),native_characters_by_page=[len(x.get_text().strip()) for x in d],local_path=str(p.relative_to(R)),pdf_metadata=d.metadata);attempts.append(a);break
  except Exception as e:
   a.update(result='error',error=f'{type(e).__name__}: {e}');attempts.append(a)
   if n==0:time.sleep(1)
 result.append({'source_id':sid,'official_catalogue_url':'https://www.ba.gov.br/conselhodeeducacao/biblioteca-documentos/resolucoes-normativas','attempts':attempts})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','sources':result,'total_acquired_bytes':total,'scope':'Actual official artifact acquisition; no wholeUF or structured/reconciled act readiness inferred. Source metadata/inventory follow original contents.'};(O/'ba-current-acts-acquisition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
