"""Serial, source-hash-bound integration of independently produced North adapters."""
from pathlib import Path
import json,hashlib,datetime,sys,copy
import fitz
ROOT=Path(__file__).resolve().parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
manifest=ROOT/'data/manifests/north.json';sources=json.loads(manifest.read_text());byid={s['id']:s for s in sources};changes=[]
for sid,page,printed,label,heading in [
 ('pa-dcepa-ei-ef',112,'112','1º, 2º E 3º ANO DO ENSINO FUNDAMENTAL','LÍNGUA PORTUGUESA'),
 ('ap-rca-ei-ef-mec',240,'239','BLOCO DE ANOS DE LÍNGUA PORTUGUESA: 1º AO 5º ANO','ORGANIZADOR CURRICULAR ÁREA DE LINGUAGEM - ENSINO FUNDAMENTAL ANOS INICIAIS'),
 ('ap-rca-ei-ef-cedoc',240,'239','BLOCO DE ANOS DE LÍNGUA PORTUGUESA: 1º AO 5º ANO','ORGANIZADOR CURRICULAR ÁREA DE LINGUAGEM - ENSINO FUNDAMENTAL ANOS INICIAIS')]:
 s=byid[sid];doc=fitz.open(ROOT/s['local_path']);p=doc[page-1];frags=[]
 for block in p.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   text=''.join(span['text'] for span in line['spans']).strip()
   if text in [label,heading]:frags.append({'source_id':sid,'page':page,'printed_page':printed,'section':heading,'excerpt':text,'bbox':list(line['bbox']),'method':'pymupdf-native-heading-primary-visual-confirmation'})
 assert len(frags)==2,(sid,frags)
 old=copy.deepcopy(s.get('position_contexts'))
 target=next(e for e in frags if e['excerpt']==label)
 c={'page':page,'stage':'EF','component':'Língua Portuguesa','area':'Linguagens' if sid.startswith('ap') else None,'years':list(range(1,6)) if sid.startswith('ap') else [1,2,3],'year_label':label,'evidence':target,'heading_evidence':frags,'note':'Automated primary visual review: a single Habilidades column is under this explicit local year-block heading. This observation is not a literal quotation; no broader page range or prerequisite relation is inferred.'}
 s['position_contexts']=[c];changes.append({'source_id':sid,'old_position_contexts':old,'new_position_contexts':[c],'source_sha256':s['sha256']})
for name in ['ro-ei','ro-matrizes-2026','ro-itinerarios-2026','ro-matrizes-2025','ro-rcem-lgg']:
 proposal_path=ROOT/f'docs/evidence/source-audit-ro/{name}-proposed-source-fields.json';proposal=json.loads(proposal_path.read_text());s=byid[proposal['source_id']]
 assert proposal['artifact_sha256']==s['sha256']
 adapter_path=ROOT/proposal['fields']['uncoded_items_path'];adapter=json.loads(adapter_path.read_text());expected=proposal.get('adapter_sha256')
 assert adapter['artifact_sha256']==s['sha256'] and adapter['source_id']==s['id']
 if expected:assert sha(adapter_path)==expected,(s['id'],sha(adapter_path),expected)
 if s.get('uncoded_items_path') and s['uncoded_items_path']!=proposal['fields']['uncoded_items_path']:
  previous=json.loads((ROOT/s['uncoded_items_path']).read_text());assert {r['key']for r in previous['items']}.issubset({r['key']for r in adapter['items']}),'Historical batch would regress a newer adapter. Use the current serial proposal.'
 old={k:copy.deepcopy(s.get(k)) for k in proposal['fields']};s.update(proposal['fields'])
 changes.append({'source_id':s['id'],'old_fields':old,'new_fields':proposal['fields'],'source_sha256':s['sha256'],'sidecar_sha256':sha(adapter_path),'sidecar_records':len(adapter['items']),'proposal_path':str(proposal_path.relative_to(ROOT)),'whole_document_reconciled':False})
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
for s in sources:ingest.validate_position_contexts(s)
dump(manifest,sources)
# Verify actual bound adapter loading, text and hierarchy with the frozen real loader/finalizer.
from validate_artifact import validators
schema=validators(ROOT)['Learning'];gates=[]
for change in changes:
 sid=change['source_id'];s=byid[sid]
 if not change.get('sidecar_sha256'):continue
 path=ROOT/s['uncoded_items_path'];adapter=json.loads(path.read_text());doc=fitz.open(ROOT/s['local_path']);extracted={'source_id':sid,'sha256':s['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(doc)]}
 parsed=ingest.source_uncoded_items([s],{sid:extracted});final=ingest.finalize_items(parsed,[s]);assert len(parsed)==len(final)==len(adapter['items']),(sid,len(parsed),len(final),len(adapter['items']))
 errors=[e.message for item in final for e in schema.iter_errors(item)];assert not errors,(sid,errors[:5])
 lookup={i['structural_key']:i for i in final}
 for item in adapter['items']:
  actual=lookup[item['key']]
  for field in ['text','kind','positions','code']:assert actual.get(field)==item.get(field),(sid,item['key'],field)
  if item.get('parent_key'):assert actual['parent_id']==f'ca:{sid}:section:{item["parent_key"]}'
 gates.append({'source_id':sid,'sidecar_sha256':sha(path),'records':len(final),'literal_loader_finalizer_schema':'passed','text_kind_positions_code_hierarchy_preserved':True,'native_pages':len(doc),'ready':False})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'curriculos-abertos:north-integration','changes':changes,'actual_manifest_bound_gates':gates,'all_north_position_context_shapes_valid':True,'whole_uf_ready_claimed':False,'parser_changed':False}
dump(ROOT/'docs/evidence/north-source-bindings-verification.json',report)
print(json.dumps({'source_updates':len(changes),'gates':gates,'all_context_shapes_valid':True},ensure_ascii=False))
