import collections,datetime,json,pathlib,re,sys
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;sys.path.insert(0,str(R/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from rn_document_roles import code_occurrences
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']=='pi-computacao-em-2025');assert ingest.sha_file(R/s['local_path'])==s['sha256'];routing=json.loads((R/'docs/evidence/literal-preflight-v150-routing/northeast.json').read_text());target={x['page'] for x in routing['records'] if x['source_id']==s['id']};anchor=None;pages=[];mixed=[]
with pymupdf.open(R/s['local_path']) as doc:
 for pn,page in enumerate(doc,1):
  normalize_native_page(page);reader=NativeGlyphText(page);plain=reader.text();rows=[]
  for line in reader.lines:
   text=''.join(c['text'] for c in line).strip()
   if not text:continue
   b=[c['box'] for c in line];bbox=[min(v[0] for v in b),min(v[1] for v in b),max(v[2] for v in b),max(v[3] for v in b)];rows.append({'page':pn,'text':text,'bbox':bbox})
  relations=[r for r in rows if re.fullmatch(r'RELAÇÃO ENTRE AS HABILIDADES\s*:?',r['text'])]
  if relations:anchor=relations[-1]
  if pn not in target:continue
  tables=page.find_tables().tables
  if tables or relations:
   mixed.append({'page':pn,'routed_failures':sum(r['source_id']==s['id'] and r['page']==pn for r in routing['records']),'reason':('Relationship commentary with a comparison/table layout, conservatively excluded; not a matrix of learning definitions.' if pn==77 else 'Mixed definition matrix and relationship commentary requires complete per-column primary/reference reconstruction.')});continue
  assert anchor is not None and 0<pn-anchor['page']<=3,(pn,anchor)
  assert not any('HABILIDADE DA' in r['text'] or r['text'].startswith('Competência específica:') for r in rows),(pn,'new skill matrix scope boundary')
  occ=code_occurrences(reader,ingest.CODE_ANY);assert occ
  body=reader.text([40,40,805,555]);assert all(40<o['bbox'][0] and o['bbox'][2]<805 and 40<o['bbox'][1] and o['bbox'][3]<555 for o in occ)
  printed_labels=re.findall(r'Pág\.\s*(\d+)',plain);assert len(printed_labels)==1,(pn,printed_labels)
  pages.append({'page':pn,'printed_page_label':printed_labels[0],'preceding_relationship_heading':anchor,'code_occurrences':occ,'native_relationship_page_text':body,'routed_failures':sum(r['source_id']==s['id'] and r['page']==pn for r in routing['records']),'pagewide_role':'reference_in_relationship_commentary','basis':'Complete source commentary continues RELAÇÃO ENTRE AS HABILIDADES; comparison layout such as116 is commentary and no new learning definition. Codes remain literal references.'})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast:primary_narrative_census','source_id':s['id'],'artifact_sha256':s['sha256'],'method':'Read all137original pages in order, fix printed RELAÇÃO ENTRE AS HABILIDADES anchors before target-page classification. Only complete narrative continuation pages with no physical matrix/definition heading and no source code outside the inventoried body can receive page-wide replacement.','target_pages':pages,'excluded_scope_pages':mixed,'summary':{'narrative_pages':len(pages),'literal_source_reference_occurrences':sum(len(r['code_occurrences']) for r in pages),'routed_failures_on_narrative_pages':sum(r['routed_failures'] for r in pages),'excluded_scope_pages':len(mixed),'routed_failures_on_mixed_pages':sum(r['routed_failures'] for r in mixed)},'manifest_modified':False,'cache_modified':False,'runtime_modified':False,'whole_source_reconciled':False,'UF_ready':False}
(O/'pi-computacao-source-only-narrative-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary']))
