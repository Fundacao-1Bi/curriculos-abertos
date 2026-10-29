#!/usr/bin/env python3
"""Complete MA act partitions, reusing the BA249/RN11123 anchor/line contract.

Physical DOE columns are read in declared Source order; the annex flow table uses
PyMuPDF find_tables and real cells. No global parser or manifest is modified.
"""
from pathlib import Path
import json,re,hashlib,collections,sys
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
REV='ma-normative-original-line-partition-v1.0.0';ACTOR='agent:rs_adapter:ma-normative-adapter'
CONFIGS=[('ma-resolucao-211-2026-doe','ma-211-items.json','resolution-211'),('ma-portaria-181-2026-recomposicao-doe','ma-181-items.json','portaria-181')]
def sha(b):return hashlib.sha256(b).hexdigest()
def source_lines(source,doc):
 lines=[]
 for spec in source['page_regions']:
  for region,box in enumerate(spec['regions']):
   pg=doc[spec['page']-1];local=[]
   for block in pg.get_text('dict',clip=fitz.Rect(box),sort=False)['blocks']:
    for line in block.get('lines',[]):
     t=''.join(s['text'] for s in line['spans']).strip()
     if t:local.append({'page':spec['page'],'region':region,'text':t,'bbox':list(line['bbox'])})
   assert [l['text'] for l in local]==[t.strip() for t in pg.get_text('text',clip=fitz.Rect(box),sort=False).splitlines() if t.strip()]
   lines.extend(local)
 for n,line in enumerate(lines):line['ordinal']=n
 return lines

def build(source,name,rootkey,census):
 doc=fitz.open(ROOT/source['local_path']);assert sha((ROOT/source['local_path']).read_bytes())==source['sha256'];lines=source_lines(source,doc);assert len(lines)==census['source_only_counts']['lines']
 anchors=[];cn=0;annex=False
 for n,l in enumerate(lines):
  t=l['text'];key=kind=number=None
  if n==0:key,kind=rootkey,'ato_normativo'
  elif t.startswith('Aprova o Documento Curricular') or t.startswith('Institui a destinação'):key,kind='ementa','ementa_normativa'
  elif t.startswith('O CONSELHO ESTADUAL DE EDUCAÇÃO') or t.startswith('A SECRETÁRIA DE ESTADO DA EDUCAÇÃO'):key,kind='preamble','preambulo_normativo'
  elif t.startswith('CONSIDERANDO'):cn+=1;key,kind=f'considerando-{cn}','considerando_normativo'
  elif t=='RESOLVE:':key,kind='resolve','dispositivo_deliberativo'
  elif m:=re.fullmatch(r'CAPÍTULO\s+([IVX]+)',t):key,kind,number='chapter-'+m[1],'capitulo_normativo',m[1]
  elif m:=re.match(r'^Art\.\s*(\d+)(?:º|\.)?',t):key,kind,number='article-'+m[1],'artigo_normativo',m[0].strip()
  elif t.startswith('SALA DAS SESSÕES PLENÁRIAS'):key,kind='signature','assinatura_normativa'
  elif t=='DÊ-SE CIÊNCIA.':key,kind='publication-command','comando_publicacao'
  elif t=='JANDIRA DIAS ARAÚJO SILVA':key,kind='signature','assinatura_normativa'
  elif t.startswith('ANEXO ÚNICO'):key,kind,number='annex','anexo_normativo','ANEXO ÚNICO';annex=True
  elif annex and (m:=re.match(r'^(\d+)\.\s+D[AO]S?\s+',t)):key,kind,number='annex-section-'+m[1],'secao_anexo_normativo',m[1]+'.'
  if key:anchors.append({'start':n,'key':key,'kind':kind,'number':number})
 assert anchors[0]['start']==0
 items=[];ownership=collections.Counter();chapter=None;parts=[]
 def emit(key,kind,parent,groups,number=None,context=None):
  nonlocal items
  assert groups and all(g for g in groups)
  evidence=[]
  for g in groups:
   p=g[0]['page'];assert all(l['page']==p and l['region']==g[0]['region'] for l in g)
   excerpt=' '.join(l['text'] for l in g);bbox=[min(l['bbox'][0] for l in g),min(l['bbox'][1] for l in g),max(l['bbox'][2] for l in g),max(l['bbox'][3] for l in g)]
   evidence.append({'source_id':source['id'],'page':p,'printed_page':str(p),'section':key,'excerpt':excerpt,'bbox':bbox,'locator':f'ma-normative/{key}/page-{p}/fragment-{len(evidence)}','method':'document-specific-normative-partition'})
   for l in g:ownership[l['ordinal']]+=1
  text=ingest.clean_text(' '.join(e['excerpt'] for e in evidence));locator='ma-normative/'+key
  evidence[0]['locator']=locator  # Shared sidecar importer preserves the record locator here.
  record={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'code':None,'page':evidence[0]['page'],'locator':locator,'text':text,'kind':kind,'source_number':number,'positions':[{'stage':stage,'component':component,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_document_normative_scope','position_note':'Ato de Educação Básica' if source['id'].startswith('ma-resolucao-211') else 'Ensino Médio Regular em regime parcial; nenhuma série ou período letivo atribuídos.'} for stage in source['stages'] for component in (['Computação'] if source['id'].startswith('ma-resolucao-211') else ['Língua Portuguesa','Matemática'])],'evidence':evidence,'source_context':{'document_type':'ato_normativo','record_grain':'normative_part_not_learning','source_document_order':len(items)+1,'original_line_ordinals':[l['ordinal'] for g in groups for l in g],'jurisdiction_scope':source.get('jurisdiction_scope') or source.get('scope_note'),**(context or {})},'actor_type':'automated','actor_id':ACTOR,'extraction_method':REV,'technical_validation_status':'complete_original_line_partition_checked','expected_final_id':f'ca:{source["id"]}:section:{key}'}
  if source['id'].startswith('ma-portaria-181'):
   record['source_context']['position_scope_basis']={'source_item_keys':['ementa','article-1','annex-section-1'],'scope_rule':'Âmbito explícito do ato para Língua Portuguesa e Matemática; não constitui nova habilidade ou equivalência.'}
  items.append(record);parts.append({'key':key,'kind':kind,'parent_key':parent,'source_number':number,'line_ordinals':record['source_context']['original_line_ordinals'],'pages':list(dict.fromkeys(e['page'] for e in evidence)),'fragment_count':len(evidence),'text_sha256':sha(text.encode())})
 def groups_for(ll):
  grouped=collections.OrderedDict()
  for l in ll:grouped.setdefault((l['page'],l['region']),[]).append(l)
  return list(grouped.values())
 for pos,a in enumerate(anchors):
  end=anchors[pos+1]['start'] if pos+1<len(anchors) else len(lines);ll=lines[a['start']:end];key,kind=a['key'],a['kind'];parent=None if key==rootkey else rootkey
  if kind=='capitulo_normativo':chapter=key
  if kind=='artigo_normativo':parent=chapter or 'resolve'
  if kind=='secao_anexo_normativo':parent='annex'
  if key=='annex-section-15':
   t=next(t for t in doc[35].find_tables().tables if t.row_count==8 and t.col_count==3 and 200<t.bbox[1]<240);box=fitz.Rect(t.bbox)
   body=[l for l in ll if box.contains(fitz.Point((l['bbox'][0]+l['bbox'][2])/2,(l['bbox'][1]+l['bbox'][3])/2))];heading=[l for l in ll if l not in body];emit(key,kind,parent,groups_for(heading),a['number'])
   labels=[' '.join(c.split()) for c in t.extract()[0]]
   assigned=[]
   for rown,row in enumerate(t.rows):
    cellgroups=[]
    for ci,cell in enumerate(row.cells):
     rect=fitz.Rect(cell);cc=[l for l in body if rect.contains(fitz.Point((l['bbox'][0]+l['bbox'][2])/2,(l['bbox'][1]+l['bbox'][3])/2))];assert cc;(assigned.extend(l['ordinal'] for l in cc));cellgroups.append(cc)
    rk='annex-flow-table' if rown==0 else f'annex-flow-row-{rown}';typ='quadro_normativo' if rown==0 else 'etapa_fluxo_pedagogico';rp=key if rown==0 else 'annex-flow-table'
    emit(rk,typ,rp,cellgroups,None if rown==0 else str(rown)+'.',{'table_page':36,'table_bbox':list(t.bbox),'row_index':rown,'column_labels':labels,'cell_values':[' '.join(l['text'] for l in g) for g in cellgroups],'table_grain':'Pedagogical planning flow, not curricular skills or learning objectives'})
   assert sorted(assigned)==sorted(l['ordinal'] for l in body) and len(set(assigned))==len(assigned)
  else:emit(key,kind,parent,groups_for(ll),a['number'])
 expected=set(range(len(lines)));assert set(ownership)==expected and all(n==1 for n in ownership.values())
 assert ingest.normalize(' '.join(l['text'] for l in lines))==ingest.normalize(' '.join(i['text'] for i in items))
 bykey={i['key']:i for i in items};assert len(bykey)==len(items)
 for i in items:
  parent=i['parent_key'];seen={i['key']}
  while parent:assert parent in bykey and parent not in seen;seen.add(parent);parent=bykey[parent]['parent_key']
 pages={}
 for spec in source['page_regions']:
  pages[spec['page']]='\n'.join(doc[spec['page']-1].get_text(clip=fitz.Rect(b)) for b in spec['regions'])
 extracted={'source_id':source['id'],'sha256':source['sha256'],'pages':[{'page':p,'text':t} for p,t in pages.items()]}
 for i in items:assert ingest.evidence_check(i,extracted,doc),i['key']
 path=ROOT/'data/manifests/uncoded'/name;path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 return {'source_id':source['id'],'artifact_sha256':source['sha256'],'sidecar_path':str(path.relative_to(ROOT)),'sidecar_sha256':sha(path.read_bytes()),'actor_type':'automated','adapter_revision':REV,'source_line_count':len(lines),'exact_once_line_ownership':True,'canonical_normalized_partition_equals_source':True,'counts_by_kind':dict(collections.Counter(i['kind'] for i in items)),'records':len(items),'literal_fragments':sum(len(i['evidence']) for i in items),'parts':parts,'multi_page_or_column_parts':[p for p in parts if p['fragment_count']>1],'source_only_census_path':'docs/evidence/source-audit-ma-current/ma-normative-source-census.json','scope_limit':'Complete selected act/annex partition only; importer/finalizer and full candidate incorporation are separate checks.'}
def main():
 census=json.loads((OUT/'ma-normative-source-census.json').read_text());byc={r['source_id']:r for r in census['sources']};ss={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};reports=[build(ss[sid],name,key,byc[sid]) for sid,name,key in CONFIGS];(OUT/'ma-normative-extraction-report.json').write_text(json.dumps({'actor_type':'automated','sources':reports},ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items() if k not in ('parts','multi_page_or_column_parts')} for r in reports],ensure_ascii=False))
if __name__=='__main__':main()
