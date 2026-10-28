#!/usr/bin/env python3
"""Whole RN source/role audit; no original, cache, manifest or core modifications."""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;OUT.mkdir(parents=True,exist_ok=True);PRIVATE=ROOT/'var/private-evidence/source-audit-rn-fidelity';PRIVATE.mkdir(parents=True,exist_ok=True)
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):raise RuntimeError('Use patched var/venv-pipeline/bin/python')
sys.path.insert(0,str(ROOT/'pipeline'))
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ingest import CODE_ANY,clean_text,finalize_items
SID={'rn-trilhas-aprofundamento','rn-dcec-computacao'}
def ws(s):return re.sub(r'\s+',' ',s or'').strip()
def norm(s):return ws(''.join(c for c in unicodedata.normalize('NFKD',s or'').casefold()if not unicodedata.combining(c)))
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def in_box(b,x,y):return b[0]<=x<b[2]and b[1]<=y<b[3]
def role_of(label):
 t=norm(label)
 if re.fullmatch(r'habilidades?',t):return'learning_definition'
 if t.startswith('explicacao')and'habilidade'in t:return'explanation_reference_context'
 if t=='exemplos':return'example_reference_context'
 if t.startswith('sugestoes didaticas'):return'pedagogical_reference_context'
 if t.startswith('objeto')and'conhecimento'in t:return'knowledge_object_context'
 return None
sources=[s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s['id']in SID];baseline=json.loads((ROOT/'docs/evidence/data-preflight-native-baseline.json').read_text());failureids={s['id']:{f['id']for f in baseline['failures']if f.get('source_id')==s['id']}for s in sources}
pages=[];cells=[];cards=[];anchors=[];checks=[];summaries=[];negatives=[]
for source in sources:
 path=ROOT/source['local_path'];digest=sha(path)
 if digest!=source['sha256']:raise RuntimeError('Source SHA mismatch')
 D=fitz.open(path);cache_path=ROOT/'data/extracted'/f'{digest}-page-cell-v1.4.0.json';baseline_archive=PRIVATE/f'baseline-cache-{source["id"]}.json';cache_path=baseline_archive if baseline_archive.exists()else cache_path;cache=json.loads(cache_path.read_text());items=finalize_items(cache['items'],[source]);by_page=collections.defaultdict(list)
 for item in items:
  if item.get('code'):
   for ei,ev in enumerate(item['evidence']):by_page[ev['page']].append((item,ei,ev))
 source_cells=[];source_cards=[];source_anchors=[];source_checks=[];source_counts=collections.Counter();header_labels=collections.Counter();pseudo_fonts=collections.Counter();sampled=set()
 for index,page in enumerate(D):
  number=index+1;normalization=normalize_native_page(page);reader=NativeGlyphText(page);text=reader.text();words=page.get_text('words');footers=[{'label':w[4],'bbox':list(w[:4]),'half':'left'if(w[0]+w[2])/2<page.rect.width/2 else'right'}for w in words if w[4].isdigit()and w[1]>page.rect.height-55];table_records=[]
  physical_pseudo=[]
  for span in page.get_texttrace():
   for c in span['chars']:
    if c[1]<0:pseudo_fonts[(span['font'],chr(c[0]))]+=1;physical_pseudo.append({'font':span['font'],'unicode':chr(c[0]),'origin':list(c[2])})
  source_counts['all_trace_expansions']+=len(physical_pseudo)
  page_cards=[]
  if source['id']=='rn-trilhas-aprofundamento':
   for pi,path_info in enumerate(page.get_drawings()):
    box=path_info['rect']
    if path_info['type']!='s'or not 40<box.width<page.rect.width*.7 or not 18<box.height<160 or len(path_info['items'])!=1 or path_info['items'][0][0]not in['qu','re']:continue
    native=reader.text(list(box));matches=list(CODE_ANY.finditer(native))
    if not matches:continue
    residual=norm(CODE_ANY.sub('',native)).strip(' ();:,.[]/–—-');labels=['investigacao cientifica','processos criativos','mediacao e intervencao sociocultural','empreendedorismo'];is_reference=residual in labels
    rec={'source_id':source['id'],'page':number,'path_index':pi,'bbox':list(box),'native_text':native,'codes':[m.group()for m in matches],'source_label_residue':residual,'classification':'explicit_reference_code_card'if is_reference else'unclassified_code_rectangle','source_file_modified':False};cards.append(rec);source_cards.append(rec);page_cards.append(rec)
  tables=page.find_tables(strategy='lines').tables if len(words)>4 else[];source_counts['tables']+=len(tables)
  for ti,table in enumerate(tables):
   extracted=table.extract();roles={};header_evidence={}
   for ri,row in enumerate(table.rows[:5]):
    for ci,b in enumerate(row.cells):
     if not b:continue
     label=reader.text(b);role=role_of(label)
     if role:roles[ci]=role;header_evidence[ci]={'row':ri,'text':label,'bbox':list(b)};header_labels[(role,ws(label))]+=1
   for ri,row in enumerate(table.rows):
    for ci,bbox in enumerate(row.cells):
     if not bbox:continue
     native=reader.text(bbox);old=extracted[ri][ci]or''
     if not native.strip()and not old.strip():continue
     centerx=(bbox[0]+bbox[2])/2;printed=[f['label']for f in footers if f['half']==('left'if centerx<page.rect.width/2 else'right')];rec={'source_id':source['id'],'page':number,'printed_page_labels':printed,'table':ti,'row':ri,'column':ci,'bbox':list(bbox),'role':roles.get(ci,'unknown'),'header_evidence':header_evidence.get(ci),'native_text':native,'table_extract_text':old,'codes':CODE_ANY.findall(native),'nonwhitespace_difference':re.sub(r'\s+','',native)!=re.sub(r'\s+','',old),'native_sha256':hashlib.sha256(native.encode()).hexdigest(),'coordinate_space':'display PDF after normalization'};cells.append(rec);source_cells.append(rec);table_records.append(rec)
  # Independent all-page code inventory, preserving every literal occurrence.
  used_search=collections.Counter()
  for ordinal,m in enumerate(CODE_ANY.finditer(text)):
   code=m.group();boxes=page.search_for(code);occurrence=used_search[code];used_search[code]+=1;box=boxes[occurrence]if occurrence<len(boxes)else None;possible_cells=[];possible_cards=[]
   if box:
    x,y=(box.x0+box.x1)/2,(box.y0+box.y1)/2;possible_cells=[c for c in table_records if in_box(c['bbox'],x,y)];possible_cards=[c for c in page_cards if in_box(c['bbox'],x,y)]
   role=min(possible_cells,key=lambda c:(c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]))['role']if possible_cells else'explicit_reference_code_card'if any(c['classification']=='explicit_reference_code_card'for c in possible_cards)else'outside_detected_cell';rec={'source_id':source['id'],'page':number,'code':code,'ordinal_in_page':ordinal,'search_occurrence':occurrence,'bbox':list(box)if box else None,'role':role,'native_context':text[max(0,m.start()-45):m.end()+100]};anchors.append(rec);source_anchors.append(rec)
  for item,ei,ev in by_page[number]:
   b=ev.get('bbox');native=reader.text(b)if b else text;literal=clean_text(ev.get('excerpt',''))in clean_text(native);candidates=[];codeboxes=page.search_for(item['code'])
   for cb in codeboxes:
    x,y=(cb.x0+cb.x1)/2,(cb.y0+cb.y1)/2
    if b and not in_box(b,x,y):continue
    candidates.extend(c for c in table_records if in_box(c['bbox'],x,y));candidates.extend({**c,'role':c['classification']}for c in page_cards if in_box(c['bbox'],x,y))
   container=min(candidates,key=lambda c:(c['bbox'][2]-c['bbox'][0])*(c['bbox'][3]-c['bbox'][1]))if candidates else None;role=container['role']if container else'unknown';r={'source_id':source['id'],'id':item['id'],'code':item['code'],'page':number,'method':ev.get('method'),'locator':ev.get('locator'),'bbox':b,'baseline_failure':item['id']in failureids[source['id']],'literal_cluster_region_match':literal,'source_column_role':role,'container_bbox':container['bbox']if container else None,'excerpt':ev.get('excerpt'),'native_region':native,'container_native_text':container['native_text']if container else None};checks.append(r);source_checks.append(r)
   if item['id']in failureids[source['id']]and role not in sampled:
    sampled.add(role);filename=f'{source["id"]}-p{number}-{role}.png';page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=fitz.Rect(b)if b else page.rect).save(PRIVATE/filename);r['private_visual']=str((PRIVATE/filename).relative_to(ROOT))
  pages.append({'source_id':source['id'],'page':number,'rect':list(page.rect),'printed_footer_labels':footers,'native_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'native_characters':len(text),'code_mentions':len(CODE_ANY.findall(text)),'tables':len(tables),'reference_cards':len(page_cards),'trace_expansions':len(physical_pseudo),'normalization':normalization})
  if number%50==0:print(json.dumps({'source_id':source['id'],'page':number,'pages':len(D),'cells':len(source_cells),'reference_cards':len(source_cards),'coded_checks':len(source_checks)}),flush=True)
 summary={'source_id':source['id'],'source_sha256':digest,'physical_pages':len(D),'cached_coded_items':cache['coded_items'],'cached_coded_evidence_fragments':len(source_checks),'baseline_failures':len(failureids[source['id']]),'baseline_failure_ids_matched':sum(c['baseline_failure']for c in source_checks),'literal_cluster_findings':sum(not c['literal_cluster_region_match']for c in source_checks),'source_roles_of_baseline_failures':dict(collections.Counter(c['source_column_role']for c in source_checks if c['baseline_failure'])),'all_source_code_mentions':len(source_anchors),'source_code_mentions_by_role':dict(collections.Counter(a['role']for a in source_anchors)),'detected_nonempty_cells':len(source_cells),'table_character_order_differences':sum(c['nonwhitespace_difference']for c in source_cells),'reference_cards':len(source_cards),'unclassified_reference_cards':sum(c['classification']!='explicit_reference_code_card'for c in source_cards),'counts':dict(source_counts),'headers':[{'role':r,'label':l,'count':n}for(r,l),n in header_labels.items()],'trace_expansions_by_font':[{'font':f,'unicode':u,'count':n}for(f,u),n in pseudo_fonts.items()],'source_ready':False};summaries.append(summary)
write('page-inventory.json',pages);write('physical-cell-inventory.json',cells);write('reference-card-inventory.json',cards);write('all-code-occurrences.json',anchors);write('all-cached-coded-fragment-checks.json',checks);write('summary.json',{'sources':summaries,'all_pages':len(pages),'baseline_failures':sum(len(v)for v in failureids.values()),'all_coded_fragments':len(checks),'production_modified':False,'originals_modified':False,'actor_type':'automated','scope':'Complete sources and all cached coded records, including baseline-negative cases. Literal match does not approve column role, exact code-text linkage, semantics, OCR or source completeness.'});print(json.dumps(summaries,ensure_ascii=False,indent=2))
