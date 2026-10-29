#!/usr/bin/env python3
"""Bounded real importer/hierarchy negative controls; no source/cache mutation."""
from pathlib import Path
import os,sys,json,copy,tempfile,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,os.environ.get('RN_PROBE_PIPELINE',str(ROOT/'pipeline')))
import ingest,pymupdf as fitz
ingest.ROOT=ROOT;ingest.safe_path.__defaults__=(ROOT,)
SID='rn-trilhas-aprofundamento';AUDIT=ROOT/'docs/evidence/source-audit-rn-uncoded';side=json.loads((ROOT/'data/manifests/uncoded/rn-trilhas-items.json').read_text());raw=json.loads((ROOT/'data/manifests/northeast.json').read_text());source=next(s for s in (raw['sources'] if isinstance(raw,dict) else raw) if s['id']==SID)
with fitz.open(ROOT/source['local_path']) as doc:ex={'source_id':SID,'sha256':source['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)} for i,p in enumerate(doc)]}
results=[]
with tempfile.TemporaryDirectory(prefix='rn-negative-',dir=ROOT/'var/private-evidence/source-audit-rn-uncoded') as td:
 path=Path(td)/'adapter.json';src=copy.deepcopy(source);src['uncoded_items_path']=str(path.relative_to(ROOT));base={k:v for k,v in side.items() if k not in ('items','item_parent_links')}
 def run(name,record=None,wrapper_hash=None,links=None,expect='literal_reject'):
  obj=copy.deepcopy(base);obj['items']=[record] if record else [side['items'][0]];obj['item_parent_links']=links or []
  if wrapper_hash:obj['artifact_sha256']=wrapper_hash
  path.write_text(json.dumps(obj,ensure_ascii=False));errors=[]
  try:
   it=ingest.source_uncoded_items([src],{SID:ex},errors)
   if links:
    coded=json.loads((ROOT/'var/private-evidence/source-audit-rn-uncoded/shared-coded-baseline.json').read_text());ingest.attach_hierarchy(ingest.finalize_items(coded+it,[src]),[src])
   rejected=bool(errors);detail=errors[0]['check'] if errors else 'accepted'
  except ValueError as e:rejected=True;detail=str(e)
  expected_accept=expect=='accept';assert rejected!=expected_accept,(name,detail)
  results.append({'case':name,'result':'accepted' if not rejected else 'rejected','expected':expect,'detail':detail})
 r=copy.deepcopy(next(x for x in side['items'] if x['kind']=='objetivo_aprendizagem'));run('positive_local_objective',r,expect='accept');r['text']+=' CONTEUDO_INVENTADO_987654321';run('invented_objective_text',r)
 md=copy.deepcopy(next(x for x in side['items'] if x['kind']=='modulo_curricular'));run('positive_rotated_native_cluster_label',md,expect='accept');md['text']='Módulo 9';md['evidence'][0]['excerpt']='Módulo 9';run('wrong_rotated_module_number',md)
 md=copy.deepcopy(next(x for x in side['items'] if x['kind']=='modulo_curricular'));md['evidence'][0]['source_id']='different-source';run('cross_source_native_glyph_evidence',md)
 md=copy.deepcopy(next(x for x in side['items'] if x['kind']=='modulo_curricular'));md['evidence'][0]['artifact_sha256']='0'*64;run('wrong_native_glyph_artifact_hash',md)
 run('wrong_sidecar_wrapper_hash',wrapper_hash='0'*64)
 run('ambiguous_repeated_code_parent_selector',links=[{'code':'EMIFLGG01','parent_key':'document'}])
 exact=copy.deepcopy(side['item_parent_links'][0]);exact['parent_key']='missing-parent';run('missing_structural_parent',links=[exact])
report={'actor_type':'automated','actor_id':'agent:rs_adapter:rn-real-negative-controls','source_id':SID,'sidecar_sha256':hashlib.sha256((ROOT/'data/manifests/uncoded/rn-trilhas-items.json').read_bytes()).hexdigest(),'cases':results,'failures':0,'method':'Real source_uncoded_items/finalize_items/attach_hierarchy with minimal isolated temporary sidecars. No source PDF, active manifest, cache or core modified.'}
(AUDIT/'rn-trilhas-negative-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(results),'failures':0}))
