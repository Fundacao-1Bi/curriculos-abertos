"""Add the thirty full field-right quotations; preserve prior snapshots and identities."""
from pathlib import Path
import json,hashlib,copy,datetime,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=ROOT/'docs/evidence/source-audit-to';OLD=ROOT/'data/manifests/uncoded/to-ei-organizers-age-v2-items.json';OUT=ROOT/'data/manifests/uncoded/to-ei-rights-v3-items.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();expected='fbb08f66d3c681db8d842dc60d5c88fbb2ff74d2c2dad46283ac6717026841bd';assert sha(OLD)==expected;A=json.loads(OLD.read_text());items=copy.deepcopy(A['items']);source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==A['source_id']);D=fitz.open(ROOT/source['local_path']);SID=source['id'];olditems={r['key']:r for r in A['items']};bykey={r['key']:r for r in items};changes=[];inventories=[]
for r in items:
 if r['source_context'].get('explicit_right_label_only'):
  r['kind']='rotulo_direito';r['source_context']['technical_kind_correction']={'previous_kind':'direito_aprendizagem','current_kind':'rotulo_direito','reason':'Repeated organizer header names are labels, not the complete field-specific right statements.'};e=r['evidence'][0];rects=D[e['page']-1].search_for(r['text'],clip=fitz.Rect(e['bbox']));assert len(rects)==1,(r['key'],rects);e['bbox']=list(rects[0]);e['method']='primary_exact_right_label_glyph_bounds';changes.append(r['key'])
# Physical field quotations. CG's sixth statement is on65above the organizer,
# despite being last in the PDF's creation-order text; geometric order is used.
specs=[(54,[(53,348.3,552.39)],'Eu o outro e o nós'),(65,[(64,613.3,806),(65,73.8,107.87)],'Corpo, gestos e movimentos'),(73,[(72,411.3,673.45)],'Traços, sons, formas e imagens'),(78,[(77,521.2,783.32)],'Escuta, fala, pensamento e imaginação'),(93,[(92,377.5,639.65)],'Espaços, tempos, quantidades, relações e transformações')]
labels=['conviver','brincar','participar','explorar','expressar','conhecer-se']
for organizer,regions,heading in specs:
 units=[];current=None
 for pn,y0,y1 in regions:
  lines=[]
  for b in D[pn-1].get_text('dict')['blocks']:
   for l in b.get('lines',[]):
    text=''.join(s['text']for s in l['spans']).strip()
    if text and y0<=l['bbox'][1]<y1-.01:lines.append({'page':pn,'text':text,'bbox':list(l['bbox'])})
  lines.sort(key=lambda l:(l['bbox'][1],l['bbox'][0]))
  for line in lines:
   if line['text'].startswith('■'):
    if current:units.append(current)
    m=re.match(r'^■\s*([A-ZÇÊ-]+)',line['text']);assert m,line
    current={'label':m[1].lower(),'lines':[]}
   assert current,(pn,line)
   current['lines'].append(line)
 if current:units.append(current)
 assert [u['label']for u in units]==labels,(organizer,[u['label']for u in units])
 inventories.append({'organizer_field_key':f'field-p{organizer}','rights_heading_literal':heading,'regions':regions,'units':[{'label':u['label'],'page':u['lines'][0]['page'],'line_count':len(u['lines'])}for u in units]})
 for unit in units:
  key=f'field-p{organizer}-right-definition-{unit["label"]}';parent=f'field-p{organizer}-right-{unit["label"]}';assert parent in bykey;ev=[]
  for line in unit['lines']:
   ev.append({'source_id':SID,'page':line['page'],'printed_page':str(line['page']),'section':heading,'excerpt':line['text'],'bbox':line['bbox'],'locator':f'to-right:{key}:line:{len(ev)+1}','method':'native-primary-full-field-right-quotation-line','coordinate_space':'original_pdf_page'})
  title=bykey[f'field-p{organizer}']['text'];positions=copy.deepcopy(bykey[parent]['positions']);record={'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':f'field-p{organizer}','kind':'direito_aprendizagem','code':None,'official_code_present_in_source':False,'text':'\n'.join(e['excerpt']for e in ev).removeprefix('■').lstrip(),'page':ev[0]['page'],'locator':'to-right:'+key,'positions':positions,'evidence':ev,'source_context':{'full_field_specific_right_statement':True,'corresponding_organizer_label_key':parent,'original_list_marker':'■','not_only_an_organizer_label':True,'source_rights_heading_literal':heading,'organizer_field_heading_literal':title,'heading_variation_preserved':heading.casefold()!=title.casefold(),'quoted_reference_printed_by_source':'Brasil,2016 (2ª Versão da BNCC)','documentary_parent_association':'Field-right quotation immediately precedes this field organizer in the same chapter; no national equivalence/alias asserted.'},'source_order':0,'actor_type':'automated','actor_id':'curriculos-abertos:to-ei-primary-field-rights-v3'};items.append(record)
items.sort(key=lambda r:(r['page'],r['evidence'][0]['bbox'][1],r['evidence'][0]['bbox'][0],r['key']))
for order,r in enumerate(items,1):r['source_order']=order
assert len(items)==len(A['items'])+30
for r in items:
 if r['key']not in olditems:continue
 old=olditems[r['key']]
 for f in ['key','parent_key','code','code_original','text','positions']:assert r.get(f)==old.get(f),(r['key'],f)
 if r['key']not in changes:assert r['kind']==old['kind']
clock=json.loads(OUT.read_text())['generated_at']if OUT.exists()else datetime.datetime.now(datetime.timezone.utc).isoformat();a={**A,'generated_at':clock,'technical_revision':'full-field-right-definitions-and-label-order-v3','prior_sidecar_sha256':expected,'prior_sidecar_path':str(OLD.relative_to(ROOT)),'official_curriculum_edition_changed':False,'scope':'All three organizer column roles54–103 plus the30completefield-right quotations53/64–65/72/77/92. Thirty repeated organizer labels are explicitly typed rotulo_direito; complete definitions are distinct documentary units. Other narrative sections110page book not globally reconciled.','items':items};OUT.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
pin={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')};E={'source_id':SID,'sha256':source['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(D)]};bad=[r['key']for r in items if not ingest.evidence_check(r,E,D)];assert not bad,bad
proposed={**source,'uncoded_items_path':str(OUT.relative_to(ROOT)),'adapter_authority':{'coded_learning_pages':[54,103]}};loaded=ingest.source_uncoded_items([proposed],{SID:E});final=ingest.finalize_items(loaded,[proposed]);assert len(final)==len(items)
from validate_artifact import validators
schema=validators(ROOT)['Learning'];errors=[e.message for r in final for e in schema.iter_errors(r)];assert not errors,errors[:5];assert pin=={p.name:sha(p)for p in(ROOT/'pipeline').glob('*.py')}
assert sha(OLD)==expected
report={'actor_type':'automated','source_id':SID,'artifact_sha256':source['sha256'],'prior_sidecar_sha256':expected,'sidecar_path':str(OUT.relative_to(ROOT)),'sidecar_sha256':sha(OUT),'records':len(items),'kind_counts':dict(__import__('collections').Counter(r['kind']for r in items)),'prior_ids_codes_texts_positions_parents_preserved':329,'explicit_kind_corrections':changes,'label_glyph_boxes_tightened':30,'label_order_corrected_from_primary_x_positions':True,'full_right_definition_count':30,'rights_source_inventory':inventories,'literal_loader_finalizer_schema':'passed','parser_pin_stable':True,'independent_review':'pending_v3_right_definitions_and_label_order','actual_source_binding':False,'whole_source_ready':False};(BASE/'ei-rights-v3-adapter-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print({k:report[k]for k in ['records','kind_counts','sidecar_sha256','literal_loader_finalizer_schema']})
