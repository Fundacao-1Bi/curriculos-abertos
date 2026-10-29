#!/usr/bin/env python3
"""Reconcile only the fully inventoried curricular annex, never the articles.
Expected technical IDs come from the independent physical heading/list inventory.
Every expected canonical text and page region is rechecked against the primary.
"""
from pathlib import Path
import datetime,hashlib,json,re,sys
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
source=next(s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text()) if s['id']=='br-ifa-parametros-2025')
sidecar=json.loads((ROOT/source['uncoded_items_path']).read_text())
pdf=fitz.open(ROOT/source['local_path']);digest=hashlib.sha256((ROOT/source['local_path']).read_bytes()).hexdigest()
assert digest==source['sha256']==sidecar['artifact_sha256']
# These are the physical numbered lists checked directly against pages17–24,
# independently of the number of emitted items. LGG really has six objectives.
specs=[('comuns',10,[17,18],source['normative_parts'][1],None),('lgg',6,[18,19],source['normative_parts'][2],'Linguagens e suas Tecnologias'),('mat',5,[20,21],source['normative_parts'][3],'Matemática e suas Tecnologias'),('cnt',5,[21,22],source['normative_parts'][4],'Ciências da Natureza'),('chs',5,[23,24],source['normative_parts'][5],'Ciências Humanas e Sociais Aplicadas')]
pages=[{'page':n,'text':pdf[n-1].get_text('text',sort=False)} for n in range(1,len(pdf)+1)]
actual=ingest.source_uncoded_items([source],{source['id']:{'pages':pages}});by_id={it['id']:it for it in actual};by_key={it['key']:it for it in sidecar['items']}
prefix='ca:'+source['id']+':section:';parts=[]
for group,count,page_range,name,component in specs:
 keys=['grupo-'+group]
 if group=='comuns':keys.insert(0,'anexo')
 for n in range(1,count+1):
  key=group+'-'+str(n).zfill(2);keys.append(key)
  if group!='comuns':keys.append(key+'-capacidades')
 expected=[prefix+key for key in keys]
 # Independently reread the actual printed numbered list of this source group.
 numbered=next(row for row in sidecar['physical_numbered_lists'] if row['group']==group)
 assert numbered['observed']==list(range(1,count+1))
 for key in keys:
  original=by_key[key];loaded=by_id[prefix+key]
  assert loaded['code'] is None and loaded['text']==original['text']
  for e in original['evidence']:
   assert e['excerpt'] in pdf[e['page']-1].get_text('text',sort=False)
   assert len(e['bbox'])==4
  assert original.get('parent_key') is None or prefix+original['parent_key'] in by_id
 example=by_key[group+'-01']['evidence'][0]
 parts.append({'name':name,'expected_item_ids':expected,'verified_item_ids':expected.copy(),'expected_components':[component] if component else ['Competências comuns aos IFAs'],'page_ranges':[page_range],'sample_item_ids':[prefix+group+'-01'],'evidence':[{'page':example['page'],'section':name,'excerpt':example['excerpt'],'verification':'Entire physical numbered list and all corresponding full primary text fragments/page regions were independently checked; all explicit capacity groups included.','physical_numbered_denominator':list(range(1,count+1)),'verification_report':'docs/evidence/source-audit-southeast/br-ifa-2025-reconciliation.json'}],'findings':[]})
assert set(by_id)=={i for p in parts for i in p['expected_item_ids']}
record={'source_id':source['id'],'artifact_sha256':digest,'extraction_revision':ingest.EXTRACTION_REVISION,'actor_type':'automated','actor_id':'data_bncc_southeast:primary-annex-reconciliation','executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Independent physical five-group heading/number inventory, complete page text and region checks, actual current pipeline source_uncoded_items loader; stable expected IDs derived from original numbered list identities. Not a human pedagogical review.','parts':parts,'pending_parts':[source['normative_parts'][0]],'scope':'Only entire curricular annex PDF17–24 reconciled. Normative articles PDF1–16 remain pending; full source readiness is not asserted.'}
out=ROOT/'data/manifests/reconciliation'/f'{source["id"]}.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'parts':len(parts),'items':len(by_id),'pending_parts':record['pending_parts'],'path':str(out.relative_to(ROOT))},ensure_ascii=False))
