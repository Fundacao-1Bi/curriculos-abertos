#!/usr/bin/env python3
"""Declare physical target fields before generating canonical sidecars."""
import json,re,unicodedata,collections
from pathlib import Path
OUT=Path(__file__).resolve().parent

def norm(t):return re.sub(r'\s+',' ',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode()).casefold().strip(' :')
def same(a,b):return abs(a-b)<1.2
LABELS={'modulo':'modulo_curricular','unidade curricular':'unidade_curricular','serie':'ano_escolar','trimestre':'periodo_curricular','semestre':'periodo_curricular','componente':'componente_curricular','area do conhecimento':'area_conhecimento','area de conhecimento':'area_conhecimento','eixo(s) estruturantes(s)':'eixo_estruturante','eixo(s) estruturante(s)':'eixo_estruturante','eixo estruturante':'eixo_estruturante','eixos estruturantes':'eixo_estruturante','objetos de conhecimento':'objeto_conhecimento','objeto de conhecimento':'objeto_conhecimento','temas integradores':'tema_integrador','sugestoes metodologicas':'orientacao_metodologica','orientacoes metodologicas':'orientacao_metodologica','avaliacao':'criterio_avaliacao','perfil do egresso':'contexto_curricular','tipo de unidade curricular sugerida':'estrutura_curricular','ch semanal':'metadado_documental','c.h semanal':'metadado_documental','carga horaria':'metadado_documental'}
def role(t):
 n=norm(t)
 if re.fullmatch(r'objetivos?(?: do)?(?: itinerari\s*o| itinerario| aprofundamento)?',n):return 'objetivo_trilha'
 if re.fullmatch(r'competencias?(?: do ifa)?',n)and'ifa'in n:return 'competencia_especifica'
 
 if re.fullmatch(r'modulo(?: [ivx]+)?',n):return 'modulo_curricular'
 if re.fullmatch(r'possibilidades? (?:de )?avaliacao',n)or n=='possibilidadede avaliacao':return 'criterio_avaliacao'
 if re.fullmatch(r'possibilidades? metodologicas',n):return 'orientacao_metodologica'
 if re.fullmatch(r'(?:(?:possibilidades?|possiblidades?) (?:de )?)?temas? integrador(?:es)?',n):return 'tema_integrador'
 if re.fullmatch(r'(?:sugestoes de )?materia(?:l|is) de apoio',n):return 'referencia_bibliografica'
 if n=='formacao dos professores que poderao atuar na uc':return 'formacao_docente'
 return LABELS.get(n)
reports=[]
for f in sorted(OUT.glob('*-physical-cells.json')):
 d=json.loads(f.read_text());fields=[];headers=[];coverage=[]
 for pp in d['pages']:
  cells=pp['cells'];pn=pp['page'];used=set()
  for i,c in enumerate(cells):
   cr=role(c['text']);box=c['bbox'];n=norm(c['text'])
   peers=[x for x in cells if x is not c and same(x['bbox'][1],box[1])and same(x['bbox'][3],box[3])and role(x['text'])]
   matrix_column=bool(cr in {'unidade_curricular','objeto_conhecimento','estrutura_curricular','eixo_estruturante'}and peers)
   embedded='modulo_curricular'if re.match(r'^M[ÓO]DULO\s+[IVX]+\s*[-–—:]',c['text'],re.I)else'ano_escolar'if re.fullmatch(r'serie:\s*[123][ao]?',n)else'periodo_curricular'if re.match(r'^periodo:\s*.+',n)else None
   if embedded:fields.append({'page':pn,'field_role':embedded,'label':c,'body':c,'mode':'explicit_caption_with_value'})
   chemistry_guard=(d['source_id']=='es-ifa-cntmat'and d['artifact_sha256']=='e0600fd2fe84e7a62a79fea438a541fabc59adece3307fa6aa6694695f482f0a'and pn in(136,139))or(d['source_id']=='es-ifa-das-quatro-areas-do-conhecimento-finalizado'and d['artifact_sha256']=='8a3c14dfec03ceecaa4925b2fa51f53f737adffda40dc5a71e59b2490b125d0f'and pn in(258,261))
   if chemistry_guard and n=='quimica'and box[0]<50:
    fields.append({'page':pn,'field_role':'componente_curricular','label':c,'body':c,'mode':'explicit_component_name_in_original_form_label_column'})
    peers_right=[x for x in cells if same(x['bbox'][0],box[2])and same(x['bbox'][1],box[1])and same(x['bbox'][3],box[3])]
    if peers_right:fields.append({'page':pn,'field_role':'trilha_aprofundamento','label':c,'body':peers_right[0],'mode':'explicit_chemistry_form_part_title'})
   if re.match(r'^\s*Compet[eê]ncia\s+\d+[.:]?\s*\n',c['text'],re.I)and len(norm(c['text']))>35:
    first=c['text'].splitlines()[0];fields.append({'page':pn,'field_role':'competencia_especifica','label':{'bbox':box,'text':first},'body':c,'mode':'explicit_competency_heading_in_own_bounded_cell'});used.add(i)
   if cr and not matrix_column:
    right=[(j,x)for j,x in enumerate(cells)if same(x['bbox'][1],box[1])and same(x['bbox'][3],box[3])and same(x['bbox'][0],box[2])]
    if right:
     j,body=min(right,key=lambda z:z[1]['bbox'][0]);fields.append({'page':pn,'field_role':cr,'label':c,'body':body,'mode':'explicit_row_label'});used.add(j)
    else:
     containing=[(j,x)for j,x in enumerate(cells)if x['bbox'][1]<=box[1]+1 and x['bbox'][3]>=box[3]-1 and same(x['bbox'][0],box[2])]
     if containing:
      j,whole=min(containing,key=lambda z:z[1]['bbox'][0]);fields.append({'page':pn,'field_role':cr,'label':c,'body':{'bbox':[whole['bbox'][0],box[1],whole['bbox'][2],box[3]],'text':None},'mode':'explicit_left_label_band_inside_merged_right_cell','merged_right_cell':whole})
   n=norm(c['text'])
   if n=='objetivo do eixo' or n in ('competencias','competencias gerais') or n=='habilidades' or n.startswith('competencias especificas da area') or matrix_column:
    # Only explicit column headers, never mentions inside body paragraphs.
    if len(c['text'])<110:
     kind=cr if matrix_column else'objetivo_formativo'if n=='objetivo do eixo'else'competencia_geral'if n=='competencias gerais'else'competencia_especifica'if n.startswith('competencias')else'habilidade_local_sem_codigo'
     headers.append({'page':pn,'role':kind,'cell':c})
     for j,b in enumerate(cells):
      bb=b['bbox']
      if bb[1]>=box[3]-1 and same(bb[0],box[0])and same(bb[2],box[2]) and norm(b['text'])!=n and j not in used and not role(b['text']):
       # Header retains its column only until an explicit replacement header at the same bounds.
       intervening=any(x['bbox'][1]>box[1]+1 and x['bbox'][1]<bb[1]-1 and same(x['bbox'][0],box[0])and same(x['bbox'][2],box[2]) and norm(x['text'])in('competencias','habilidades','base tecnologica','objetivo do eixo')for x in cells)
       if intervening:continue
       # Coded entries already belong to the coded adapter and are not recast as uncoded objectives.
       if re.match(r'\s*\(?(?:EMIF|EM\d|EF\d|EI\d)',b['text']):
        coverage.append({'page':pn,'bbox':bb,'role':kind,'status':'coded_field_not_uncoded_leaf','text_sha256':__import__('hashlib').sha256(b['text'].encode()).hexdigest()});continue
       fields.append({'page':pn,'field_role':kind,'label':c,'body':b,'mode':'explicit_column_header'});used.add(j)
  # Structural full-width titles and literal axis names neighboring objective cells are separately auditable.
  for target in [x for x in fields if x['page']==pn]:
   bb=target['body']['bbox'];sibs=[x for x in cells if same(x['bbox'][1],bb[1])and same(x['bbox'][3],bb[3])and same(x['bbox'][2],bb[0])]
   if target['field_role']=='objetivo_formativo'and sibs:target['axis_name']=sibs[-1]
  coverage.append({'page':pn,'physical_cells':len(cells),'target_fields':sum(x['page']==pn for x in fields)})
 # Deduplicate fields physically, preferring explicit row-label authority.
 unique={}
 for q in sorted(fields,key=lambda x:x['mode']!='explicit_row_label'):
  unique.setdefault((q['page'],tuple(q['body']['bbox'])),q)
 fields=list(unique.values());
 if d['source_id']=='es-em-ept-integrado':fields=[] # Entire EPT scope delegated to source-specific primary column/continuation inventory.

 if any(q['body']['text'] is None for q in fields):
  import sys;sys.path.insert(0,str(OUT.parents[3]/'pipeline'));import pymupdf as fitz
  from geometry import normalize_native_page
  root=OUT.parents[3];ss=next(s for s in json.loads((root/'data/manifests/bncc-southeast.json').read_text())if s['id']==d['source_id']);D=fitz.open(root/ss['local_path'])
  for q in fields:
   if q['body']['text'] is None:
    page=D[q['page']-1];normalize_native_page(page);
    from physical_cells import field_content,bind_source_page
    bind_source_page(ss,page,q['page'])
    q['body'].update(field_content(page,q['body']['bbox']))
 result={'source_id':d['source_id'],'artifact_sha256':d['artifact_sha256'],'document_pages':d['document_pages'],'physical_cell_count':d['cell_count'],'fields':fields,'field_count':len(fields),'by_role':dict(collections.Counter(x['field_role']for x in fields)),'coded_field_exclusions':coverage,'method':'Inventory from explicit primary vector-bounded row labels and column headers; no cached parser output. Classification precedes item generation.'}
 (OUT/(d['source_id']+'-target-fields.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');reports.append({k:result[k]for k in('source_id','artifact_sha256','document_pages','physical_cell_count','field_count','by_role')})
(OUT/'target-field-summary.json').write_text(json.dumps({'sources':reports,'field_count':sum(x['field_count']for x in reports),'by_role':dict(sum((collections.Counter(x['by_role'])for x in reports),collections.Counter()))},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(json.loads((OUT/'target-field-summary.json').read_text()),ensure_ascii=False,indent=2))
