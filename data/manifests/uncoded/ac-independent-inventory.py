#!/usr/bin/env python3
"""Denominator derived from source TOC and native marker glyphs, not output counts.
The item sidecar is read only after the expected inventory has been built.
"""
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
if sys.version_info<(3,11)or tuple(map(int,fitz.VersionBind.split('.')[:3]))<(1,26,7):
 raise RuntimeError('Use patched Python >=3.11/PyMuPDF >=1.26.7: var/venv-pipeline/bin/python')
ROOT=Path(__file__).resolve().parents[3];AUDIT=ROOT/'docs/evidence/source-audit-ac'
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s)if not unicodedata.combining(c)).casefold()
def write(name,data):(AUDIT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def native(page):
 lines=[]
 for block in page.get_text('dict')['blocks']:
  for line in block.get('lines',[]):
   text=''.join(s['text']for s in line['spans']).strip()
   if text and 60<line['bbox'][1]<530:lines.append({'text':text,'bbox':line['bbox']})
 return sorted(lines,key=lambda r:(round(r['bbox'][1],1),r['bbox'][0]))
def marker(t):return bool(re.match(r'^[•●▪]\s*\S',t))
s=next(x for x in json.loads((ROOT/'data/manifests/north.json').read_text())if x['id']=='ac-cru-ei-ef');D=fitz.open(ROOT/s['local_path']);toc='\n'.join(p.get_text()for p in D[:17]);expected_tables=[]
for m in re.finditer(r'(\d+\.\s*QUADRO ORGANIZADOR[\s\S]{0,350}?)\.{2,}\s*(\d{2,4})',toc,re.I):expected_tables.append({'title':re.sub(r'\s+',' ',m[1]).strip(),'printed_page':int(m[2]),'page':int(m[2])+1})
write('toc-independent-tables.json',expected_tables)
expected=[];contexts=[];parents=[]
# EI: marker glyphs in the two explicit normative subsections, excluding experiences/evaluation.
mode=None;field=None;age=None;parent=None
for p in range(47,135):
 for line in native(D[p-1]):
  t=line['text'];n=norm(t)
  if re.match(r'^\d+\.\s*(?:referencias didaticas para\s*)?(?:bebes|criancas)',n):age=t;mode=None
  if 'campo de experiencias'in n:field=t;mode=None
  if re.match(r'^\d+\.\d+\.\s*Direitos de aprendizagem',t,re.I):mode='ei-rights';contexts.append({'page':p,'role':mode,'title':t,'field':field,'age':age});continue
  if 'objetivo de aprendizagem e desenvolvimento:'in n:
   mode=None;m=re.search(r'\(([A-Z0-9]+)\)',t);parents.append({'page':p,'code':m[1]if m else None,'heading':t,'bbox':line['bbox'],'field':field,'age_group':age});continue
  if n.startswith('aprendizagens especificas'):mode='ei-specific';contexts.append({'page':p,'role':mode,'title':t,'field':field,'age':age});continue
  if re.match(r'^sugest(?:ao|oes) de experiencias',n)or re.match(r'^\d+\.\d+\.\s*(?:avaliacao|referencias)',n):mode=None;continue
  if mode and marker(t):expected.append({'page':p,'category':mode,'bbox':line['bbox'],'text':t,'part':'EDUCAÇÃO INFANTIL','field':field,'age_group':age})
# EF objective glyphs: source TOC establishes pages/tables; slim printed borders bound the first column.
parts=[p for p in s['structure_sections']if p.get('stage')=='EF']
for part in parts:
 starts=[x for x in expected_tables if part['page_start']<=x['page']<=part['page_end']]
 if not starts:continue
 first=min(x['page']for x in starts)
 for pno in range(first,part['page_end']+1):
  p=D[pno-1];lines=native(p)
  borders=[d['rect']for d in p.get_drawings()if d['rect'].width<1.5 and d['rect'].height>10 and 140<d['rect'].x0<210 and d['rect'].y0<530]
  if not borders:continue
  values=collections.Counter(round(r.x0,1)for r in borders);right=min(values,key=lambda x:(-values[x],x))
  stop=min([530]+[l['bbox'][1]for l in lines if re.match(r'^\d+[.\-]?\s*(?:REFERÊNCIAS|BIBLIOGRAFIA)',l['text'],re.I)])
  for l in lines:
   t=l['text'];box=l['bbox']
   if marker(t)and box[0]<right and box[2]<right+1 and 70<=box[1]<stop and not re.match(r'^[•●▪]\s*(?:OBJETIVOS|CAPACIDA|PETENCIAS)',norm(t).upper()):
    # Source TOC/year association is geometric when a table starts after preceding content on the same page.
    table=None
    for candidate in starts:
     if candidate['page']>pno:break
     if candidate['page']<pno:table=candidate;continue
     headers=[h for h in lines if re.match(r'^\d+\.\s*QUADRO ORGANIZADOR\b',h['text'],re.I)]
     if headers and box[1]>headers[0]['bbox'][1]:table=candidate
    expected.append({'page':pno,'category':'ef-objective-column','bbox':box,'text':t,'part':part['title'],'table':table['title']if table else None,'grade':(' / '.join(re.findall(r'([1-9]\s*[º°]\s*ANO)',table['title'],re.I))if table else None)})
 # EF grade rights: derive explicit grade/block contexts directly from the pre-table source, not extracted rows.
 enabled=False;grade=None
 for pno in range(part['page_start'],first):
  for l in native(D[pno-1]):
   t=l['text'];n=norm(t)
   if re.fullmatch(r'[1-9]\s*[º°o]\s*ANOS?',t,re.I):enabled=True;grade=t;contexts.append({'page':pno,'role':'ef-grade-rights','title':grade,'part':part['title']});continue
   if re.match(r'^4\.\d+(?:\.|\s)',t):enabled=False;grade=t;continue
   if re.match(r'^5[.\s]+',t)and'COMPET'in t.upper():enabled=False;continue
   if re.search(r'(?:sejam capazes|capazes de):?\s*$',n):enabled=True;grade=t;contexts.append({'page':pno,'role':'ef-explicit-expectation-block','title':t,'part':part['title']});continue
   if enabled and marker(t):expected.append({'page':pno,'category':'ef-grade-rights','bbox':l['bbox'],'text':t,'part':part['title'],'grade':grade})
# Unmarked source paragraphs were identified by visual/documentary audit. The source location and prefix,
# rather than output counts, define each required paragraph; line continuations are not separate starts.
unmarked={854:['Identificar e descrever problemas ambientais'],123:['Ler, mesmo','Aprimorar a comunicação','Ampliar seu repertório','Utilizar a estratégia'],1079:['Conhecer diferentes patrimônios','Interagir em situações','Compreender, de forma geral','Expressar-se na Língua Inglesa'],1340:['Comunicar-se pela fala','Ler de modo autônomo','Utilizar, em situações','Produzir textos de autoria'],1341:['Comunicar-se pela fala','Ler, de modo autônomo','Utilizar, em situações','Produzir, de modo autônomo']}
for pno,prefixes in unmarked.items():
 lines=native(D[pno-1])
 for prefix in prefixes:
  candidates=[l for l in lines if l['text'].startswith(prefix)]
  # Some pages contain a bulleted version for a different grade. Unmarked paragraphs are the denominator here.
  if len(candidates)!=1:raise RuntimeError(f'Audit prefix not unique: {pno}/{prefix}/{len(candidates)}')
  l=candidates[0]
  if pno==123:
   context=next(e for e in reversed(parents)if e['page']<pno or e['page']==pno and e['bbox'][1]<l['bbox'][1]);meta={'part':'EDUCAÇÃO INFANTIL','field':context['field'],'age_group':context['age_group']}
  else:
   part=next(p for p in parts if p['page_start']<=pno<=p['page_end']);grade=None
   for prior in range(pno,part['page_start']-1,-1):
    grades=[g for g in native(D[prior-1])if re.fullmatch(r'[1-9]\s*[º°o]\s*ANOS?',g['text'],re.I)and(prior<pno or g['bbox'][1]<l['bbox'][1])]
    if grades:grade=grades[-1]['text'];break
   meta={'part':part['title'],'grade':grade}
  expected.append({**meta,'page':pno,'category':'ei-specific-unmarked'if pno==123 else'ef-grade-rights-unmarked','bbox':l['bbox'],'text':l['text'],'basis':'Explicit paragraph prefix independently recorded in source audit.'})
write('independent-expected-anchors.json',expected);write('independent-contexts.json',contexts);write('independent-coded-parents.json',parents)
def item_anchor(item):
 m=re.search(r':y(\d+):x(\d+)$',item['locator'])
 return (int(m[2])/100,int(m[1])/100)if m else(item['evidence'][0]['bbox'][0],item['evidence'][0]['bbox'][1])
# Compare only after the complete denominator exists.
output=json.loads((ROOT/'data/manifests/uncoded/ac-objectives-items.json').read_text());items=output['items'];matches=[];missing=[];used=set()
for e in expected:
 candidates=[(i,item)for i,item in enumerate(items)if i not in used and item['page']==e['page']and item['source_context']['column_role']==e['category']and abs(item_anchor(item)[1]-e['bbox'][1])<3 and abs(item_anchor(item)[0]-e['bbox'][0])<3]
 if len(candidates)==1:
  i,item=candidates[0];used.add(i);matches.append({'page':e['page'],'category':e['category'],'item_id':item['id'],'locator':item['locator'],'source_anchor':e['text'],'source_bbox':e['bbox']})
 else:missing.append({**e,'candidate_count':len(candidates)})
parent_missing=[]
for e in parents:
 candidates=[(i,item)for i,item in enumerate(items)if i not in used and item['page']==e['page']and item.get('code')==e['code']and item['source_context']['column_role']=='ei-coded-parent']
 if len(candidates)==1:used.add(candidates[0][0]);matches.append({'page':e['page'],'category':'ei-coded-parent','item_id':candidates[0][1]['id'],'source_anchor':e['heading'],'source_bbox':e['bbox']})
 else:parent_missing.append(e)
extra=[{'id':item['id'],'page':item['page'],'category':item['source_context']['column_role'],'text':item['text'][:130]}for i,item in enumerate(items)if i not in used]
actual_tables=json.loads((AUDIT/'tables.json').read_text());expect_pages={x['page']for x in expected_tables};actual_pages={x['page']for x in actual_tables}
report={'source_id':s['id'],'artifact_sha256':s['sha256'],'actor_type':'automated','actor_id':'agent:portal:ac-independent-document-inventory','method':'Independent source TOC (first 17 pages), native marker glyphs/printed column borders, explicit source grade/headings, and individually recorded unmarked paragraph prefixes. Expected anchors are built before reading the item sidecar.','expected_tables':len(expected_tables),'actual_tables':len(actual_tables),'missing_table_pages':sorted(expect_pages-actual_pages),'extra_table_pages':sorted(actual_pages-expect_pages),'expected_uncoded_starts':len(expected),'expected_coded_parents':len(parents),'matched':len(matches),'missing_uncoded_anchors':missing,'missing_coded_parents':parent_missing,'extra_extracted_items':extra,'by_source_category':dict(collections.Counter(e['category']for e in expected)),'source_contexts':dict(collections.Counter(e['role']for e in contexts)),'expected_by_part_year_group':[{'part':part,'field_or_component':field,'grade_or_group':grade,'category':category,'count':count}for(part,field,grade,category),count in sorted(collections.Counter((e.get('part')or'Parte não identificada',e.get('field')or e.get('part'),e.get('grade')or e.get('age_group')or'Faixa não informada',e['category'])for e in expected).items(),key=str)],'all_expected_learning_starts_reconciled':not missing and not parent_missing and not extra and expect_pages==actual_pages,'source_ready':False,'remaining_scope':'Normative introduction, competencies, contexts and source edition/in-force reconciliation are distinct from this learning-column pass. No human or institutional approval asserted.'}
write('independent-reconciliation.json',report);write('independent-matched-anchors.json',matches)
print(json.dumps({k:v for k,v in report.items()if k not in ['missing_uncoded_anchors','missing_coded_parents','extra_extracted_items','expected_by_part_year_group']},ensure_ascii=False,indent=2));print('missing_uncoded',len(missing),'missing_parents',len(parent_missing),'extra_items',len(extra));print('first_missing',missing[:5]);print('first_extra',extra[:5]);sys.exit(0 if report['all_expected_learning_starts_reconciled']else 1)
