#!/usr/bin/env python3
"""Typed uncoded EI organizer columns. Objective column is excluded and separately mapped.
Exact repeated rights within identical field+age scope are retained as occurrences,
not manufactured as new rights. Guidance/proposals keep whole column/page grain.
"""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text,CODE_ANY,normalize
SID='mg-crmg-eief-atualizada';source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']==SID);P=ROOT/source['local_path'];h=hashlib.sha256()
with P.open('rb')as f:
 for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
assert h.hexdigest()==source['sha256'];SHA=h.hexdigest();map_path=OUT/'mg-ei-organizers-column-role-map-v1.json';mapping=json.loads(map_path.read_text());assert mapping['source_sha256']==SHA and mapping['mapped_table_pages']==75 and not mapping['findings'];D=fitz.open(P);data=[];checks=[];denominator=[];findings=[];label=re.compile(r'^\s*(?:[•·\uf0b7]\s*)?(CONVIVER|BRINCAR|PARTICIPAR|EXPLORAR|EXPRESSAR|CONHECER-SE)\b');LABELS={'CONVIVER','BRINCAR','PARTICIPAR','EXPLORAR','EXPRESSAR','CONHECER-SE'}
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def ws(t):return' '.join(t.split())
_trace_page_number=None
_trace_page_data=None
def original_trace_text(page,bbox):
 global _trace_page_number,_trace_page_data
 if _trace_page_number!=page.number:
  _trace_page_number=page.number;_trace_page_data=page.get_texttrace()
 tokens={}
 for span in _trace_page_data:
  if span.get('dir',(1,0))[0]<.9:continue
  by_baseline={}
  for ch in span['chars']:
   box=ch[3];x,y=(box[0]+box[2])/2,(box[1]+box[3])/2
   if ch[0]>=0 and bbox[0]<=x<bbox[2]and bbox[1]<=y<bbox[3]:by_baseline.setdefault(round(ch[2][1],1),[]).append(ch)
  # A rendering span can contain many physical lines. Keep original char order
  # within its baseline, then arrange original fragments by physical x/y.
  for y,chars in by_baseline.items():
   text=''.join(chr(c[0])for c in chars);x=min(c[2][0]for c in chars);tokens.setdefault(y,[]).append((x,text))
 # Font fragments within one printed line can differ by a fraction of a point
 # in baseline (notably CONHECER-/SE). Cluster only physical baselines <=.6pt;
 # preserve every original character and sort their original fragments by x.
 physical=[]
 for y,parts in sorted(tokens.items()):
  if physical and abs(y-physical[-1][0])<=.6:physical[-1][1].extend(parts)
  else:physical.append([y,list(parts)])
 return'\n'.join(' '.join(t for _,t in sorted(parts))for _,parts in physical)
def source_rows(reader,pn,bbox):
 rows=[]
 for ordinal,clusters in enumerate(reader.lines):
  selected=[c for c in clusters if bbox[0]<=(c['box'][0]+c['box'][2])/2<bbox[2]and bbox[1]<=(c['box'][1]+c['box'][3])/2<bbox[3]]
  if not selected:continue
  text=''.join(c['text']for c in selected)
  if not text.strip():continue
  boxes=[c['box']for c in selected];b=[min(x[0]for x in boxes),min(x[1]for x in boxes),max(x[2]for x in boxes),max(x[3]for x in boxes)];rows.append({'page':pn,'source_line':ordinal,'text':text,'bbox':b})
 return sorted(rows,key=lambda r:(round(r['bbox'][1],0),r['bbox'][0]))
for m in mapping['pages']:
 pn=m['page'];page=D[pn-1];normalization=normalize_native_page(page);reader=NativeGlyphText(page);columns={};pagechecks=[];empty=[]
 # All source-only body columns are read before any item. Objective text is kept
 # only in the role census for the coded owner; no code body is re-registered here.
 for role,col in m['columns'].items():
  rows=source_rows(reader,pn,col['body_bbox']);text=clean_text(' '.join(r['text']for r in rows));trace=original_trace_text(page,col['body_bbox']);columns[role]={'rows':rows,'text':text,'raw_text':'\n'.join(r['text']for r in rows),'bbox':col['body_bbox'],'source_header':col['header_literal'],'source_header_bbox':col['header_bbox']}
  if not rows:empty.append(role)
  if role!='objectives':
   for row in rows:
    clip=page.get_text('text',clip=fitz.Rect(row['bbox'])+(-.15,-.15,.15,.15),sort=False);glyph=reader.text(row['bbox']);render=original_trace_text(page,row['bbox']);c={'page':pn,'column':role,'source_line':row['source_line'],'native_glyph':canon(clean_text(row['text']))in canon(glyph),'native_clip':canon(clean_text(row['text']))in canon(clip),'render_trace':canon(clean_text(row['text']))in canon(render)};pagechecks.append(c)
  columns[role]['full_column_original_trace_matches']=canon(text)==canon(trace)
 rights=columns['rights'];anchors=[i for i,r in enumerate(rights['rows'])if label.match(r['text'])];# Rendering spans can split a bold uppercase label into several fragments.
 # Count the six literally printed uppercase names across original glyphs after
 # whitespace-only layout collapse; no spelling/case/word replacement is used.
 original_labels=re.findall(r'CONVIVER|BRINCAR|PARTICIPAR|EXPLORAR|EXPRESSAR|CONHECER-SE',re.sub(r'\s','',original_trace_text(page,rights['bbox'])))
 if rights['rows']and(set(original_labels)!=LABELS or len(original_labels)!=6):findings.append({'page':pn,'issue':'original_rights_label_count_or_names_not_six','labels':original_labels})
 if rights['rows']and len(anchors)!=len(original_labels):findings.append({'page':pn,'issue':'native_and_independent_trace_right_anchor_count_diff','native':len(anchors),'trace':len(original_labels)})
 records=[]
 for n,start in enumerate(anchors):
  end=anchors[n+1]if n+1<len(anchors)else len(rights['rows']);rows=rights['rows'][start:end];records.append({'label':label.match(rows[0]['text'])[1],'rows':rows,'text':clean_text(' '.join(r['text']for r in rows))})
 captions=[];folio=None;book_header=[]
 all_original_rows=source_rows(reader,pn,[0,0,page.rect.width,page.rect.height]);field_caption=next(r for r in all_original_rows if'CAMPO DE EXPERIÊNCIAS:'in r['text']);age_caption=next(r for r in all_original_rows if'FAIXA ETÁRIA:'in r['text'])
 for row in all_original_rows:
  # Include wrapped continuation lines of the field caption, not just its prefix.
  if field_caption['bbox'][1]-.3<=row['bbox'][1] and row['bbox'][3]<=age_caption['bbox'][3]+.3:captions.append(row)
  if row['bbox'][3]<55:
   if row['text'].strip().isdigit():folio=row['text'].strip()
   elif'Currículo Referência de Minas Gerais'in row['text']:book_header.append(row)
 denominator.append({'page':pn,'field_key':m['field_key'],'age_key':m['age_key'],'field':m['field_literal'],'age':m['age_header_literal'],'physical_right_paragraphs_from_trace':len(original_labels),'labels_from_trace_whitespace_only_layout_collapse':original_labels,'empty_original_columns':empty,'column_source_glyph_line_counts':{role:len(col['rows'])for role,col in columns.items()},'full_column_original_trace_matches':{role:col['full_column_original_trace_matches']for role,col in columns.items()}});checks+=pagechecks;data.append({'map':m,'columns':columns,'rights':records,'captions':captions,'folio':folio,'book_header':book_header,'normalization':normalization})
failures=[c for c in checks if not c['native_glyph']or not(c['native_clip']or c['render_trace'])];(OUT/'mg-ei-organizers-v1-source-denominator.json').write_text(json.dumps({'source_id':SID,'source_sha256':SHA,'method':'All75original role-mapped pages read before output. Independent texttrace labels count actual nonempty rights panels; blank continuation columns remain blank. Exact field/age/text grouping happens only after this physical occurrence census.','physical_table_pages':75,'physical_right_paragraph_occurrences':sum(r['physical_right_paragraphs_from_trace']for r in denominator),'pages':denominator,'findings':findings,'literal_failures':failures,'source_ready':False},ensure_ascii=False,indent=2)+'\n')
if findings or failures:raise ValueError(f'Original census findings={len(findings)}, literal failures={len(failures)}; no candidate written')
items=[];bykey={};rights_groups={};compressed_evidence_records=0
def evidence(row,d):return{'source_id':SID,'page':row['page'],'printed_page':d['folio'],'section':d['map']['field_literal']+' / '+d['map']['age_header_literal'],'excerpt':clean_text(row['text']),'locator':f'native-line:{row["source_line"]}','bbox':row['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':d['normalization'],'method':'pymupdf-native-glyph-cluster-v1'}
def positions(d,age=True):return[{'stage':'EI','component':d['map']['field_literal'],'area':None,'years':None,'year_label':None,'age_group':d['map']['age_header_literal']if age else None,'period':None,'position_origin':'explicit_original_field_and_age_table_caption','position_note':'Literal campo de experiências and age caption. No individual school year or discipline inferred.'}]
def add(key,kind,rows,parent,d,context,age=True):
 global compressed_evidence_records
 boxes=[r['bbox']for r in rows];region=[min(b[0]for b in boxes),min(b[1]for b in boxes),max(b[2]for b in boxes),max(b[3]for b in boxes)];region_text=NativeGlyphText(D[rows[0]['page']-1]).text(region);canonical=clean_text(' '.join(r['text']for r in rows));evidence_rows=rows
 if len(rows)>1 and normalize(canonical)==normalize(region_text)and canon(canonical)==canon(region_text):
  evidence_rows=[{'page':rows[0]['page'],'source_line':rows[0]['source_line'],'text':canonical,'bbox':region}];compressed_evidence_records+=1
 obj={'source_id':SID,'artifact_sha256':SHA,'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(r['text']for r in rows)),'page':rows[0]['page'],'locator':'mg-ei-organizers-v1/'+key,'positions':positions(d,age),'evidence':[evidence(r,d)for r in evidence_rows],'source_context':context,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-EI-original-role-columns-and-right-occurrences-v1'};assert'\x00'not in obj['text'];items.append(obj);bykey[key]=obj;return obj
for d in data:
 m=d['map'];field_rows=[r for r in d['captions']if'FAIXA ETÁRIA:'not in r['text']];age_rows=[r for r in d['captions']if'FAIXA ETÁRIA:'in r['text']];assert field_rows and age_rows
 if m['field_key']not in bykey:add(m['field_key'],'campo_experiencias',field_rows,None,d,{'source_role':'Original campo de experiências caption','learning_objective_claim':False,'classification':'documentary_context','caption_occurrences':[]},False)
 if m['age_key']not in bykey:add(m['age_key'],'grupo_etario',age_rows,m['field_key'],d,{'source_role':'Original field/age organizer scope','learning_objective_claim':False,'classification':'documentary_context','page_scope_occurrences':[]})
 occurrence={'page':m['page'],'field_caption':[{'text':r['text'],'bbox':r['bbox']}for r in field_rows],'age_caption':[{'text':r['text'],'bbox':r['bbox']}for r in age_rows],'printed_folio_literal':d['folio'],'book_header':[{'text':r['text'],'bbox':r['bbox']}for r in d['book_header']],'column_headers':{role:{'text':col['source_header'],'bbox':col['source_header_bbox'],'body_bbox':col['bbox'],'empty_original_column':not bool(col['rows'])}for role,col in d['columns'].items()}}
 bykey[m['field_key']]['source_context']['caption_occurrences'].append({'page':m['page'],'evidence':occurrence['field_caption']});bykey[m['age_key']]['source_context']['page_scope_occurrences'].append(occurrence)
 for right in d['rights']:
  identity=(m['field_literal'],m['age_header_literal'],right['label'],canon(right['text']));key='mg-ei-organizer:right:'+hashlib.sha256('|'.join(identity).encode()).hexdigest()[:24]
  if identity not in rights_groups:
   node=add(key,'direito_aprendizagem',right['rows'],m['age_key'],d,{'source_role':'Explicit source learning-right paragraph in this field/age scope','classification':'learning_right','learning_objective_claim':False,'source_right_label_literal':right['label'],'identity_basis':'Exact original text after permitted whitespace/soft-linewrap normalization, plus literal field+age captions. Regular hyphens, spelling, case and punctuation are retained. No semantic similarity merge.','physical_occurrences':[]});node['source_right_label']=right['label'];rights_groups[identity]=node
  node=rights_groups[identity];boxes=[r['bbox']for r in right['rows']];node['source_context']['physical_occurrences'].append({'page':m['page'],'locator':'original-right-panel/'+right['label'],'paragraph_bbox':[min(b[0]for b in boxes),min(b[1]for b in boxes),max(b[2]for b in boxes),max(b[3]for b in boxes)],'original_wording_sha256_after_declared_layout_normalization':hashlib.sha256(canon(right['text']).encode()).hexdigest(),'source_line_locators':[r['source_line']for r in right['rows']],'canonical_text_matches_primary':True})
 for role,kind in[('didactic','orientacao_didatica'),('experiences','experiencia_sugerida')]:
  col=d['columns'][role]
  if not col['rows']:continue
  add(f'mg-ei-organizer:{role}:p{m["page"]}',kind,col['rows'],m['age_key'],d,{'source_role':col['source_header'],'classification':'documentary_context'if role=='didactic'else'pedagogical_experience_proposal','learning_objective_claim':False,'grain':'Entire original physical column/page container, with multiple original paragraphs retained together. Not an invented atomic activity or student skill.','raw_original_column_text':col['raw_text'],'original_body_bbox':col['bbox'],'code_like_mentions_diagnostic_only':list(dict.fromkeys(match[0]for match in CODE_ANY.finditer(col['raw_text']))),'code_reference_scope':'Tokens in teacher guidance/proposals are context; no learning definition, equivalence or national correspondence inferred.','objective_column_excluded':True,'paired_objective_documentary_scope':{'header_literal':d['columns']['objectives']['source_header'],'body_bbox':d['columns']['objectives']['bbox'],'scope':'Original adjacent column in the same field/age table. No one-to-one activity/goal equivalence inferred from this page container.'}})
assert len({i['key']for i in items})==len(items);assert all(not i.get('parent_key')or i['parent_key']in bykey for i in items);path=ROOT/'data/manifests/uncoded/mg-ei-organizers-v1-items.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
if path.exists():generated=json.loads(path.read_text())['generated_at']
a={'source_id':SID,'artifact_sha256':SHA,'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','method':'mg-EI-original-role-columns-and-right-occurrences-v1','scope':'Uncoded roles only in75EI organizer pages. Objective column excluded for coded owner. Field/age/right text exact repeats retain all physical occurrences; no semantic equivalence or student-learning claim. Guidance/proposal containers preserve whole original columns/pages. All other normative parts remain included and unreconciled.','original_role_map_path':str(map_path.relative_to(ROOT)),'original_role_map_sha256':hashlib.sha256(map_path.read_bytes()).hexdigest(),'items':items};serialized=json.dumps(a,ensure_ascii=False,separators=(',',':')).encode();assert len(serialized)<4*1024*1024,'Necessary sidecar exceeds4MiB; coordinate before writing';path.write_bytes(serialized+b'\n');report={'source_id':SID,'source_sha256':SHA,'sidecar_path':str(path.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sidecar_bytes':path.stat().st_size,'physical_table_pages':75,'physical_right_paragraph_occurrences':sum(r['physical_right_paragraphs_from_trace']for r in denominator),'right_records_after_exact_scope_text_grouping':len(rights_groups),'nodes':len(items),'kinds':dict(collections.Counter(i['kind']for i in items)),'checked_uncoded_source_fragments':len(checks),'exact_region_evidence_compressed_records':compressed_evidence_records,'native_clip_mismatches_with_independent_trace_resolution':sum(not c['native_clip']and c['render_trace']for c in checks),'literal_failures':failures,'original_empty_columns':[{'page':r['page'],'roles':r['empty_original_columns']}for r in denominator if r['empty_original_columns']],'source_manifest_edited':False,'already_delivered_pins_modified':False,'source_ready':False};(OUT/'mg-ei-organizers-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'mg-ei-organizers-v1-fragment-checks.json').write_text(json.dumps(checks,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps(report,ensure_ascii=False))
