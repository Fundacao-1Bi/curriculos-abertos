#!/usr/bin/env python3
"""Create non-autoloaded MA Source proposals; no mutation of Northeast manifest."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-ma-current'
def main():
 acts=json.loads((OUT/'acts/source-proposals.json').read_text());inv=json.loads((OUT/'indexed-catalogue-inventory.json').read_text());pending=acts['research_pending_sources']
 for s in pending:
  if s['id']=='ma-dctma-educacao-digital-midiatica':
   s['issuer']='Secretaria de Estado da Educação do Maranhão, conforme art.1 da Resolução CEE/MA211/2026';s['redistribution']='Documento integral ainda não obtido; nenhuma condição de redistribuição atribuída.'
 d={'format':'curriculos-abertos/source-proposals-v1','actor_type':'automated','actor_id':'agent:rs_adapter:ma-current-inventory','at':datetime.now(timezone.utc).isoformat(),'integration_status':'awaiting_northeast_review_single_location','proposed_sources':acts['proposed_sources'],'research_pending_sources':pending,'catalogue_candidates':inv['entries'],'existing_source_ids_not_duplicated':['ma-dctm-ei-ef','ma-dctm-em-vol2'],'catalogue_evidence_path':'docs/evidence/source-audit-ma-current/indexed-catalogue-inventory.json','scope_limit':'No automatic loading; proposals require single-location integration by Northeast. Catalogue labels do not assert PDF identity, adoption or editorial dates.'}
 d['pending_typology_sources']=acts.get('pending_typology_sources',[])
 # ESC02: a modality-specific policy is not automatically a required corpus part.
 modality=[s for s in d['proposed_sources'] if s['id']=='ma-resolucao-162-2025-eiti-doe']
 d['proposed_sources']=[s for s in d['proposed_sources'] if s['id']!='ma-resolucao-162-2025-eiti-doe']
 for s in modality:
  s.update(mandatory=None,required=None,include_in_corpus=None)
  s['typology_review_reason']='ESC02: documento específico da modalidade EITI não constitui condição automática do lançamento; integração indispensável ao referencial selecionado ainda precisa decisão documental. Aquisição e recorte preservados, sem exclusão.'
 d['pending_typology_sources'].extend(modality)
 for s in d['pending_typology_sources']:
  s.setdefault('redistribution','Original integral mantido em cache privado; condições de redistribuição não estabelecidas.')
 p=ROOT/'data/manifests/ma-current-supplement.json'
 if p.exists():
  prior=json.loads(p.read_text());ids=prior.get('integrated_source_ids',[])
  before={s['id']:s for s in prior.get('proposed_sources',[])+prior.get('research_pending_sources',[])}
  after={s['id']:s for s in d['proposed_sources']+pending}
  for ident in ids:
   assert ident in after and all(before[ident].get(k)==after[ident].get(k) for k in ('artifact_url','sha256','local_path','page_regions')),'Integrated source changed; revalidate with Northeast before rebuilding'
   after[ident]['integration_status']='integrated_into_northeast_manifest'
  if ids:
   for key in ('integrated_source_ids','integrated_manifest_path','integration_status','integration_confirmation'):d[key]=prior[key]
 schema=json.loads((ROOT/'data/schema/1.1.0.json').read_text());v=Draft202012Validator({'$schema':schema['$schema'],'$ref':'#/$defs/Source','$defs':schema['$defs']})
 for s in d['proposed_sources']+pending+d['pending_typology_sources']:v.validate(s)
 tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
 r={'actor_type':'automated','schema_version':'1.1.0','all_source_proposals_valid':True,'acquired_required_proposals':len(d['proposed_sources']),'research_pending_sources':len(pending),'acquired_pending_typology_proposals':len(d['pending_typology_sources']),'disposition':'Null artifact URLs preserved where original unlocated; wrapper deliberately outside autoload.','supplement_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 (OUT/'proposal-schema-check.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
