#!/usr/bin/env python3
"""Complete the short SC English AI document without changing 143 skill leaves.
Original PDF census precedes adapter loading. No OCR guesses or national codes.
"""
from pathlib import Path
import json,re,hashlib,collections,copy,sys
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
SID='sc-lingua-inglesa-ai';METHOD='sc-li-ai-full-document-v1.0.0';OUT=ROOT/'data/manifests/uncoded/sc-li-ai-complete-items.json'
def sha(v):return hashlib.sha256(v).hexdigest()
def norm(v):return re.sub(r'\s+',' ',v).strip()
def bbox(ws):return [min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]
def inside(ws,b):return [w for w in ws if b[0]-.15<=(w[0]+w[2])/2<=b[2]+.15 and b[1]-.15<=(w[1]+w[3])/2<=b[3]+.15]
def text(ws):
 lines=collections.defaultdict(list)
 for w in ws:lines[(w[5],w[6])].append(w)
 return norm(' '.join(' '.join(w[4] for w in sorted(row,key=lambda w:w[0])) for row in sorted(lines.values(),key=lambda row:(min(w[1] for w in row),min(w[0] for w in row)))))
def finalid(page,locator):return f'ca:{SID}:'+sha(f'{SID}|{page}|{locator}|uncoded|occurrence:0'.encode())[:20]
def structural_key(role,label,parent,scope):return 'sc-h-'+sha(json.dumps([SID,role,label,parent,scope],ensure_ascii=False,separators=(',',':')).encode())[:20]
def main():
 source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID);assert sha((ROOT/source['local_path']).read_bytes())==source['sha256'];doc=fitz.open(ROOT/source['local_path']);readers={pn:NativeGlyphText(p) for pn,p in enumerate(doc,1)};native={pn:r.text() for pn,r in readers.items()};blocks={}
 for pn,p in enumerate(doc,1):blocks[pn]=[(bi,b,norm(' '.join(''.join(s['text'] for s in l['spans']) for l in b['lines']))) for bi,b in enumerate(p.get_text('dict')['blocks']) if b.get('lines')]
 # Independent document census: original rightmost nonspanning cells and native
 # paragraph blocks, not IDs or counts taken from any adapter/cache.
 cells=[];skill_expected=[];axes=[];seen=set();axis_seen=set();year=None;structural_inventory={};root_key=structural_key('chapter','Língua Inglesa',None,['chapter','Língua Inglesa']);structural_inventory[root_key]={'role':'chapter','label':'Língua Inglesa','page':3}
 for pn in range(15,30):
  p=doc[pn-1];ws=p.get_text('words');m=re.search(r'ANOS\s+INICIAIS\s*[–-]\s*([1-5])\s*[º°]\s*ANO',native[pn],re.I)
  if m:year=int(m.group(1))
  assert year is not None
  label=f'{year}º ANO';year_key=structural_key('year_or_block',label,root_key,['year',label,root_key]);structural_inventory[year_key]={'role':'year_or_block','label':label,'page':{1:15,2:18,3:21,4:24,5:27}[year]}
  for ti,t in enumerate(p.find_tables().tables):
   tw=t.bbox[2]-t.bbox[0]
   for ri,row in enumerate(t.rows):
    valid=[(ci,b) for ci,b in enumerate(row.cells) if b]
    if not valid:continue
    ci,b=valid[-1];ws_cell=inside(ws,b);raw=text(ws_cell);cellkey=(pn,tuple(round(v,2) for v in b))
    if raw.startswith('EIXO ') and b[3]-b[1]<150 and cellkey not in axis_seen:
     axis_seen.add(cellkey);axes.append({'page':pn,'table':ti,'row':ri,'bbox':list(b),'text':raw,'year':year,'key':f'li-axis-p{pn}-t{ti}-r{ri}'})
    if b[2]-b[0]>.8*tw or b[0]<t.bbox[0]+.25*tw or not ws_cell or raw=='HABILIDADES' or cellkey in seen:continue
    seen.add(cellkey);native_blocks=collections.defaultdict(list)
    for w in ws_cell:native_blocks[w[5]].append(w)
    ordered=sorted(native_blocks.values(),key=lambda q:(min(w[1] for w in q),min(w[0] for w in q)));cell={'page':pn,'table':ti,'row':ri,'column':ci,'bbox':list(b),'native_word_count':len(ws_cell),'paragraph_count':len(ordered),'year':year};cells.append(cell)
    parent=year_key
    for left in sorted([o for j,o in enumerate(row.cells) if o and j!=ci and o[2]<=b[0]+1],key=lambda o:o[0]):
     title=text(inside(ws,left))
     if not (2<len(title)<=160) or re.search(r'[.;]',title) or re.match(r'^(?:[→●•-]|Identificar|Compreender|Investigar|Selecionar|Reconhecer|Utilizar|Levantar)',title,re.I):continue
     key=structural_key('row_context',title,parent,['row',pn,[round(v,1) for v in left],parent]);structural_inventory[key]={'role':'row_context','label':title,'page':pn,'bbox':list(left)};parent=key
    for pi,part in enumerate(ordered):
     loc=f'sc-english-skill-table:{ti}/row:{ri}/column:{ci}/paragraph:{pi}';skill_expected.append({'id':finalid(pn,loc),'page':pn,'locator':loc,'bbox':bbox(part),'source_text':text(part),'word_count':len(part),'year':year})
 assert len(cells)==78 and len(skill_expected)==143 and len(axes)==25 and len(structural_inventory)==141
 original={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'Original31PDFpages: native content inventory, rightmost nonspanning source cells and native paragraph blocks, source year headings and25EIXO bands; no adapter/cache IDs consulted','physical_pages':len(doc),'nonempty_native_pages':[p for p,t in native.items() if t.strip()],'blank_native_pages':[p for p,t in native.items() if not t.strip()],'page_native_token_counts':{p:len(ingest.normalize(t).split()) for p,t in native.items()},'source_learning_cells':cells,'source_skill_paragraphs':skill_expected,'source_axis_occurrences':axes,'source_competence_ordinals':[1,2,3,4,5,6],'source_axis_definitions':['ORALIDADE','LEITURA','ESCRITA','CONHECIMENTOS LINGUÍSTICOS','DIMENSÃO INTERCULTURAL'],'independently_derived_original_structural_keys':structural_inventory}
 (ROOT/'docs/evidence/source-audit-sc-li-complete/independent-source-inventory.json').write_text(json.dumps(original,ensure_ascii=False,indent=2)+'\n')
 baseline_path=ROOT/'data/manifests/uncoded/sc-hierarchy-sc-lingua-inglesa-ai.json';baseline=json.loads(baseline_path.read_text());items=copy.deepcopy(baseline['items']);leaves=[i for i in items if not i.get('key')];assert len(leaves)==143;extras=[];bykey={i['key']:i for i in items if i.get('key')};chapter=next(i for i in items if i.get('source_context',{}).get('structural_role')=='chapter');year_nodes={i['positions'][0]['years'][0]:i for i in items if i.get('source_context',{}).get('structural_role')=='year_or_block'}
 pos={'stage':'EF','component':'Língua Inglesa','area':'Linguagens','years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_source_document_heading','position_note':'Componente/área literais; anos somente nos organizadores que os explicitam.'}
 def add(key,kind,pn,raw,box,parent=None,position=None,role=None,number=None):
  loc='sc-li-complete:'+key;record={'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':norm(raw),'title':norm(raw).split(':',1)[0] if role=='axis_occurrence' else norm(raw),'page':pn,'locator':loc,'positions':[copy.deepcopy(position or pos)],'evidence':[{'source_id':SID,'page':pn,'printed_page':None,'section':'Língua Inglesa – Anos Iniciais','excerpt':norm(raw),'bbox':list(box),'locator':loc,'method':METHOD,'coordinate_space':'source_page_display_coordinates'}],'source_context':{'official_code_absent':True,'structural_role':role,'not_an_invented_national_code':True},'extraction_method':METHOD,'extraction_revision':METHOD,'actor_type':'automated','actor_id':'agent:data_central_south','technical_validation_status':'literal_original_source_and_geometry_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
  if number is not None:record['source_number']=number
  extras.append(record);return key
 # The cover has a real text-layer defect, resolved by actual raster OCR and
 # inspected against both the original render and its native titlepage3.
 from ocr import ocr_page
 p1=doc[0];ocr=ocr_page(p1,source,1);assert norm(ocr['text'])=='Currículo Base do Ensino Fundamental do Território Catarinense Língua Inglesa - Anos Iniciais';proof={**ocr,'artifact_sha256':source['sha256'],'page':1,'source_id':SID};proof_path=ROOT/'data/manifests/uncoded/proofs/sc-li-cover-ocr.json';proof_path.parent.mkdir(parents=True,exist_ok=True);proof_path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');year_words=[w for w in p1.get_text('words') if w[4]=='2026'];assert len(year_words)==1;title_box=[min(w['x0'] for w in ocr['words']),min(w['top'] for w in ocr['words']),max(w['x1'] for w in ocr['words']),max(w['bottom'] for w in ocr['words'])];cover=add('li-cover','secao_normativa',1,'2026 '+ocr['text'],bbox(p1.get_text('words')),role='cover_verified_native_year_and_real_ocr_title');extras[-1]['evidence']=[{**extras[-1]['evidence'][0],'excerpt':'2026','bbox':list(year_words[0][:4])},{**extras[-1]['evidence'][0],'excerpt':norm(ocr['text']),'bbox':title_box,'ocr_reference_path':str(proof_path.relative_to(ROOT)),'ocr_reference_sha256':sha(proof_path.read_bytes()),'method':ocr['method']}];extras[-1]['source_context'].update(original_native_cover_text=native[1],source_typography_note='Native cover layer ends Anos Inici. Actual Tesseract raster OCR recovers visible Anos Iniciais, crosschecked with native titlepage3 and original render; no dictionary completion.',visual_evidence_path='docs/evidence/source-audit-sc/li-ai-whole-document-preamble.png',native_title_crosscheck_page=3)
 area=add('li-area','estrutura_curricular',11,native[11],bbox(doc[10].get_text('words')),cover,role='explicit_area_divider');chapter['parent_key']=cover;chapter['source_context']['structural_role']='frontmatter_title';formal=add('li-chapter-1','secao_normativa',12,blocks[12][0][2],blocks[12][0][1]['bbox'],area,role='numbered_chapter',number='1')
 for n in year_nodes.values():n['parent_key']=formal
 sections={}
 for pn,bi,key,num in [(12,1,'li-section-1-1','1.1'),(12,4,'li-section-1-2','1.2'),(13,6,'li-section-1-3','1.3')]:
  b=next(b for b in blocks[pn] if b[0]==bi);sections[num]=add(key,'secao_normativa',pn,b[2],b[1]['bbox'],formal,role='explicit_numbered_section',number=num)
 for pn,bi,parent in [(12,2,sections['1.1']),(12,5,sections['1.2']),(13,0,sections['1.2']),(14,3,sections['1.3'])]:
  b=next(b for b in blocks[pn] if b[0]==bi);add(f'li-foundation-p{pn}-b{bi}','secao_normativa',pn,b[2],b[1]['bbox'],parent,role='source_foundation_paragraph')
 for bi in range(1,6):
  b=next(b for b in blocks[13] if b[0]==bi);add(f'li-axis-definition-{bi}','estrutura_curricular',13,b[2],b[1]['bbox'],sections['1.2'],role='axis_definition')
 for num,(pn,bi) in enumerate([(13,7),(13,8),(13,9),(14,0),(14,1),(14,2)],1):
  b=next(b for b in blocks[pn] if b[0]==bi);assert re.match(rf'^{num}\.\s',b[2]);add(f'li-competence-{num}','competencia_especifica',pn,b[2],b[1]['bbox'],sections['1.3'],role='explicit_numbered_subject_competence',number=str(num))
 b=next(b for b in blocks[14] if b[0]==5);refs=add('li-references','secao_normativa',14,b[2],b[1]['bbox'],formal,role='bibliographic_section')
 for bi in [6,7]:
  b=next(b for b in blocks[14] if b[0]==bi);add(f'li-reference-{bi}','secao_normativa',14,b[2],b[1]['bbox'],refs,role='bibliographic_reference')
 for pn in [4,5,6,7,9]:add(f'li-frontmatter-p{pn}','secao_normativa',pn,native[pn],bbox(doc[pn-1].get_text('words')),cover,role='authorship_or_source_index')
 for axis in axes:
  yp={**pos,'years':[axis['year']],'year_label':f'{axis["year"]}º ANO'};add(axis['key'],'estrutura_curricular',axis['page'],axis['text'],axis['bbox'],year_nodes[axis['year']]['key'],position=yp,role='axis_occurrence')
 for item in items:
  if item.get('source_context',{}).get('structural_role')!='row_context':continue
  y=item['positions'][0]['years'][0];pn=item['evidence'][0]['page'];top=item['evidence'][0]['bbox'][1];prior=[a for a in axes if a['year']==y and (a['page']<pn or a['page']==pn and a['bbox'][1]<top)]
  assert prior,(pn,top,item['text']);item['parent_key']=max(prior,key=lambda a:(a['page'],a['bbox'][1]))['key']
 page_links=[];page_expected=[]
 for pn,raw in native.items():
  if len(raw.strip())<100:continue
  parent=year_nodes[next(a['year'] for a in axes if a['page']<=pn and pn<({1:18,2:21,3:24,4:27,5:30}[a['year']]))]['key'] if 15<=pn<=29 else formal if pn>=12 else cover
  page_links.append({'page':pn,'locator':'page-section','code':None,'parent_key':parent,'evidence':{'page':pn,'section':'Explicit document chapter/year organizer','excerpt':'Língua Inglesa – Anos Iniciais'}});page_expected.append(finalid(pn,'page-section'))
 wrapper={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':METHOD,'baseline_adapter_sha256':sha(baseline_path.read_bytes()),'items':items+extras,'item_parent_links':page_links};OUT.write_text(json.dumps(wrapper,ensure_ascii=False,indent=2)+'\n')
 report={'actor_type':'automated','actor_id':'agent:data_central_south','method':METHOD,'source_id':SID,'artifact_sha256':source['sha256'],'baseline_sha256':sha(baseline_path.read_bytes()),'output_path':str(OUT.relative_to(ROOT)),'output_sha256':sha(OUT.read_bytes()),'baseline_records':len(items),'original_skill_leaves_unchanged':[(i['text'],i['evidence'],i['positions'],i['locator']) for i in leaves]==[(i['text'],i['evidence'],i['positions'],i['locator']) for i in baseline['items'] if not i.get('key')],'new_records':len(extras),'new_kinds':dict(collections.Counter(i['kind'] for i in extras)),'source_skill_paragraph_count':len(skill_expected),'source_learning_cells':len(cells),'source_axis_occurrence_count':len(axes),'source_specific_competence_count':6,'source_axis_definition_count':5,'expected_skill_ids':[x['id'] for x in skill_expected],'expected_page_section_ids':page_expected,'expected_new_ids':[f'ca:{SID}:section:{i["key"]}' for i in extras],'blank_pages':[p for p,t in native.items() if not t.strip()],'pending':'Actual importer/finalizer, whole-page native token proof, source-cell word accounting and full sidecar emission are separate next verification steps; no UF readiness.'};(ROOT/'docs/evidence/source-audit-sc-li-complete/build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if not k.startswith('expected_')},ensure_ascii=False))
if __name__=='__main__':main()
