import urllib.request,pathlib,json,datetime,hashlib,time,os
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
URL='https://paraiba.pb.gov.br/arquivos/pdfs/PropostaCurriculardoEnsinoMdiodaParabaPCEMPB23.pdf/@@download/file/PropostaCurriculardoEnsinoMdiodaParabaPCEMPB23.pdf'
P=R/'data/raw/PB/pb-pcem.pdf';TEMP=P.with_suffix('.pdf.part');attempts=[]
for n in range(2):
 attempt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':URL,'method':'Ordinary urllib HTTPS GET of exact public download link observed in official view page; no cookies, credentials, browser headers, token replay, challenge solving or TLS bypass.'}
 try:
  with urllib.request.urlopen(URL,timeout=45) as response:
   attempt.update(http_status=response.status,content_type=response.headers.get('Content-Type'),content_length=response.headers.get('Content-Length'),final_url=response.url)
   assert response.url.startswith('https://paraiba.pb.gov.br/'),response.url
   total=0;h=hashlib.sha256();prefix=b''
   with TEMP.open('wb') as target:
    while block:=response.read(1024*1024):
     if not prefix:prefix=block[:16];assert prefix.startswith(b'%PDF-'),f'Non-PDF prefix: {prefix!r}'
     total+=len(block);assert total<=200*1024*1024,'Exceeded authorized200MiB limit';target.write(block);h.update(block)
   attempt.update(bytes=total,sha256=h.hexdigest(),pdf_magic=prefix.decode('latin1'))
  d=pymupdf.open(TEMP);attempt.update(pdf_pages=len(d),needs_pass=d.needs_pass,is_repaired=d.is_repaired,pdf_metadata=d.metadata)
  assert len(d)==867,len(d);assert not d.needs_pass
  if P.exists():assert hashlib.sha256(P.read_bytes()).hexdigest()==h.hexdigest(),'Refuse overwrite different artifact';TEMP.unlink()
  else:TEMP.replace(P)
  attempt.update(result='acquired_and_pdf_validated',local_path=str(P.relative_to(R)))
  attempts.append(attempt);break
 except Exception as e:
  attempt.update(result='error',error=f'{type(e).__name__}: {e}');attempts.append(attempt)
  if TEMP.exists():TEMP.unlink()
  if n==0:time.sleep(1)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast','source_id':'pb-pcem','official_view_url':'https://paraiba.pb.gov.br/arquivos/pdfs/PropostaCurriculardoEnsinoMdiodaParabaPCEMPB23.pdf/view','view_observation':{'content_type_label':'application/pdf','size_label':'7.6 MB','last_modified_label':'25/04/2023 09h27','date_semantics':'Portal last-modified only, not editorial/adoption date.','browser_pdf_pages_visible':867,'browser_cover_visible':'CURRÍCULO DO NOVO ENSINO MÉDIO DA PARAÍBA'},'browser_download_attempt':'Normal FileSaveAs and actual download link opened Save panel with disabled Save, even Downloads/unique filename. No bytes acquired through UI; direct ordinary GET of newly observed public endpoint is separate acquisition.', 'attempts':attempts,'scope':'Acquisition validation only, not full extraction, edition/current adoption, documentary reconciliation or UF readiness.'};(O/'pb-em-official-acquisition.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(attempts[-1],ensure_ascii=False,indent=2))
