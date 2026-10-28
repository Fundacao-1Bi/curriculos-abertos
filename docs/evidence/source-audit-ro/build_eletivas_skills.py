#!/usr/bin/env python3
"""Add complete local statements from all43skill fields and all332code occurrences."""
import collections,copy,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from validate_artifact import validators
from build_eletivas_objectives import ACTIONS,dump
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADS=re.compile(r'(?m)^[ \t]*(?:Habilidades socioemocionais e transversais|Habilidades de Autonomia e Escolha \(Cognitivas\)|Habilidades Práticas e Culinárias \(Técnicas\)|Habilidades Socioemocionais e Globais|Habilidades Sociais e Culturais|Habilidades relacionadas as competências gerais da BNCC:|Habilidades Específicas dos Itinerários Formativos Associadas aos Eixos\nEstruturantes\.|Investigação científica|Processos criativos|Mediação e intervenção sociocultural|Empreendedorismo|LINGUAGENS|CIÊNCIAS HUMANAS|GEOGRAFIA)[ \t]*$')
CAPABILITY_LABELS=['Análise Crítica de Rótulos','Planejamento de Cardápios','Diferenciação de Alimentos','Técnicas de Preparo Saudável','Aproveitamento Integral','Gestão  de  Cozinha','Autogestão e Autocuidado','Consciência Ambiental e Sustentabilidade','Pensamento  Crítico  sobre  Mídia','Valorização da Cultura Alimentar','Trabalho em Equipe','Autoconhecimento e autorregulação','Colaboração e empatia','Pensamento crítico e autonomia']
UNCODED=re.compile(r'(?m)^[ \t]*(?:'+ACTIONS+r'|Agir|Comunicar|Confeccionar|Organizar|Anotar|Associar|Perceber|Pensamento crítico e resolução de problemas|Habilidades técnicas e digitais|Trabalho em equipe e colaboração|Criatividade e inovação|'+ '|'.join(re.escape(x)for x in CAPABILITY_LABELS)+r')\b')
def main():
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']=='ro-eletivas-2026');path=ROOT/source['local_path'];assert sha(path.read_bytes())==source['sha256'];doc=fitz.open(path)
    base=json.loads((ROOT/'data/manifests/uncoded/ro-eletivas-objectives-primary.json').read_text());assert len(base['items'])==415
    adapter=copy.deepcopy(base);records=adapter['items'];census=json.loads((BASE/'eletivas-primary-field-census.json').read_text());allfields=census['physical_fields'];fields=[f for f in allfields if f['label'].startswith('HABILIDADE')];assert len(fields)==43
    projects=census['projects'];projectmap={(p['code'],p['page']):p for p in projects};keymap={r['key']:r for r in records};field_units=[];coded_counter=collections.Counter();reference_counter=collections.Counter();code_fields=collections.defaultdict(list)
    def add(key,parent,kind,text,page,bounds,project,code=None,context=None,code_bounds=None):
        p=keymap[parent]['positions'];e={'source_id':source['id'],'page':page,'printed_page':None,'section':key,'excerpt':text,'bbox':bounds,'locator':'ro-eletivas:'+key,'method':'complete-local-skill-field-native-sort-v1'}
        r={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':text,'page':page,'locator':e['locator'],'positions':copy.deepcopy(p),'evidence':[e],'source_context':context or {},'actor_type':'automated','actor_id':'curriculos-abertos:ro-eletivas-primary-audit','technical_validation_status':'complete_primary_skill_field_and_local_literal_identifier_checked'}
        if code is not None:
            assert code_bounds is not None;r['evidence'].append({'source_id':source['id'],'page':page,'printed_page':None,'section':key,'excerpt':code,'bbox':code_bounds,'locator':e['locator']+':code','method':'primary-literal-code-glyphs','evidence_role':'code_locator'})
        records.append(r);keymap[key]=r;return r
    for f in fields:
        field_number=allfields.index(f)+1;p=projectmap[(f['project_code'],f['project_page'])];parent=f'projeto-{p["code"]}-p{p["page"]}-campo-{field_number}';native=doc[f['page']-1].get_text('text',clip=fitz.Rect(f['bbox']),sort=True).strip();assert native==f['text']==keymap[parent]['text'];code_fields[f['page']].append(f['bbox'])
        events=[]
        for m in ingest.CODE_ANY.finditer(native):events.append((m.start(),m.end(),'code',m.group()))
        for m in HEADS.finditer(native):events.append((m.start(),m.end(),'heading',None))
        # Two fields have uncoded learning after the last coded statement, with
        # no separate native heading. These literal source starts delimit it.
        if f['project_code']=='CNT6':
            target='Explorar a importância da diversidade';start=native.index(target);events.append((start,start,'uncoded',None))
        events.sort();units=[];code_ordinals=collections.Counter()
        def save_uncoded(text,start,end):
            starts=sorted(set([0,*[m.start()for m in UNCODED.finditer(text)]]))
            for i,a in enumerate(starts):
                b=starts[i+1]if i+1<len(starts)else len(text);literal=text[a:b].strip()
                if not literal:continue
                kind='habilidade_local_sem_codigo'
                if literal in ['Pensamento crítico e resolução de problemas','Habilidades técnicas e digitais','Trabalho em equipe e colaboração','Criatividade e inovação']:kind='capacidade'
                key=parent+'-sem-codigo-'+str(len(units)+1);add(key,parent,kind,literal,f['page'],f['bbox'],p,context={'literal_field_label':f['label'],'no_generated_official_code':True});units.append({'key':key,'text_sha256':sha(literal.encode()),'kind':kind})
        if not events:save_uncoded(native,0,len(native))
        else:
            prefix=native[:events[0][0]].strip()
            if prefix:save_uncoded(prefix,0,events[0][0])
            for i,(start,after,role,code)in enumerate(events):
                end=events[i+1][0]if i+1<len(events)else len(native);literal=native[start:end].strip()
                if role=='heading':
                    heading=native[start:after].strip();key=parent+'-rotulo-'+str(len(units)+1);add(key,parent,'grupo_curricular',heading,f['page'],f['bbox'],p);units.append({'key':key,'text_sha256':sha(heading.encode()),'kind':'grupo_curricular'})
                    tail=native[after:end].strip()
                    if tail:save_uncoded(tail,after,end)
                elif role=='uncoded':save_uncoded(literal,start,end)
                else:
                    body=re.sub(r'^[\s)\]\-–—:]+','',native[after:end]).strip();assert body,(f['project_code'],code,'missing statement')
                    bounds=[r for r in doc[f['page']-1].search_for(code)if fitz.Rect(f['bbox']).contains(r.tl+(r.br-r.tl)*.5)];assert bounds
                    # Each printed code appears once in its skill field; duplicates
                    # across cards/pages remain distinct documentary occurrences.
                    assert len(bounds)==sum(1 for m in ingest.CODE_ANY.finditer(native)if m.group()==code),(f['project_code'],code,'glyph count differs');bounds=sorted(bounds,key=lambda r:(r.y0,r.x0));ordinal=code_ordinals[code];code_ordinals[code]+=1
                    key=parent+'-codigo-'+str(len(units)+1)+'-'+code;add(key,parent,'habilidade',body,f['page'],f['bbox'],p,code=code,code_bounds=list(bounds[ordinal]),context={'printed_local_identifier':code,'statement_scope':'local_source_statement_with_printed_identifier','national_canonical_text_identity_verified':False,'semantic_equivalence_claimed':False,'no_code_alias_or_spelling_repair':True,'source_year_not_inferred_from_identifier':True});units.append({'key':key,'text_sha256':sha(body.encode()),'kind':'habilidade','code':code});coded_counter[(f['page'],code)]+=1
        field_units.append({'page':f['page'],'project':p['code'],'field_key':parent,'bbox':f['bbox'],'native_sha256':sha(native.encode()),'units':units})
    # Code-only mentions in knowledge-object cards and the CNT9 activity table
    # remain documentary references; no statement or equivalence is fabricated.
    native_counter=collections.Counter((pn,m.group())for pn in range(24,118)for m in ingest.CODE_ANY.finditer(doc[pn-1].get_text()))
    missing=native_counter-coded_counter;assert sum(native_counter.values())==332 and sum(coded_counter.values())==274
    for (pn,code),count in missing.items():
        p=max((p for p in projects if p['page']<=pn),key=lambda p:p['page']);parent=f'projeto-{p["code"]}-p{p["page"]}'
        bounds=[r for r in doc[pn-1].search_for(code)if not any(fitz.Rect(rect).contains(r.tl+(r.br-r.tl)*.5)for rect in code_fields[pn])];assert len(bounds)==count,(pn,code,len(bounds),count)
        for i,rect in enumerate(sorted(bounds,key=lambda r:(r.y0,r.x0))):
            key=f'{parent}-referencia-p{pn}-{code}-{i+1}';add(key,parent,'referencia_no_documento',code,pn,list(rect),p,code=code,code_bounds=list(rect),context={'role':'code_only_reference_in_knowledge_objects_or_activity_table','no_full_learning_statement_at_this_occurrence':True,'semantic_equivalence_claimed':False,'source_year_not_inferred_from_identifier':True});reference_counter[(pn,code)]+=1
    assert coded_counter+reference_counter==native_counter
    destination=ROOT/'data/manifests/uncoded/ro-eletivas-skill-fields-v2.json';adapter['method']='Preserves415objective/context records; adds all43physical skill fields,274literal local coded statements,58code-only references and uncoded capabilities with complete field character coverage. No local wording or printed identifier is normalized to national text.';adapter['expected_inventory']={**base['expected_inventory'],'skill_field_coded_statement_occurrences':274,'code_only_reference_occurrences':58,'all_primary_code_occurrences_pages24_117':332};dump(destination,adapter)
    proposed={**source,'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':{**source.get('adapter_authority',{}),'coded_learning_pages':[24,117]}};extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':pn,'text':doc[pn-1].get_text('text',sort=True)}for pn in [1,*range(24,118)]]}
    finalized=ingest.finalize_items(ingest.source_uncoded_items([proposed],{source['id']:extracted}),[proposed]);assert len(finalized)==len(records);schema=validators(ROOT);errors=[(r['id'],e.message)for r in finalized for e in schema['Learning'].iter_errors(r)];assert not errors,errors[:8]
    report={'source_id':source['id'],'source_sha256':source['sha256'],'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(records),'kinds':dict(collections.Counter(r['kind']for r in records)),'base415_preserved':records[:415]==base['items'],'skill_fields':field_units,'coded_statements':274,'code_only_references':58,'all_primary_code_occurrences':332,'real_finalizer_schema_records':len(finalized),'ready':False,'reconciled':False,'binding_ready':False,'remaining_scope':['Full competency-field atomization, objects/axis/context/rubric and introductory chapter structure still pending.','Independent saved-file complete skill-field character readback must pass before binding.'],'engine':{'python':sys.version,'pymupdf':fitz.VersionBind},'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_eletivas_skills.py'};dump(BASE/'eletivas-skills-primary-report.json',report);dump(BASE/'ro-eletivas-skills-proposed-source-fields.json',{'source_id':source['id'],'artifact_sha256':source['sha256'],'adapter_sha256':report['adapter_sha256'],'fields':{'uncoded_items_path':str(destination.relative_to(ROOT)),'adapter_authority':proposed['adapter_authority']},'binding_ready':False,'ready':False,'reconciled':False});print(json.dumps({k:report[k]for k in ['adapter_sha256','records','kinds','coded_statements','code_only_references','real_finalizer_schema_records']},ensure_ascii=False))
if __name__=='__main__':main()
