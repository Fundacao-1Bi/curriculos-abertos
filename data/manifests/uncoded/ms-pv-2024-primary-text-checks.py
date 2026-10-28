#!/usr/bin/env python3
"""Bind all681 MS texts to an independent primary visible-glyph model for gateV2.
Expected text/key model is built BEFORE reading the frozen adapter. No hashes of
extraction output alone are accepted, and no active manifest/sidecar is written.
"""
from pathlib import Path
import sys,json,hashlib,collections,re,copy,importlib.util
import fitz
ROOT=Path(__file__).resolve().parents[3];AUDIT=ROOT/'docs/evidence/source-audit-ms-pv';SID='ms-projeto-vida-orientacoes-2024';SHA='eff8fcd19d69b1f5d614cbb2ca1599d98e11c697772084b56694a142fecf7048'
MODEL=AUDIT/'independent-denominator.json';OUT=Path(__file__).with_name('ms-pv-2024-primary-text-checks.json')
s=importlib.util.spec_from_file_location('independent_ms_source_reader',AUDIT/'independent-inventory.py');W=importlib.util.module_from_spec(s);s.loader.exec_module(W)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tsha(t):return hashlib.sha256(t.encode('utf-8')).hexdigest()
def boxunion(bb):return [min(b[0] for b in bb),min(b[1] for b in bb),max(b[2] for b in bb),max(b[3] for b in bb)]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def run():
 denom=json.loads(MODEL.read_text());assert denom['source_id']==SID and denom['artifact_sha256']==SHA
 source=next(x for x in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if x['id']==SID);pdf=ROOT/source['local_path'];assert digest(pdf)==SHA
 expected={};glyph_checks=[];body_cache={};tables_cache={};evcount=0
 def ev(pn,text,bb,section):return {'source_id':SID,'page':pn,'printed_page':str(pn),'section':section,'excerpt':text,'bbox':bb,'method':'independent-primary-visible-glyph-model-v1','verification':'Source-only glyph trace, primary physical cell/header; exact UTF-8 text bound after visible-source comparison.'}
 def add(key,kind,text,evidence,parent=None,code=None):
  assert key not in expected and text
  expected[key]={'item_id':f'ca:{SID}:section:{key}','key':key,'kind':kind,'expected_primary_text':text,'text_sha256':tsha(text),'evidence':evidence,'expected_parent_key':parent,'expected_code':code}
 with fitz.open(pdf) as doc:
  def gs(pn):
   if pn not in body_cache:body_cache[pn]=W.glyphs(doc[pn-1])
   return body_cache[pn]
  for pn,key in [(50,'ef-ai'),(78,'ef-af'),(99,'em')]:
   lines=[l for l in W.rendered_lines([c for c in gs(pn) if c['font']=='ArchivoBlack-Regular']) if re.search(r'ENSINO|ANOS',l['text'])];assert lines
   text=W.norm(' '.join(l['text'] for l in lines));add(key,'etapa_curricular',text,[ev(pn,text,boxunion([l['bbox'] for l in lines]),'Explicit stage divider')])
  for table in denom['tables']:
   pn=table['page'];ctx=table['context'];yk=f'{ctx["stage"].lower()}-year-{ctx["year"]}';sk='em' if ctx['stage']=='EM' else 'ef-ai' if pn<78 else 'ef-af'
   if yk not in expected:
    ye=ctx['year_evidence'];pn_y=ye['page'];bb=boxunion([l['bbox'] for l in ye['lines']]);actual=W.rendered_text(W.region_glyphs(gs(pn_y),bb));assert actual==ye['text'],(yk,actual,ye['text']);add(yk,'ano_escolar',actual,[ev(pn_y,actual,bb,'Explicit visible school-year heading')],sk)
   candidates=[t for t in doc[pn-1].find_tables(strategy='lines').tables if t.col_count==3 and max(abs(a-b) for a,b in zip(t.bbox,table['table_bbox']))<.5];assert len(candidates)==1,(pn,len(candidates));actual_table=candidates[0];tables_cache[pn]=actual_table
   ee=[]
   for ci,bb in enumerate(actual_table.rows[0].cells):
    tx=W.rendered_text(W.region_glyphs(gs(pn),bb));ee.append(ev(pn,tx,list(bb),f'Original table column header{ci}'))
   assert [e['excerpt'] for e in ee]==['CÓDIGO DA HABILIDADE','HABILIDADE','OBJETOS DE CONHECIMENTO'];add(f'table-p{pn}','quadro_curricular',W.norm(' '.join(e['excerpt'] for e in ee)),ee,yk)
  for row in denom['rows']:
   pn=row['page'];ri=row['physical_row'];actual_row=tables_cache[pn].rows[ri];assert len(actual_row.cells)==3
   # Revalidate the independent cached model directly from all physical cells.
   for ci,cell in enumerate(row['cells']):
    bb=list(actual_row.cells[ci]);assert max(abs(a-b) for a,b in zip(bb,cell['bbox']))<.5
    visible=[c for c in W.region_glyphs(gs(pn),bb) if c['color']!=[1.,1.,1.]];actual=W.rendered_text(visible);assert actual==cell['rendered_text'],(pn,ri,ci,actual,cell['rendered_text']);glyph_checks.append({'page':pn,'row':ri,'column':ci,'glyphs':len(visible),'text_sha256':tsha(actual),'exact_primary_model_match':True})
   k=f'skill-p{pn}-r{ri}';c=row['cells'][1];add(k,'habilidade',c['rendered_text'],[ev(pn,c['rendered_text'],c['bbox'],f'Physical row{ri}/HABILIDADE')],f'table-p{pn}',row['code'])
   cell=row['cells'][2];whole=cell['rendered_text'];markers=cell['pillar_markers'];counts=collections.Counter(m['text'] for m in markers)
   # No adapter text/bbox is used to split content. Printed title occurrence counts
   # must equal the source bold-marker census, ruling out ambiguous prose matches.
   assert all(whole.count(title)==n for title,n in counts.items()),(pn,ri,'ambiguous title occurrence')
   starts=[];cursor=0
   for marker in markers:
    at=whole.find(marker['text'],cursor);assert at>=cursor;starts.append(at);cursor=at+len(marker['text'])
   assert starts[0]==0
   for i,(marker,start) in enumerate(zip(markers,starts),1):
    pk=f'pillar-p{pn}-r{ri}-n{i}';end=starts[i] if i<len(starts) else len(whole);body=whole[start+len(marker['text']):end].strip();assert body
    add(pk,'pilar_estruturante',marker['text'],[ev(pn,marker['text'],marker['bbox'],f'Physical row{ri}/printed bold pillar{i}')],k)
    add(f'objects-p{pn}-r{ri}-n{i}','objeto_conhecimento',body,[ev(pn,body,cell['bbox'],f'Physical row{ri}/objects following printed pillar{i}: {marker["text"]}')],pk)
 # The source-derived model is complete before the adapter is opened.
 assert len(expected)==681 and collections.Counter(x['kind'] for x in expected.values())=={'etapa_curricular':3,'ano_escolar':12,'quadro_curricular':73,'habilidade':141,'pilar_estruturante':226,'objeto_conhecimento':226}
 assert sum(len(x['evidence']) for x in expected.values())==827
 model_projection=json.dumps({k:v['text_sha256'] for k,v in expected.items()},sort_keys=True,separators=(',',':')).encode();model_sha=hashlib.sha256(model_projection).hexdigest()
 sidepath=ROOT/'data/manifests/uncoded/ms-pv-2024-items.json';side=json.loads(sidepath.read_text());assert digest(sidepath)=='77eb9feaa003382a73741f36f3379d83aa945debae1cd128b7ad95513e781f08';actual={r['key']:r for r in side['items']};assert set(actual)==set(expected)
 checks=[];failures=[]
 for key,e in expected.items():
  a=actual[key];assert a['id']==e['item_id'] and a['kind']==e['kind'] and a.get('parent_key')==e['expected_parent_key'] and a.get('code')==e['expected_code'],key
  ok=a['text']==e['expected_primary_text'] and tsha(a['text'])==e['text_sha256']
  if not ok:failures.append({'key':key,'expected':e['expected_primary_text'],'actual':a['text']})
  checks.append({k:e[k] for k in ('item_id','text_sha256','evidence')})
 assert not failures,failures[:3]
 # Exact V2 gate checks, including a controlled accent/word mutation.
 sys.path.insert(0,str(ROOT/'pipeline'));import reconciliation
 byid={x['id']:x for x in actual.values()};verified,issues=reconciliation._checks(checks,byid,SID);assert len(verified)==681 and not issues
 mutated=copy.deepcopy(byid);target=next(e['item_id'] for e in expected.values() if e['kind']=='habilidade');mutated[target]['text']+=' alteração';v,err=reconciliation._checks(checks,mutated,SID);assert len(v)==680 and any(x.startswith('item_text_changed_or_unbound:') for x in err)
 accented=next(i for i,x in byid.items() if 'ê' in x['text']);mutated_accent=copy.deepcopy(byid);mutated_accent[accented]['text']=mutated_accent[accented]['text'].replace('ê','e',1);va,erra=reconciliation._checks(checks,mutated_accent,SID);assert len(va)==680 and any(x.startswith('item_text_changed_or_unbound:') for x in erra)
 groups=collections.defaultdict(list)
 for key,e in expected.items():
  cur=key
  while expected[cur]['expected_parent_key']:cur=expected[cur]['expected_parent_key']
  groups[cur].append(e['item_id'])
 assert {k:len(v) for k,v in groups.items()}=={'ef-ai':245,'ef-af':207,'em':229}
 report={'actor_type':'automated','actor_id':'agent:rs_adapter:ms-primary-text-v2','source_id':SID,'artifact_sha256':SHA,'sidecar_sha256':digest(sidepath),'source_only_independent_model_path':str(MODEL.relative_to(ROOT)),'source_only_independent_model_sha256':digest(MODEL),'independent_reader_path':str((AUDIT/'independent-inventory.py').relative_to(ROOT)),'independent_reader_sha256':digest(AUDIT/'independent-inventory.py'),'prior_independent508_comparison_sha256':digest(AUDIT/'independent-adapter-comparison.json'),'method':'Build681 expected texts/keys from independent source-only visible-glyph model before opening adapter; recompare423physical cells plus12year headers/73three-column headers/3stage dividers to current original PDF. Split objects only by unambiguous source bold-pillar title markers. Bind exact UTF-8 SHA256 without normalization after this primary comparison.','expected_item_text_sha256':{e['item_id']:e['text_sha256'] for e in expected.values()},'primary_text_model_projection_sha256':model_sha,'item_checks':checks,'expected_ids_by_stage_part':dict(groups),'counts':{'items':681,'primary_evidence_fragments':827,'physical_cells_rechecked':len(glyph_checks),'independent_prior_checks':508,'v2_gate_verified':len(verified),'v2_gate_issues':len(issues)},'controlled_text_mutation_rejected':True,'controlled_diacritic_only_mutation_rejected':True,'failures':failures,'source_ready':False,'scope':'Only three organizers:245EF-AI/207EF-AF/229EM. Orientation/framework pages1–49 and126–127 remain pending. This receipt does not prove incorporation into a national sharded artifact.'}
 dump(OUT,report);dump(AUDIT/'ms-pv-2024-primary-text-model.json',{'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','model_built_before_adapter_read':True,'expected_records':list(expected.values()),'direct_primary_cell_checks':glyph_checks,'text_model_projection_sha256':model_sha});dump(AUDIT/'ms-pv-2024-primary-text-v2-verification.json',{'actor_type':'automated','actor_id':report['actor_id'],'source_id':SID,'artifact_sha256':SHA,'sidecar_sha256':report['sidecar_sha256'],'receipt_path':str(OUT.relative_to(ROOT)),'receipt_sha256':digest(OUT),'counts':report['counts'],'stage_part_counts':{k:len(v) for k,v in groups.items()},'gate_version':reconciliation.GATE_VERSION,'controlled_text_mutation_rejected':True,'controlled_diacritic_only_mutation_rejected':True,'failures':failures,'status':'passed','source_ready':False,'whole_source_reconciliation':False});print(json.dumps({'records':681,'evidence':827,'cells_rechecked':len(glyph_checks),'v2_gate_verified':len(verified),'receipt_sha256':digest(OUT),'sidecar_unchanged_sha256':digest(sidepath)}))
if __name__=='__main__':run()
