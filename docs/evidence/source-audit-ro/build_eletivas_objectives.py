#!/usr/bin/env python3
"""43 project headers, all126 main fields and every literal objective unit.

This increment does not supersede generic coded records: skill/competency fields,
objects, rubrics and introductory normative chapters still need typed reconciliation.
"""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
# These are documentary boundaries at the start of actual printed lines, never
# generated goals. Original text, numbering, wording and line wraps are retained.
ACTIONS='Analisar|Aplicar|Aprender|Apresentar|Argumentar|Articular|Atuar|Avaliar|Buscar|Capacitar|Caracterizar|Comparar|Compreender|Conectar|Conhecer|Consolidar|Construir|Contribuir|Criar|Debater|Demonstrar|Descrever|Desenvolver|Despertar|Diferenciar|Difundir|Discutir|Dominar|Educar|Empregar|Encenar|Encorajar|Ensinar|Entender|Estimular|Examinar|Exercitar|Explorar|Facilitar|Familiarizar-se|Favorecer|Fomentar|Fortalecer|Identificar|Incentivar|Incorporar|Integrar|Interpretar|Investigar|Levar|Motivar|Oferecer|Permitir|Pesquisar|Planejar|Preparar|Produzir|Promover|Propiciar|Proporcionar|Propocionar|Provocar|Realizar|Reconhecer|Reduzir|Refletir|Registrar|Relacionar|Saber|Sensibilizar|Simular|Trabalhar|Traçar|Transformar|Utilizar|Valorizar|Vivenciar|Adaptar|Ampliar|Alertar|Auxiliar|Mostrar|Abordar'
STRUCTURAL='COMPETÊNCIA ESPECÍFICA|Competência [0-9]|Finalidade:|OBJETIVO GERAL:|OBJETIVOS ESPECÍFICOS:|Objetivo Geral|Objetivo Específico|Ao fim da eletiva|Ao final da eletiva|Os objetivos da|Objetiva- se|Planejamento de Estudos|Desenvolvimento de Novas|Exploração de Novos|Integração com o Cotidiano|Estes  objetivos|Atitudes/Valores \(Ser\)' 
PREFIX=r'(?:(?:Gerais:|Específicos:|Conhecimentos \(Saber\)|Habilidades \(Saber Fazer\))\s*)?'
START=re.compile(r'(?m)^[ \t]*(?:[-•●]\s*|\d{1,2}\.\s*)?'+PREFIX+r'(?:'+ACTIONS+'|'+STRUCTURAL+r')\b')
PURPOSE=re.compile(r'^(?:Promover|Estimular|Ampliar|Apresentar|Incentivar|Levar|Favorecer|Contribuir|Despertar|Proporcionar|Propocionar|Provocar|Alertar|Encorajar|Facilitar|Capacitar|Conectar|Motivar|Fomentar|Transformar|Oferecer|Educar|Reduzir Riscos|Sensibilizar|Mostrar|Propiciar|Consolidar|Permitir|Ensinar|Fortalecer|Preparar|Auxiliar|Abordar)\b')
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n');t.replace(p)
def classify(text):
    content=re.sub(r'^(?:[-•●]\s*|\d{1,2}\.\s*)','',text).strip();content=re.sub(r'^(?:Gerais:|Específicos:)\s*','',content)
    if re.match(r'COMPETÊNCIA ESPECÍFICA',content):return 'competencia_especifica'
    if re.match(r'Competência [0-9]',content):return 'competencia_geral'
    if re.match(r'(?:OBJETIVO GERAL:|OBJETIVOS ESPECÍFICOS:|Objetivo Geral|Objetivo Específico|Planejamento de Estudos|Desenvolvimento de Novas|Exploração de Novos|Integração com o Cotidiano|Os objetivos da|Estes  objetivos|Ao final da eletiva|Atitudes/Valores \(Ser\))',content):return 'secao_normativa'
    if PURPOSE.match(content)or content.startswith(('Finalidade:','Objetiva- se')):return 'objetivo_formativo'
    return 'objetivo_aprendizagem'
def main():
    census=json.loads((BASE/'eletivas-primary-field-census.json').read_text());source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==census['source_id']);path=ROOT/source['local_path'];assert sha(path.read_bytes())==census['artifact_sha256']==source['sha256'];doc=fitz.open(path)
    records=[];unit_census=[];fields=[f for f in census['physical_fields']if f['label']!='COMPETENCIA GERAL'];projects=census['projects'];projectmap={(p['code'],p['page']):p for p in projects}
    assert len(projects)==43 and len(fields)==126
    def add(key,parent,kind,text,page,bounds,project=None,context=None):
        area=project['area'].strip()if project and project.get('area')else None
        e={'source_id':source['id'],'page':page,'printed_page':None,'section':key,'excerpt':text,'bbox':bounds,'locator':'ro-eletivas:'+key,'method':'primary-stroked-field-native-sort-v1'}
        r={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':None,'text':text,'page':page,'locator':e['locator'],'positions':[{'stage':'EM','component':'Eletivas','area':area,'years':None,'year_label':None,'age_group':None,'period':None}],'evidence':[e],'source_context':context or {},'actor_type':'automated','actor_id':'curriculos-abertos:ro-eletivas-primary-audit','technical_validation_status':'literal_full_field_and_project_header_checked_semantic_review_not_claimed'};records.append(r);return r
    rootbounds=[139.0,325.0,913.0,973.0];add('eletivas-root',None,'grupo_curricular',doc[0].get_text('text',clip=fitz.Rect(rootbounds),sort=True).strip(),1,rootbounds)
    for p in projects:
        key=f'projeto-{p["code"]}-p{p["page"]}';p['key']=key
        add(key,'eletivas-root','grupo_curricular',p['title'],p['page'],p['title_bbox'],p,{'printed_project_identifier':p['code'],'project_code_is_not_a_learning_code':True,'code_evidence':{'page':p['page'],'bbox':p['code_bbox'],'text':p['code']},'area_evidence':{'page':p['page'],'bbox':p['area_bbox'],'text':p['area']}})
    fieldordinal=collections.Counter()
    for f in fields:
        p=projectmap[(f['project_code'],f['project_page'])];fieldordinal[(p['key'],f['label'])]+=1;key=p['key']+'-campo-'+str(fields.index(f)+1)
        assert doc[f['page']-1].get_text('text',clip=fitz.Rect(f['bbox']),sort=True).strip()==f['text']
        add(key,p['key'],'secao_normativa',f['text'],f['page'],f['bbox'],p,{'literal_field_label':f['label'],'label_evidence':{'page':f['page'],'bbox':f['label_bbox'],'text':f['label']},'field_is_context_not_a_second_learning_denominator':True})
        if not f['label'].startswith('OBJETIVO'):continue
        matches=list(START.finditer(f['text']));assert matches,(p['code'],'no explicit objective boundary')
        starts=sorted(set([0,*[m.start()for m in matches]]));units=[]
        for i,start in enumerate(starts):
            end=starts[i+1]if i+1<len(starts)else len(f['text']);literal=f['text'][start:end].strip()
            if not literal:continue
            kind=classify(literal);unitkey=key+'-unidade-'+str(len(units)+1)
            add(unitkey,key,kind,literal,f['page'],f['bbox'],p,{'literal_field_label':f['label'],'native_character_start':f['text'].find(literal,start),'native_character_end':f['text'].find(literal,start)+len(literal),'organizational_purposes_kept_out_of_student_learning_denominator':kind=='objetivo_formativo','classification_method':'literal_source_objective_field; explicit organizational-purpose verbs separated; automated classification without pedagogical review','no_school_year_inferred_from_project_or_cited_skill_code':True})
            units.append({'key':unitkey,'start':start,'end':end,'kind':kind,'text_sha256':sha(literal.encode())})
        assert re.sub(r'\s','',f['text'])==''.join(re.sub(r'\s','',records[-len(units)+i]['text'])for i in range(len(units)))
        unit_census.append({'project':p['code'],'page':f['page'],'field_key':key,'bbox':f['bbox'],'field_sha256':f['text_sha256'],'units':units})
    destination=ROOT/'data/manifests/uncoded/ro-eletivas-objectives-primary.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    adapter={'source_id':source['id'],'artifact_sha256':source['sha256'],'generated_at':generated,'actor_type':'automated','actor_id':'curriculos-abertos:ro-eletivas-primary-audit','method':'All43actualprojectheaders,126mainphysicalfields,41objectivefieldswithcompletebodycoverage. No project identifier or citedcode convertedintoanuncodedlearningcode. Contextfields do not duplicate learning denominator.','expected_inventory':{'projects':43,'objective_fields':41,'competency_fields':42,'skill_fields':43,'field_count':126},'items':records};dump(destination,adapter)
    proposed={**source,'uncoded_items_path':str(destination.relative_to(ROOT))};sys.path.insert(0,str(ROOT/'pipeline'));import ingest
    from validate_artifact import validators
    extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in [1,*range(24,118)]]}
    finalized=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:extracted}),[proposed]);assert len(finalized)==len(records)
    schema=validators(ROOT);errors=[(r['id'],e.message)for r in finalized for e in schema['Learning'].iter_errors(r)];assert not errors,errors[:10]
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(records),'kinds':dict(collections.Counter(r['kind']for r in records)),'objective_units':unit_census,'later_primary_census_correction':json.loads((BASE/'eletivas-field-census-correction.json').read_text())if(BASE/'eletivas-field-census-correction.json').exists()else None,'full_objective_fields':41,'all_primary_fields':126,'actual_projects':43,'real_finalizer_schema_records':len(finalized),'binding_ready':True,'ready':False,'reconciled':False,'remaining_scope':['Coded skills remain in generic extraction: full statement and cited-reference reconciliation pending.','Competency fields preserved completely as source context; multiple competency units, source-mislabeled purposes and quotations require full typed reconciliation.','Knowledge objects, axis fields, methodological context, rubrics and introductory normative structure still require complete typed review.','Automated objective classification is not human pedagogical review; organizational purposes remain separate from learner goals.'],'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_eletivas_objectives.py'}
    dump(BASE/'eletivas-objectives-primary-report.json',report);dump(BASE/'ro-eletivas-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':{'uncoded_items_path':str(destination.relative_to(ROOT))},'binding_ready':True,'ready':False,'reconciled':False})
    print(json.dumps({k:report[k]for k in ['adapter_sha256','records','kinds','full_objective_fields','real_finalizer_schema_records']},ensure_ascii=False))
if __name__=='__main__':main()
