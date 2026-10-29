#!/usr/bin/env python3
"""SC C3 explicitly labelled skill columns, preserving uncoded source text.
Does not infer BNCC codes. Coded cells remain the generic coded parser's scope.
"""
import json,re,hashlib,collections
import fitz
from extract_sc_uncoded import ROOT,SOURCES,words_in,words_text,paragraphs,canonical_text
from extract_sc_em_uncoded import record
from extract_sc_c3_objectives import blocks,heading,apply_heading
SID='sc-cb-em-caderno-3';REV='sc-trilhas-explicit-skill-columns-v1.0.0'
CODE=re.compile(r'\b(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2}|EM\d{2}[A-Z]{3}\d{3}|EMIF[A-Z]{2,5}\d{2,3})\b')
def tables_for(p,pn):
 path=ROOT/f'docs/evidence/source-audit-sc/c3-table-geometry-p{pn}.json'
 if path.exists():return json.loads(path.read_text())
 ts=[{'bbox':list(t.bbox),'rows':[list(r.cells) for r in t.rows]} for t in p.find_tables().tables];path.write_text(json.dumps(ts));return ts
def nominal_heading(p,chunk):
 canonical=canonical_text(chunk['text'])
 if len(canonical)<150 and re.match(r'^(Investigação científica|Processos criativos|Mediação e intervenção sociocultural|Empreendedorismo)(?:\s*[:(]|$)',canonical,re.I):return True
 first=re.sub(r'[^\w-]','',chunk['text'].lstrip('\u001f→•- ').split()[0]).split('-')[0]
 if re.search(r'(ar|er|ir|or|ôr)$',first,re.I):return False
 if not hasattr(p,'_sc_spans'):p._sc_spans=[s for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']]
 spans=[s for s in p._sc_spans if chunk['bbox'][0]-1<=(s['bbox'][0]+s['bbox'][2])/2<=chunk['bbox'][2]+1 and chunk['bbox'][1]-1<=(s['bbox'][1]+s['bbox'][3])/2<=chunk['bbox'][3]+1]
 total=sum(len(re.sub(r'\W','',s['text'])) for s in spans);bold=sum(len(re.sub(r'\W','',s['text'])) for s in spans if 'bold' in s['font'].lower())
 return total>0 and bold/total>0.8
def extract():
 doc=fitz.open(ROOT/SOURCES[SID]['local_path']);items=[];audit=[];seen=set();carry=[];hierarchy={};pending=[]
 for index,p in enumerate(doc):
  pn=index+1
  if pn<21:continue
  if p.rotation:p.remove_rotation()
  before_hierarchy=dict(hierarchy);page_headings=[]
  for b in blocks(p):
   h=heading(b,pn)
   if h and h['level']<=2:
    page_headings.append(h);apply_heading(hierarchy,h)
  heads=[w for w in p.get_text('words') if re.search(r'(?:^|/)Habilidades?(?:$|/)',w[4],re.I)]
  if not heads and not carry:continue
  ts=tables_for(p,pn);targets=[]
  for h in heads:
   hx=(h[0]+h[2])/2;hy=(h[1]+h[3])/2;found=[]
   for ti,t in enumerate(ts):
    for ri,row in enumerate(t['rows']):
     for ci,c in enumerate(row):
      if c and c[0]-1<=hx<=c[2]+1 and c[1]-1<=hy<=c[3]+1:
       txt=words_text(words_in(p,c))
       if re.match(r'^(?:Habilidades?(?:\s|/|$)|Palavras-chave/Habilidades?|Eixos? estruturantes?.*habilidades?)',txt,re.I) and len(txt)<250:found.append((ti,ri,ci,c,txt))
   if found:
    ti,ri,ci,c,txt=min(found,key=lambda v:(v[3][2]-v[3][0])*(v[3][3]-v[3][1]))
    if re.match(r'^Habilidades? relacionadas',txt,re.I) and ci+1<len(ts[ti]['rows'][ri]) and ts[ti]['rows'][ri][ci+1]:
     targets.append({'table':ti,'header_row':ri-1,'only_row':ri,'column':ci+1,'column_bbox':ts[ti]['rows'][ri][ci+1],'header':txt,'header_page':pn,'origin':'explicit_source_skill_row_label'})
    else:targets.append({'table':ti,'header_row':ri,'column':ci,'column_bbox':c,'header':txt,'header_page':pn,'origin':'explicit_source_skill_header'})
  for prior in carry:
   if prior['page']!=pn-1:continue
   for ti,t in enumerate(ts):
    if t['bbox'][1]>130:continue
    if len(t['rows'][0])!=prior['columns']:continue
    row=t['rows'][0]
    for ci,c in enumerate(row):
     if not c or abs(c[0]-prior['column_bbox'][0])>45 or abs(c[2]-prior['column_bbox'][2])>45:continue
     if any(x['table']==ti and abs(x['column_bbox'][0]-c[0])<4 and abs(x['column_bbox'][2]-c[2])<4 for x in targets):continue
     txt=words_text(words_in(p,c))
     if not txt or re.match(r'^(Habilidade|Objeto|Eixo|Unidade|Carga)',txt,re.I):continue
     targets.append({'table':ti,'header_row':-1,'column':ci,'column_bbox':c,'header':prior['header'],'header_page':prior['header_page'],'origin':'continued_source_table_skill_column','continuation_from_page':pn-1});pending.append({'page':pn,'issue':'continued_column_requires_visual_documentary_check','header_page':prior['header_page']});break
  carry=[]
  for target in targets:
   t=ts[target['table']];header=target['column_bbox'];cells=0;records=0;coded=0;table_context=[];unit_meta={};table_hierarchy=dict(before_hierarchy)
   for hb in page_headings:
    if hb['bbox'][1]>=t['bbox'][1]:continue
    apply_heading(table_hierarchy,hb)
   for pri,prow in enumerate(t['rows'][:max(0,target['header_row'])]):
    texts=[canonical_text(words_text(words_in(p,c))) if c else None for c in prow]
    table_context.append({'row':pri,'texts':texts,'cells':prow})
    nonempty=[x for x in texts if x]
    if nonempty and re.match(r'^Unidade\s+[Cc]urricular',nonempty[0]):unit_meta.update(unit_identifier=nonempty[0],unit_title=nonempty[1] if len(nonempty)>1 else None,unit_title_page=pn)
    if nonempty and nonempty[0]=='Carga horária':unit_meta['unit_duration']=nonempty[1] if len(nonempty)>1 else None
   for ri,row in enumerate(t['rows']):
    if ri<=target['header_row']:continue
    if target.get('only_row') is not None and ri!=target['only_row']:continue
    for ci,c in enumerate(row):
     if not c or abs(c[0]-header[0])>4 or abs(c[2]-header[2])>4:continue
     key=(pn,tuple(round(v,2) for v in c))
     if key in seen:continue
     seen.add(key);ws=words_in(p,c);txt=words_text(ws)
     if not txt or re.match(r'^(Habilidades?(?:\s|$)|Fonte:|Quadro\s+\d)',txt,re.I):continue
     if CODE.search(txt):coded+=1;continue
     cells+=1
     context=[{'column':j,'text':canonical_text(words_text(words_in(p,oc))),'bbox':oc} for j,oc in enumerate(row) if oc and j!=ci]
     last_goal=None
     for pi,ch in enumerate(paragraphs(ws)):
      literal=ch['text'].lstrip('\u001f→•- ')
      if not literal:continue
      loc=f'sc-trilhas-skill-table:{target["table"]}/row:{ri}/column:{ci}/paragraph:{pi}'
      ctx={'section':'Trilhas de Aprofundamento','official_code_absent':True,'column_header':target['header'],'column_header_page':target['header_page'],'column_origin':target['origin'],'source_heading_path':list(table_hierarchy.values()),'table_source_context':table_context,'other_source_cells':context,'cell_bbox':c,'unit_grain':'source_typographic_paragraph_in_explicit_skill_column',**unit_meta}
      it=record(SID,pn,loc,literal,ch['bbox'],'Trilhas de Aprofundamento',ctx);it['kind']='habilidade';it['extraction_method']=REV;it['extraction_revision']=REV;it['evidence'][0]['method']=REV
      if re.match(r'^Eixos? estruturantes?',target['header'],re.I) and 'Palavras-chave' in target['header']:
       it['kind']='palavra_chave_habilidade';ctx['classification_note']='A fonte identifica esta coluna como palavras-chave de habilidades; não contada como objetivo completo.'
      for area in ('Ciências humanas e sociais aplicadas','Ciências da natureza e suas tecnologias','Linguagens e suas tecnologias','Matemática e suas tecnologias'):
       if canonical_text(literal).casefold().startswith(area.casefold()+' -'):
        it['positions'][0]['area']=area;it['positions'][0]['position_note']='Área declarada explicitamente no início do parágrafo da fonte; série não atribuída por suposição.';ctx['declared_area_prefix']=area;break
      if nominal_heading(p,ch):
       it['kind']='estrutura_curricular';ctx['classification_note']='Subtítulo nominal em negrito dentro da célula de habilidades, preservado como contexto.';last_goal=None
      elif literal[0].islower() and last_goal and (last_goal['text'].endswith(':') or last_goal['source_context'].get('source_nested_list_fragments_joined')):
       last_goal['evidence']+=it['evidence'];last_goal['text']=canonical_text(' '.join(e['excerpt'] for e in last_goal['evidence']));last_goal['source_context']['source_nested_list_fragments_joined']=True;continue
      elif len(re.sub(r'\W','',literal))<5 and not re.search(r'(ar|er|ir|or|ôr)$',literal,re.I):
       it['kind']='secao_normativa';ctx['source_text_incomplete']=True;ctx['classification_note']='Fragmento curto literalmente truncado na fonte; não completado nem promovido a habilidade.';last_goal=None
      elif literal[0].islower():
       ctx['source_initial_lowercase_preserved']=True;ctx['classification_note']='Parágrafo completo na coluna explícita de habilidades; caixa/minúscula ou falha tipográfica original preservada, sem completar a grafia.';last_goal=it
      else:last_goal=it
      items.append(it);records+=1
   audit.append({'page':pn,**target,'uncoded_cells':cells,'source_records':records,'coded_cells_left_to_coded_parser':coded})
   if t['bbox'][3]>580:
    carry.append({'page':pn,'columns':len(t['rows'][0]),**target})
  print(json.dumps({'page':pn,'targets':len(targets),'records':sum(x['source_records'] for x in audit if x['page']==pn)}),flush=True)
 return items,audit,pending
def main():
 items,audit,pending=extract();review_path=ROOT/'docs/evidence/source-audit-sc/c3-continuation-review.json';review=json.loads(review_path.read_text()) if review_path.exists() else {};reviews={x['page']:x for x in review.get('pairs',[]) if x.get('result') and x.get('actor_type')=='automated'};resolved=[];remaining=[]
 for finding in pending:
  if finding['issue']=='continued_column_requires_visual_documentary_check' and finding['page'] in reviews:resolved.append({**finding,'review':reviews[finding['page']]})
  else:remaining.append(finding)
 for item in items:
  ctx=item['source_context'];pn=item['page']
  if ctx.get('column_origin')=='continued_source_table_skill_column' and pn in reviews:
   ctx['documentary_column_review']=reviews[pn];item['technical_validation_status']='literal_source_geometry_and_documentary_column_role_checked'
   if pn==75:ctx['column_origin']='explicit_caption_and_skill_body_in_new_source_table';ctx['original_detection_origin']='continued_source_table_skill_column';ctx['source_table_caption']=reviews[pn].get('current_page_caption')
 path=ROOT/'data/manifests/uncoded/sc-trilhas-table-items.json';path.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 labelled=json.loads((ROOT/'data/manifests/uncoded/sc-trilhas-items.json').read_text());combined=sorted(labelled+items,key=lambda i:(i['page'],i['locator']));combined_path=ROOT/'data/manifests/uncoded/sc-trilhas-all-items.json';combined_path.write_text(json.dumps(combined,ensure_ascii=False,indent=2)+'\n')
 result={'actor_type':'automated','actor_id':'agent:data_central_south','extraction_revision':REV,'source_id':SID,'artifact_sha256':SOURCES[SID]['sha256'],'adapter_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'combined_adapter_sha256':hashlib.sha256(combined_path.read_bytes()).hexdigest(),'records':len(items),'tables':audit,'resolved_documentary_column_checks':resolved,'pending':remaining,'source_quality_findings':[{'page':232,'literal_fragment':'Prom','result':'fragment_printed_in_original_PDF_incomplete','render':'docs/evidence/source-audit-sc/sc-c3-p232.png','verification':'Original prints only Prom in this bullet; following page starts a different unit. No completion invented.'},{'page':217,'literal_initial':'nvestigar','result':'missing_initial_letter_printed_in_original_PDF','render':'docs/evidence/source-audit-sc/sc-c3-p217.png','verification':'Original spelling preserved as printed, without editorial reconstruction.'}],'scope_limit':'All recognized explicit skill columns, row labels and physically reviewed continuations; coded cells excluded. Broader source parts and independent total normative denominator remain pending; no UF readiness declared.'}
 (ROOT/'docs/evidence/source-audit-sc/c3-table-adapter-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='tables'},ensure_ascii=False))
if __name__=='__main__':main()
