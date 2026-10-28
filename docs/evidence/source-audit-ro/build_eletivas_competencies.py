#!/usr/bin/env python3
"""Preserve and type all43literal competency fields, including source mislabels."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
from build_eletivas_objectives import dump
sha=lambda b:hashlib.sha256(b).hexdigest()
# Documentary units, selected after reading every full field. Source numbers,
# titles and source-mislabeled purposes are never silently rewritten to BNCC.
RULES={
 'LGG3':r'(?m)^(?:Realizar|Respeitar|Conscientizar|Desenvolver)',
 'LGG4':r'(?m)^(?:Ampliar|Produzir|Organizar|Reconhecer|Compreender|Perceber|Adotar|Ser capaz|Discutir)',
 'LGG5':r'(?m)^(?:Valorizar|Investigar|Desenvolver)',
 'LGG6':r'(?m)^Competência Geral',
 'LGG10':r'(?m)^CG\d+',
 'MAT3':r'(?m)^•',
 'MAT5':r'(?m)^Competência Geral',
 'MAT10':r'(?m)^(?:Exercitar|Argumentar)',
 'MAT9':r'(?m)^(?:Exercitar|Conhecer-se)',
 'CNT5':r'(?m)^(?:A eletiva aproxima|Ao relacionar)',
 'CNT6':r'(?m)^(?:Conhecer|Adotar|Identificar|Reconhecer|Proteger-se|Agir|Participar|Analisar|Discutir|Cuidar|Acolher)',
 'CNT7':r'(?m)^[ \t]*(?:Essa competência envolve:|Domínio conceitual|Habilidade prática|Consciência socioambiental|Visão empreendedora|Integração  interdisciplinar)',
 'CNT8':r'(?m)^(?:Analisar|Investigar)',
 'CNT9':r'(?m)^\d+\.',
 'CNT10':r'(?m)^(?:Analisar|Investigar)',
 'CHT9':r'(?m)^CG\d+',
}
PURPOSE_FIELDS={'MAT1','MAT4','MAT7','MAT8','CNT3','CHT2','CHT5','CHT8'}
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-eletivas-2026');assert sha((ROOT/source['local_path']).read_bytes())==source['sha256'];doc=fitz.open(ROOT/source['local_path'])
    base=json.loads((ROOT/'data/manifests/uncoded/ro-eletivas-skill-fields-v2.json').read_text());assert len(base['items'])==809;adapter=copy.deepcopy(base);records=adapter['items'];keys={r['key']:r for r in records};census=json.loads((BASE/'eletivas-primary-field-census.json').read_text());fields=[f for f in census['physical_fields']if f['label']in ['COMPETÊNCIA GERAL','COMPETENCIA GERAL']];assert len(fields)==43;unit_census=[]
    for f in fields:
        number=census['physical_fields'].index(f)+1;parent=f'projeto-{f["project_code"]}-p{f["project_page"]}-campo-{number}';raw=doc[f['page']-1].get_text('text',clip=fitz.Rect(f['bbox']),sort=True).strip();assert raw==f['text']
        if parent not in keys:
            assert f['project_code']=='MAT10'and f['label']=='COMPETENCIA GERAL';projectparent=f'projeto-{f["project_code"]}-p{f["project_page"]}';e={'source_id':source['id'],'page':f['page'],'printed_page':None,'section':parent,'excerpt':raw,'bbox':f['bbox'],'locator':'ro-eletivas:'+parent,'method':'expanded-accent-independent-physical-field-census'};context={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':parent,'parent_key':projectparent,'kind':'secao_normativa','code':None,'text':raw,'page':f['page'],'locator':e['locator'],'positions':copy.deepcopy(keys[projectparent]['positions']),'evidence':[e],'source_context':{'literal_field_label':f['label'],'label_evidence':{'page':f['page'],'bbox':f['label_bbox'],'text':f['label']},'field_is_context_not_a_second_learning_denominator':True,'corrects_prior_accent_only_census_scope':True},'actor_type':'automated','actor_id':'curriculos-abertos:ro-eletivas-primary-audit','technical_validation_status':'primary_unaccented_field_readback'};records.append(context);keys[parent]=context
        assert raw==keys[parent]['text'];starts=sorted(set([0,*[m.start()for m in re.finditer(RULES.get(f['project_code'],r'(?!)'),raw)]]));units=[];main_competency=None
        for i,start in enumerate(starts):
            end=starts[i+1]if i+1<len(starts)else len(raw);text=raw[start:end].strip()
            if not text:continue
            kind='competencia_geral';actual_parent=parent
            if f['project_code']in PURPOSE_FIELDS or(f['project_code']=='LGG3'and text.startswith('Conscientizar'))or(f['project_code']=='LGG4'and text.startswith('Ampliar')):kind='objetivo_formativo'
            if f['project_code']=='CHT9':kind='referencia_no_documento'
            if f['project_code']=='CNT1':kind='competencia_especifica'
            if f['project_code']=='CNT5'and text.startswith(('A eletiva aproxima','Ao relacionar')):kind='secao_normativa'
            if f['project_code']=='CNT7':
                if text=='Essa competência envolve:':kind='grupo_curricular';actual_parent=main_competency
                elif i>0:kind='capacidade';actual_parent=main_competency
            key=parent+'-competencia-unidade-'+str(len(units)+1);e={'source_id':source['id'],'page':f['page'],'printed_page':None,'section':key,'excerpt':text,'bbox':f['bbox'],'locator':'ro-eletivas:'+key,'method':'all-literal-competency-field-body-native-sort-v1'}
            r={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':actual_parent,'kind':kind,'code':None,'text':text,'page':f['page'],'locator':e['locator'],'positions':copy.deepcopy(keys[parent]['positions']),'evidence':[e],'actor_type':'automated','actor_id':'curriculos-abertos:ro-eletivas-primary-audit','technical_validation_status':'complete_primary_competency_field_readback_source_mislabels_preserved','source_context':{'literal_field_label':f['label'],'source_label_does_not_override_organizational_purpose_role':kind=='objetivo_formativo','national_canonical_wording_or_number_identity_verified':False,'semantic_equivalence_claimed':False,'no_learning_code_invented_from_numeric_competency_or_CG_label':True,'source_year_not_inferred':True}}
            records.append(r);keys[key]=r
            if f['project_code']=='CNT7'and main_competency is None:main_competency=key
            units.append({'key':key,'start':start,'end':end,'kind':kind,'text_sha256':sha(text.encode())})
        unit_census.append({'page':f['page'],'project':f['project_code'],'bbox':f['bbox'],'field_key':parent,'text_sha256':sha(raw.encode()),'units':units})
    destination=ROOT/'data/manifests/uncoded/ro-eletivas-competency-fields-v3.json';adapter['method']='Preserves809priorrecords; all43competencyfields now typed in literal units, separating organizationalpurposes, bare CGreferences, explanatorycontext and statedcapabilities. Printedsource labels/numbering/wording are never silently matched or normalizedtoBNCC.';adapter['expected_inventory']={**base['expected_inventory'],'complete_competency_fields':43};dump(destination,adapter)
    proposed={**source,'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':{**source.get('adapter_authority',{}),'coded_learning_pages':[24,117]}};extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in [1,*range(24,118)]]};finalized=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:extracted}),[proposed]);schema=validators(ROOT);errors=[(r['id'],e.message)for r in finalized for e in schema['Learning'].iter_errors(r)];assert not errors,errors[:8];assert len(finalized)==len(records)
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(records),'base809_preserved':records[:809]==base['items'],'kinds':dict(collections.Counter(r['kind']for r in records)),'complete_competency_fields':43,'field_units':unit_census,'census_correction':{'previous_accented_fields':42,'actual_all_fields':43,'missing_heading':'COMPETENCIA GERAL','project':'MAT10','page':70,'prior_missing_field_claim_retracted':True},'literal_competency_number_mismatch_not_repaired':[{'project':'CHT4','page':105,'source_prints':'Competência geral 5','body_begins':'Exercitar a empatia, o diálogo','note':'Literal source kept; no national numbering correction, alias or identity/equivalence claim.'}],'real_finalizer_schema_records':len(finalized),'binding_ready':False,'ready':False,'reconciled':False,'remaining_scope':['Independent full saved-file field readback must pass before binding.','All knowledge objects/axis/methodological context/rubrics and introductory normative chapter structure still need full typed reconciliation.'],'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_eletivas_competencies.py'};dump(BASE/'eletivas-competencies-primary-report.json',report);dump(BASE/'ro-eletivas-competencies-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':{'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':proposed['adapter_authority']},'binding_ready':False,'ready':False,'reconciled':False});print(json.dumps({k:report[k]for k in ['adapter_sha256','records','kinds','complete_competency_fields','real_finalizer_schema_records']},ensure_ascii=False))
if __name__=='__main__':main()
