"""Exact supplied CEDOC URLs; bounded verified-TLS fetch, immutable raw files, pre-extraction validation."""
from pathlib import Path
import urllib.request,hashlib,json,datetime,time,concurrent.futures
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
SPECS=[dict(uf='AP',id='ap-rca-ei-ef-cedoc',asset='https://observatoriodeeducacao.institutounibanco.org.br/api/assets/observatorio/85040b57-90bf-421d-879f-a0ac2bf9062e/?download=0',catalog='https://observatoriodeeducacao.institutounibanco.org.br/cedoc/detalhe/tf-referencial-curricular-amapaense-educacao-infantil-e-ensino-fundamental,01847f46-8b77-4a4d-96bb-72eae9fcf44f',original='http://basenacionalcomum.mec.gov.br/images/implementacao/curriculos_estados/documento_curricular_ap.pdf',author='Secretaria de Estado da Educação do Amapá',expected_pages=614,expected_bytes=4199170,expected_sha256='bcf0aa03705580d2f92c7471a68ddf71121748d3407928840f0c9bba402e5c7e'),dict(uf='PB',id='pb-proposta-ei-ef-cedoc',asset='https://observatoriodeeducacao.institutounibanco.org.br/api/assets/observatorio/89fd023c-293c-460d-a282-87588f43eaee/?download=0',catalog='https://observatoriodeeducacao.institutounibanco.org.br/cedoc/detalhe/tf-proposta-curricular-do-estado-da-paraiba-educacao-infantil-e-ensino-fundamental,39027aab-c324-4c7e-bb44-0cc164c79a01',original='https://drive.google.com/file/d/1qQbrcc_3AmUaIbaDZtPR2ONtiZhqOjlL/view',author='Secretaria da Educação do Estado da Paraíba',expected_pages=392,expected_bytes=7115062,expected_sha256='af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453')]
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def fetch(spec):
 attempts=[];raw=ROOT/'data/raw'/spec['uf']/(spec['id']+'.pdf');raw.parent.mkdir(parents=True,exist_ok=True)
 for attempt in range(1,4):
  when=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
  try:
   req=urllib.request.Request(spec['asset'],headers={'User-Agent':'CurriculosAbertos source validation/1.0','Accept':'application/pdf'})
   with urllib.request.urlopen(req,timeout=60) as res:
    payload=res.read(32*1024*1024+1);headers={k.lower():v for k,v in res.headers.items()};record={'at':when,'attempt':attempt,'http_status':res.status,'effective_url':res.url,'headers':headers,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'prefix_hex':payload[:16].hex(),'is_pdf':payload.startswith(b'%PDF-'),'seconds':round(time.monotonic()-t,3)}
   attempts.append(record)
   assert record['http_status']==200 and record['is_pdf'] and len(payload)<=32*1024*1024,record
   if raw.exists():assert raw.read_bytes()==payload,'Existing raw artifact differs: preserve and investigate'
   else:raw.write_bytes(payload)
   doc=fitz.open(raw);count=len(doc);assert count>0 and not doc.needs_pass
   page_checks=[];errors=[]
   for pn,page in enumerate(doc,1):
    try:
     rect=page.rect;chars=len(page.get_text('text'));page_checks.append({'page':pn,'width':round(rect.width,3),'height':round(rect.height,3),'native_characters':chars})
    except Exception as exc:errors.append({'page':pn,'error':str(exc)})
   result={'source_id':spec['id'],'uf':spec['uf'],'stages':['EI','EF'],'author':spec['author'],'catalogPage':spec['catalog'],'catalog_publisher':'Instituto Unibanco — Observatório de Educação/CEDOC','catalog_publication_year_claim':'2020','catalog_license_claim':'Domínio Público; catalog assertion, independent redistribution assessment not established','originalSource':spec['original'],'requested_asset_url':spec['asset'],'effective_url':record['effective_url'],'capturedate':when,'local_path':str(raw.relative_to(ROOT)),'sha256':record['sha256'],'bytes':len(payload),'document_pages':count,'expected':{k:v for k,v in spec.items() if k.startswith('expected_')},'expected_matches':{'bytes':len(payload)==spec['expected_bytes'],'sha256':record['sha256']==spec['expected_sha256'],'pages':count==spec['expected_pages']},'technicalvalidation':{'http_status':record['http_status'],'content_type':headers.get('content-type'),'content_type_pdf':'application/pdf' in headers.get('content-type','').lower(),'pdf_signature':record['is_pdf'],'parser':'PyMuPDF '+fitz.VersionBind,'all_page_objects_checked':len(page_checks),'page_errors':errors,'is_repaired':doc.is_repaired,'metadata':doc.metadata,'status':'passed' if not errors else'requires_investigation','parser_open_is_completeness':False},'edition_vigencycheck':{'edition':None,'vigency':None,'status':'pending_documentary_comparison_not_inferred_from_catalog_2020'},'attempts':attempts,'page_checks':page_checks}
   write(OUT/(spec['id']+'-validation.json'),result);print(spec['id'],count,len(payload),record['sha256'],flush=True);return result
  except Exception as exc:
   attempts.append({'at':when,'attempt':attempt,'error':repr(exc),'seconds':round(time.monotonic()-t,3)});write(OUT/(spec['id']+'-attempts.json'),attempts)
   if attempt==3:raise
   time.sleep(attempt*2)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(fetch,SPECS))
write(OUT/'acquisition-summary.json',[{k:v for k,v in r.items() if k not in ['page_checks','attempts']} for r in results])
