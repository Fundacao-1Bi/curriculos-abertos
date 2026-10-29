#!/usr/bin/env python3
"""Independent documentary sample audit; never treats code mentions as completeness."""
import json,pathlib,re,collections,hashlib,datetime,concurrent.futures,unicodedata,os
import pymupdf
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).parent
REVISION=os.environ.get('AUDIT_EXTRACTION_REVISION','page-cell-v1.3.0')
CODE=re.compile(r'(?<![A-Z0-9])(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2}|EM\d{2}(?:[A-Z]{3}\d{3}|LP\d{2}|CO\d{2})|EMIF[A-Z]{2,5}\d{2,3})(?:[A-Z]{1,6}|\*|[/.-][A-Z0-9-]+)*(?![A-Z0-9])')
MAP={'LP':'Língua Portuguesa','MA':'Matemática','CI':'Ciências','GE':'Geografia','HI':'História','AR':'Arte','EF':'Educação Física','LI':'Língua Inglesa','ER':'Ensino Religioso','LGG':'Linguagens e suas Tecnologias','MAT':'Matemática e suas Tecnologias','CNT':'Ciências da Natureza e suas Tecnologias','CHS':'Ciências Humanas e Sociais Aplicadas','EO':'O eu, o outro e o nós','CG':'Corpo, gestos e movimentos','TS':'Traços, sons, cores e formas','ET':'Espaços, tempos, quantidades, relações e transformações','CO':'Computação'}
BASE={'al-recal-ei-2019','al-recal-ef','al-recal-em','ba-dcrb-ei-ef','ba-dcrb-em-vol2-2022','ce-dcrc-ei-ef-2019','ce-dcrc-em-2021','ma-dctm-ei-ef','ma-dctm-em-vol2','pb-proposta-ei-ef','pe-curriculo-ei','pe-curriculo-ef','pe-curriculo-em-2021','pi-curriculo-ei-ef','pi-curriculo-em-caderno1-2021','rn-documento-ei-2018','rn-documento-ef-2018','rn-referencial-em','se-curriculo-ei-ef','se-curriculo-em'}
def norm(t):return ' '.join(unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().casefold().split())
def group(code):
 st=code[:2]
 if code.startswith('EMIF'):return ('EM','Itinerários Formativos')
 if st=='EI':return st,('Escuta, fala, pensamento e imaginação' if code[4:6]=='EF' else MAP.get(code[4:6],code[4:6]))
 return st,MAP.get(code[4:7] if st=='EM' and not code.startswith(('EM13LP','EM13CO')) else code[4:6],code[4:7])
def scan(s):
 if s.get('status')!='acquired' or not s.get('include_in_corpus',True):return None
 p=ROOT/s['local_path'];sha=hashlib.sha256(p.read_bytes()).hexdigest()
 if sha!=s['sha256']:raise ValueError('hash mismatch '+s['id'])
 doc=pymupdf.open(p);anchors=[];counts=collections.Counter();codepages=[]
 for n,page in enumerate(doc):
  if s.get('extraction_pages') and n+1 not in s['extraction_pages']:continue
  text=page.get_text('text',sort=True)
  matches=list(CODE.finditer(text));counts.update(m.group() for m in matches)
  if matches:codepages.append(n+1)
  if s['id'] not in BASE or n+1 in s.get('non_curricular_code_pages',[]):continue
  # The sampling frame is independent native PDF code occurrences, not extracted item IDs.
  # Prefer dense curricular pages, but this alone does not prove each occurrence is a learning.
  if len(matches)<3:continue
  for m in matches:
   st,component=group(m.group())
   if st not in s['stages']:continue
   anchors.append({'source_id':s['id'],'uf':s['uf'],'stage':st,'component':component,'code':m.group(),'page':n+1,'source_text_context':text[max(0,m.start()-100):m.end()+280],'source_code_mentions_on_page':len(matches),'sha256':sha})
 cache=ROOT/'data/extracted'/f'{sha}-{REVISION}.json';ex=json.loads(cache.read_text()) if cache.exists() else None
 return {'source_id':s['id'],'sha256':sha,'document_pages':len(doc),'native_code_mentions':sum(counts.values()),'distinct_literal_codes':len(counts),'pages_with_codes':codepages,'ocr_need_not_evaluated':True,'completeness_denominator':None,'completeness_note':'Code mentions include illustrations, repetitions and references; they are NOT a denominator of learnings.','anchors':anchors,'extract':ex,'source':s}
S=json.loads((ROOT/'data/manifests/northeast.json').read_text());R=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 for r in ex.map(scan,S):
  if r:R.append(r)
bygroup=collections.defaultdict(list)
for r in R:
 for a in r['anchors']:bygroup[(a['uf'],a['stage'],a['component'])].append(a)
selected=[]
for g,aa in sorted(bygroup.items()):
 # One deterministic interior observation per stratum; first/last added for known long-block cases below.
 aa=sorted(aa,key=lambda a:(a['source_id'],a['page'],a['code']))
 a=aa[len(aa)//2];a['selection']='interior native-code occurrence per UF/stage/component';selected.append(a)
byid={r['source_id']:r for r in R};findings=[]
for a in selected:
 r=byid[a['source_id']];ex=r['extract']
 if not ex:a.update(result='pending_extraction',reason='No cache for requested extraction revision');continue
 candidates=[i for i in ex['items'] if i.get('code')==a['code'] and any(e.get('page')==a['page'] for e in i.get('evidence',[]))]
 a['matched_item_ids']=[i['id'] for i in candidates]
 if not candidates:
  a.update(result='no_extracted_coded_item_at_anchor',reason='Source code occurrence may be a learning or reference; document layout review needed to classify.');continue
 checks=[]
 doc=pymupdf.open(ROOT/r['source']['local_path']);page=doc[a['page']-1]
 for i in candidates:
  es=[e for e in i['evidence'] if e.get('page')==a['page']];e=es[0];box=e.get('bbox')
  if box:
   clip=page.get_text('text',clip=pymupdf.Rect(box),sort=True)
   literal_code=a['code'] in clip;literal_text=norm(i['text']) in norm(clip)
   occurrences=list(CODE.finditer(clip));samecell=len({m.group() for m in occurrences})
   check={'item_id':i['id'],'method':e.get('method'),'bbox':box,'code_in_cell':literal_code,'text_in_cell':literal_text,'codes_in_cell':samecell,'source_cell_excerpt':clip[:1200],'extracted_text':i['text'][:1600],'cross_page_continuation':i.get('cross_page_continuation',False)}
   if not literal_code or (not literal_text and not i.get('cross_page_continuation')):
    check['result']='cell_literal_mismatch';findings.append({'source_id':a['source_id'],'page':a['page'],'code':a['code'],'severity':'critical_candidate','issue':'cell_literal_mismatch','detail':check})
   elif samecell>1:check['result']='multiple_codes_requires_documentary_review'
   else:check['result']='literal_code_text_location_matched_automatically'
  else:
   check={'item_id':i['id'],'result':'coordinate_layout_pending','method':e.get('method'),'extracted_text':i['text'][:1200]}
  checks.append(check)
 a.update(result='sample_inspected',checks=checks)
for r in R:
 r.pop('anchors');r.pop('extract');r.pop('source')
report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast','extraction_revision':REVISION,'method':'Independent native-PDF sampling frame by UF/stage/component; compare canonical item code/text against its declared cell location. References and diagrams do not count as source expected learnings. No full part reconciliation is asserted.','source_inventory':R,'samples':selected,'findings':findings,'summary':{'acquired_sources_inspected':len(R),'sample_strata':len(selected),'ufs':sorted({x['uf'] for x in selected}),'by_result':dict(collections.Counter(x['result'] for x in selected)),'cell_literal_mismatch_candidates':len(findings),'fully_reconciled_parts':0}}
(OUT/'audit-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
