#!/usr/bin/env python3
"""Primary-only AP peer inventories. Must precede inspecting adapter output."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
SOURCES=[('ap-rca-ei-ef-mec','data/raw/AP/ap-native-ei-ef.pdf','23c42348e0b0e00d4135a108366141a257bec54b7b1bff79e521c822d9903f89',614),('ap-rca-ei-ef','data/raw/AP/ap-rca-ei-ef.pdf','fc40788a0165eb6fa61d713cee87d4b0b95b45435e496b43bb477f9471a103c4',339)]
def sha(value):return hashlib.sha256(value).hexdigest()
def dump(name,data):OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def base():return {'actor_type':'automated','actor_id':'codex-independent-ap-peer','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'adapter_read':False,'publication_modified':False,'human_pedagogical_review_claimed':False}
def open_primary(spec):
 sid,path,digest,pages=spec;assert sha((ROOT/path).read_bytes())==digest;doc=fitz.open(ROOT/path);assert len(doc)==pages;return doc
def primary():
 sources=[]
 for spec in SOURCES:
  sid,path,digest,pages=spec;doc=open_primary(spec);rows=[]
  for pi,p in enumerate(doc):
   text=p.get_text('text',sort=False);anchors=[{'literal':m.group(),'offset':m.start()} for m in re.finditer(r'(?<![A-Z0-9])(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}(?:[-/]?AP)?[-/]?\d{2,3}(?:[-/]?AP)?)(?![A-Z0-9])',text)];rows.append({'page':pi+1,'native_text_sha256':sha(text.encode()),'native_characters':len(text),'native_words':len(p.get_text('words')),'anchors':anchors,'literal_bullets':text.count('\uf0b7'),'heading_signals':[line.strip() for line in text.splitlines() if re.match(r'^\s*(?:[IVXLCDM]+\s*[–-]\s*Campo|[34]\.\s|[34]\.\d\.)',line)]})
  sources.append({'source_id':sid,'artifact':path,'artifact_sha256':digest,'pages':pages,'page_inventory':rows,'EI_occurrences':sum(sum(a['literal'].startswith('EI') for a in r['anchors']) for r in rows),'unique_EI_codes':sorted({a['literal'] for r in rows for a in r['anchors'] if a['literal'].startswith('EI')}),'native_EF_occurrences':sum(sum(a['literal'].startswith('EF') for a in r['anchors']) for r in rows)})
 dump('primary-census.json',{**base(),'method':'Complete primary native-text/code/bullet/page inventory, before reading adapter outputs. No global code aliases or OCR inference. Code scan is a literal character inventory, not an approved learning denominator.','sources':sources});print([(s['source_id'],s['pages'],s['EI_occurrences'],s['native_EF_occurrences']) for s in sources])
def ei():
 doc=open_primary(SOURCES[0]);pages=[];codes=[];bullets=[]
 for pi in range(92,131):
  page=doc[pi];words=page.get_text('words',sort=False);groups=collections.defaultdict(list)
  for wi,w in enumerate(words):
   groups[(w[5],w[6])].append((wi,w));m=re.search(r'EI\d{2}[A-Z]{2}\d{2}',w[4])
   if m:codes.append({'page':pi+1,'word_index':wi,'code':m.group(),'literal_word':w[4],'bbox':list(w[:4])})
  raw=page.get_text('rawdict')
  for bi,b in enumerate(raw['blocks']):
   for li,line in enumerate(b.get('lines',[])):
    for si,span in enumerate(line['spans']):
     for ci,char in enumerate(span['chars']):
      if char['c']=='\uf0b7':bullets.append({'page':pi+1,'rawdict_index':[bi,li,si,ci],'glyph':char['c'],'bbox':list(char['bbox'])})
  headings=[{'text':' '.join(w[4] for wi,w in group),'bbox':[min(w[0] for wi,w in group),min(w[1] for wi,w in group),max(w[2] for wi,w in group),max(w[3] for wi,w in group)]} for group in groups.values() if any('ANO' in w[4].upper() or 'MESES' in w[4].upper() for wi,w in group) and len(' '.join(w[4] for wi,w in group))<100]
  pages.append({'page':pi+1,'native_word_count':len(words),'native_words_sha256':sha(json.dumps([list(w) for w in words],ensure_ascii=False,separators=(',',':')).encode()),'age_heading_candidates':headings,'bullet_x_coordinates':dict(collections.Counter(round(b['bbox'][0],2) for b in bullets if b['page']==pi+1))})
 assert len(codes)==len({c['code'] for c in codes})==93 and len(bullets)==465
 dump('ei-primary-inventory.json',{**base(),'source_id':SOURCES[0][0],'artifact':SOURCES[0][1],'artifact_sha256':SOURCES[0][2],'scope_pages':[93,131],'method':'Before adapter inspection: every literal EI code and U+F0B7 experience glyph from rawdict, retaining exact physical anchors and native age-heading candidates. No alias, semantic splitting, nearest-text replacement or OCR.','expected_objective_codes':93,'expected_local_experience_markers':465,'objective_anchors':codes,'experience_anchors':bullets,'pages':pages});print({'objectives':len(codes),'experience_bullets':len(bullets)})
def continuations():
 doc=open_primary(SOURCES[0]);loc=ROOT/'docs/evidence/source-audit-ap-eief/ap614-continuation-locators.json';ls=json.loads(loc.read_text());assert ls['artifact_sha256']==SOURCES[0][2];tables={};records=[]
 for l in ls['cells']:
  pi=l['page']-1
  if pi not in tables:tables[pi]=doc[pi].find_tables(strategy='lines_strict').tables
  t=tables[pi][l['table']];box=t.rows[l['row']].cells[l['column']];assert box;text=doc[pi].get_text('text',clip=fitz.Rect(box),sort=False);records.append({**l,'bbox':list(box),'literal_text':text,'literal_text_sha256':sha(text.encode()),'native_words':[list(w) for w in doc[pi].get_text('words',clip=fitz.Rect(box),sort=False)],'physical_without_EI_EF_anchor':not bool(re.search(r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2})',text))})
 box=doc[528].find_tables(strategy='lines_strict').tables[0].rows[5].cells[2];records.append({'page':529,'table':0,'row':5,'column':2,'bbox':list(box),'kind':'independent_uncoded_History_cell','literal_text':doc[528].get_text('text',clip=fitz.Rect(box),sort=False),'native_words':[list(w) for w in doc[528].get_text('words',clip=fitz.Rect(box),sort=False)]})
 dump('continuation-primary-inventory.json',{**base(),'source_id':SOURCES[0][0],'artifact_sha256':SOURCES[0][2],'locator_input_sha256':sha(loc.read_bytes()),'records':records,'scope_limitation':'Coordinates supplied by owner without text; all cell wording independently read from the primary. This targeted list is not asserted as exhaustive corpus denominator.'});print({'provided_continuations':len(ls['cells']),'without_code':sum(r.get('physical_without_EI_EF_anchor',False) for r in records),'additional_History_cells':1})
def legacy():
 pdf=open_primary(SOURCES[1]);digest=SOURCES[1][2];canonical=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode();records=[];errors=[]
 for path in (ROOT/'data/extracted/ocr').glob('*.json'):
  raw=path.read_bytes()
  if digest.encode()not in raw:continue
  d=json.loads(raw)
  if d.get('artifact_sha256')!=digest:continue
  page=d['page'];assert 1<=page<=339;unsigned={k:v for k,v in d.items()if k not in('result_sha256','cache_hit')};integrity=sha(canonical(unsigned))==d.get('result_sha256');p=pdf[page-1];p.remove_rotation();rect=p.rect;identity={'artifact_sha256':digest,'page':page,'rect':[rect.x0,rect.y0,rect.width,rect.height],'rotation':p.rotation,'configuration':d['configuration']};key_ok=sha(canonical(identity))==d['cache_key']==path.stem
  if not integrity or not key_ok:errors.append({'path':str(path.relative_to(ROOT)),'result_hash_valid':integrity,'cache_identity_valid':key_ok})
  matches=[m.group()for m in re.finditer(r'(?<![A-Z0-9])(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}(?:[-/]?AP)?[-/]?\d{2,3}(?:[-/]?AP)?)(?![A-Z0-9])',d['text'])];records.append({'page':page,'cache':str(path.relative_to(ROOT)),'cache_file_sha256':sha(raw),'cache_identity_valid':key_ok,'result_hash_valid':integrity,'revision':d['revision'],'configuration':d['configuration'],'review_status':d['review_status'],'words':len(d['words']),'warning_count':len(d['warnings']),'candidate_literal_codes':matches})
 by=collections.defaultdict(list)
 for r in records:by[r['page']].append(r)
 report={**base(),'source_id':SOURCES[1][0],'artifact_sha256':digest,'document_pages':339,'cache_records':len(records),'pages_with_cache':len(by),'missing_pages':sorted(set(range(1,340))-set(by)),'pages_with_multiple_configurations':{str(k):len(v)for k,v in by.items()if len(v)>1},'integrity_errors':errors,'candidate_literal_code_occurrences':sum(len(r['candidate_literal_codes'])for r in records),'records':sorted(records,key=lambda r:(r['page'],r['cache'])),'new_OCR_executed':False,'edition_equivalence_asserted':False,'limitation':'Hashes prove integrity/provenance of existing OCR candidates, not correctness of OCR wording or code identities. No repaired code or cross-edition alias is accepted from these candidates. Native PDF has no readable EI/EF code text. Physical spot checks and documentary reconciliation remain separate.'};dump('legacy339-ocr-inventory.json',report);print({k:v for k,v in report.items()if k not in('records','pages_with_multiple_configurations')})
if __name__=='__main__':
 if sys.argv[1:]==['primary']:primary()
 elif sys.argv[1:]==['ei']:ei()
 elif sys.argv[1:]==['continuations']:continuations()
 elif sys.argv[1:]==['legacy']:legacy()
 else:raise SystemExit('usage: inventory.py primary|ei|continuations|legacy')
