#!/usr/bin/env python3
"""Authoritative MS EI objective/action columns, without generic partial codes.

All primary cells are inventoried before current extraction is consulted. The
full printed local code and original valid objective ID are retained. This is
not a whole-Source reconciliation or a new national-code relationship.
"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from native_glyphs import NativeGlyphText
SID='ms-cr-eief-v110';OUT=ROOT/'data/manifests/uncoded/ms-ei-table-items.json';EVID=ROOT/'docs/evidence/source-audit-ms-ei'
CODE=r'MS\.\s*EI\d{2}(?:EO|CG|TS|EF|ET)\d{2}\.\s*[scadn]\.\s*\d{2}'
def sha(v):return hashlib.sha256(v).hexdigest()
def clean(v):return ingest.clean_text(v)
def token(code):return re.sub(r'\s+','',code)
def main():
 EVID.mkdir(exist_ok=True);source=copy.deepcopy(next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID));pdf=ROOT/source['local_path'];assert sha(pdf.read_bytes())==source['sha256'];doc=fitz.open(pdf);proposal=json.loads((ROOT/'docs/evidence/source-audit-central-south/ms-ei-age-context-proposal.json').read_text());assert proposal['artifact_sha256']==source['sha256'];contexts=proposal['position_contexts'];records=[];inventory=[];field_nodes=set();all_goals=[];words_checks=[]
 def ev(pn,text,box,loc,role=None):return {'source_id':SID,'artifact_sha256':source['sha256'],'page':pn,'printed_page':str(pn),'section':'Educação Infantil – objetivos de aprendizagem e desenvolvimento / ações didáticas','excerpt':text,'bbox':list(box),'locator':loc,'method':'pymupdf-native-glyph-cluster-v1','coordinate_space':'source_page_display_coordinates',**({'evidence_role':role} if role else {})}
 def node(key,kind,text,pn,box,parent,pos,role):
  loc='ms-ei-structure:'+key;records.append({'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':text,'title':text if kind!='orientacao_metodologica' else 'AÇÕES DIDÁTICAS','page':pn,'locator':loc,'positions':[copy.deepcopy(pos)],'evidence':[ev(pn,text,box,loc)],'source_context':{'structural_role':role,'official_code_absent':True},'extraction_method':'ms-ei-two-columns-v1.0.0','actor_type':'automated','actor_id':'agent:data_central_south','pedagogical_review_status':'not_reviewed'})
 for context in contexts:
  pn=context['page'];page=doc[pn-1];reader=NativeGlyphText(page);field=context['evidence']['component_heading_evidence'];fi=int(field['section'].split('.')[-1]);fieldkey=f'ms-ei-field-{fi}';groupkey=f'ms-ei-field-{fi}-age-table-p{pn}';pos={k:context.get(k) for k in ['stage','component','area','years','year_label','age_group','period']};pos.update(position_origin='explicit_source_age_and_field_headers',position_evidence=context['evidence'])
  if fieldkey not in field_nodes:
   fp=doc[field['page']-1];boxes=fp.search_for(field['excerpt']);assert boxes;box=[min(r.x0 for r in boxes),min(r.y0 for r in boxes),max(r.x1 for r in boxes),max(r.y1 for r in boxes)];fieldpos={**pos,'age_group':None};node(fieldkey,'campo_experiencia',field['excerpt'],field['page'],box,None,fieldpos,'literal_numbered_field_heading');field_nodes.add(fieldkey)
  node(groupkey,'grupo_etario',context['age_group'],pn,context['evidence']['bbox'],fieldkey,pos,'literal_single_age_table_header')
  seen=set();goals=[];allcells=[]
  for ti,table in enumerate(page.find_tables().tables):
   for ri,row in enumerate(table.rows):
    for ci,box in enumerate(row.cells):
     if not box or tuple(round(v,3) for v in box) in seen:continue
     seen.add(tuple(round(v,3) for v in box));raw=clean(reader.text(box));allcells.append({'table':ti,'row':ri,'column':ci,'bbox':list(box),'text':raw})
     match=re.match(r'^\(\s*('+CODE+r')\s*\)\s*(.+)$',raw)
     if not match:continue
     code,body=match.groups();loc=f'table:{ti}/row:{ri}/cell:{ci}';record={'source_id':SID,'artifact_sha256':source['sha256'],'code':code,'code_original':code,'official_code_present_in_source':True,'kind':'objetivo_aprendizagem','text':body,'page':pn,'locator':loc,'parent_key':groupkey,'positions':[copy.deepcopy(pos)],'evidence':[ev(pn,code,box,loc,'code_locator'),ev(pn,body,box,loc)],'source_context':{'document_part':'Educação Infantil','source_declared_role':'OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO','source_field_header':field['excerpt'],'source_age_header':context['age_group'],'physical_table':ti,'physical_row':ri,'physical_column':ci,'full_local_code_preserved':True,'no_national_equivalence_inferred':True},'extraction_method':'ms-ei-two-columns-v1.0.0','extraction_revision':'ms-ei-two-columns-v1.0.0','actor_type':'automated','actor_id':'agent:data_central_south','pedagogical_review_status':'not_reviewed'};goals.append(record);records.append(record)
  printed=[clean(m[1]) for m in re.finditer(r'\(\s*('+CODE+r')\s*\)',page.get_text())];assert collections.Counter(token(c) for c in printed)==collections.Counter(token(i['code']) for i in goals),(pn,len(printed),len(goals));assert goals
  left=min(e['evidence'][0]['bbox'][0] for e in goals);divider=max(e['evidence'][0]['bbox'][2] for e in goals);top=min(e['evidence'][0]['bbox'][1] for e in goals);bottom=max(e['evidence'][0]['bbox'][3] for e in goals)
  raw_words=[w for w in page.get_text('words') if left-.1<=(w[0]+w[2])/2<=divider+.1 and top-.1<=(w[1]+w[3])/2<=bottom+.1];missing=[];multiple=[]
  for w in raw_words:
   matched=[g for g in goals if g['evidence'][0]['bbox'][0]-.1<=(w[0]+w[2])/2<=g['evidence'][0]['bbox'][2]+.1 and g['evidence'][0]['bbox'][1]-.1<=(w[1]+w[3])/2<=g['evidence'][0]['bbox'][3]+.1]
   if not matched:missing.append(w[4])
   if len(matched)>1:multiple.append(w[4])
  assert not missing and not multiple,(pn,missing,multiple)
  # The RHS is a merged age/field-level guidance cell, NOT a per-goal mapping.
  actions=[c for c in allcells if c['bbox'][0]>=divider-.5 and c['bbox'][2]-c['bbox'][0]>150 and c['bbox'][1]>=top-.5 and len(c['text'])>40]
  assert actions,(pn,'no action guidance');action_boxes=[]
  for n,c in enumerate(actions):node(f'ms-ei-actions-p{pn}-cell-{n}','orientacao_metodologica',c['text'],pn,c['bbox'],groupkey,pos,'source_merged_actions_column_for_entire_age_field');action_boxes.append(c['bbox'])
  inventory.append({'page':pn,'age_header':context['age_group'],'field_heading':field,'printed_codes':printed,'source_objective_cells':[{'code':g['code'],'text':g['text'],'locator':g['locator'],'bbox':g['evidence'][0]['bbox']} for g in goals],'actions_regions':actions,'whole_left_word_count':len(raw_words),'unaccounted_words':missing,'multiply_accounted_words':multiple});all_goals+=goals
 assert len(all_goals)==162 and len(field_nodes)==5,(len(all_goals),len(field_nodes))
 # Persist original-only denominator BEFORE loading the previous extraction.
 (EVID/'independent-primary-table-inventory.json').write_text(json.dumps({'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'All15originaltableheaders,5originalfieldheadings,162completeprintedMSlocalcodes and closed objective/action source cells, plus whole-left-column native-word accounting; no prior extracted ID count used.','pages':inventory,'objectives':162},ensure_ascii=False,indent=2)+'\n')
 candidate=copy.deepcopy(source);candidate['extraction_pages']=sorted({c['page'] for c in contexts}|{c['evidence']['component_heading_evidence']['page'] for c in contexts});ow,oc=ingest.write_json,ingest.write_extraction_cache;ingest.write_json=lambda *a:None;ingest.write_extraction_cache=lambda *a:None;ingest.log=lambda *a,**k:None
 try:oldex=ingest.extract_pdf(candidate,pdf,force=True)
 finally:ingest.write_json,ingest.write_extraction_cache=ow,oc
 old=ingest.finalize_items(copy.deepcopy(oldex['items']),[source]);oldcoded=[i for i in old if i.get('code')];raw_primary={(g['page'],g['locator'],g['code']):g for g in all_goals};old_valid={(i['evidence'][0]['page'],i['evidence'][0]['locator'],i['code']):i for i in oldcoded if i['code'].startswith('MS')};assert set(raw_primary)==set(old_valid),(set(raw_primary)-set(old_valid),set(old_valid)-set(raw_primary));assert all(g['text']==old_valid[k]['text'] for k,g in raw_primary.items())
 OUT.write_text(json.dumps({'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','method':'Original2columncodedEIrows, exactlocalcode/ID/body retained, explicitheaderpositions and merged pedagogical actions kept at age/field level.','items':records},ensure_ascii=False,indent=2)+'\n')
 candidate=copy.deepcopy(source);candidate['uncoded_items_path']=str(OUT.relative_to(ROOT));candidate.setdefault('adapter_authority',{})['coded_learning_ranges']=[[80,82],[84,86],[88,90],[92,94],[96,98]]
 imported=ingest.source_uncoded_items([candidate],{SID:oldex});final=ingest.finalize_items(imported,[candidate]);ingest.attach_hierarchy(final,[candidate]);finalgoals=[i for i in final if i.get('code')];old_ids={i['id'] for i in oldcoded};new_ids={i['id'] for i in finalgoals};preserved={i['id']:i for i in old_valid.values()};assert new_ids==set(preserved) and len(new_ids)==162;assert all(i['text']==preserved[i['id']]['text'] and i['code']==preserved[i['id']]['code'] for i in finalgoals)
 new_by_page_text={(i['evidence'][0]['page'],i['text']):i for i in finalgoals};supersessions=[]
 for i in oldcoded:
  if i['id'] in new_ids:continue
  replacement=new_by_page_text.get((i['evidence'][0]['page'],i['text']));assert replacement,(i['code'],i['text']);supersessions.append({'superseded_record_id':i['id'],'replacement_record_id':replacement['id'],'old_partial_code':i['code'],'full_source_code':replacement['code'],'reason':'Generic recovery stripped printedMS prefix/local n suffix; physical code/text already represented by full local objective. Not a national curricular equivalence.'})
 report={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'agent:data_central_south','adapter_path':str(OUT.relative_to(ROOT)),'adapter_sha256':sha(OUT.read_bytes()),'source_physical_objectives':162,'old_coded_records':len(oldcoded),'preserved_full_code_text_ids':162,'removed_partial_code_recoveries':len(supersessions),'records':len(final),'record_kinds':dict(collections.Counter(i['kind'] for i in final)),'record_supersessions':supersessions,'source_metadata_proposal':{'uncoded_items_path':str(OUT.relative_to(ROOT)),'adapter_authority_add':{'coded_learning_ranges':[[80,82],[84,86],[88,90],[92,94],[96,98]]}},'whole_source_reconciled':False,'uf_ready':False}
 (EVID/'extraction-and-lineage-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='record_supersessions'},ensure_ascii=False))
if __name__=='__main__':main()
