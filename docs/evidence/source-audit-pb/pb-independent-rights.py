from pathlib import Path
import json,re,collections
B=Path(__file__).parent;D=json.loads((B/'pb-independent-physical-inventory.json').read_text());items=[]
for comp,first,last in [('Artes Visuais',135,136),('Dança',152,152),('Música',163,163),('Teatro',173,173)]:
 head=next(l for l in D['pages'][first-1]['lines'] if l['text'].startswith('DIREITOS DE APRENDIZAGEM'))
 end=next(l for l in D['pages'][last-1]['lines'] if l['text'].startswith('A seguir,'))
 selected=[]
 for page in D['pages'][first-1:last]:
  for l in sorted(page['lines'],key=lambda q:(q['bbox'][1],q['bbox'][0])):
   if l['bbox'][1]<70 or l['bbox'][3]>787:continue
   if page['page']==first and l['bbox'][1]<=head['bbox'][3]:continue
   if page['page']==last and l['bbox'][3]>=end['bbox'][1]:continue
   selected.append({'page':page['page'],**l})
 groups=[]
 for l in selected:
  if re.match(r'^\d+\.',l['text']):groups.append([])
  assert groups,('missing numbered anchor',comp,l)
  groups[-1].append(l)
 for g in groups:
  raw=' '.join(l['text'] for l in g);m=re.match(r'^(\d+)\.\s*',raw);items.append({'page':g[0]['page'],'kind':'direito_aprendizagem','component':'Arte','subcomponent':comp,'source_number':m.group(1),'text':raw[m.end():],'raw_text':raw,'fragments':g,'source_heading':head['text']})
for pn in [185,186]:
 for table in D['pages'][pn-1]['tables']:
  for row in sorted({c['row'] for c in table['cells']}):
   cols={c['column']:c for c in table['cells'] if c['row']==row}
   if 0 not in cols or not re.fullmatch(r'\d+',cols[0]['text'].strip()):continue
   for col,kind in [(1,'principio_curricular'),(2,'direito_aprendizagem')]:
    cell=cols[col];items.append({'page':pn,'kind':kind,'component':'Educação Física','source_number':cols[0]['text'].strip(),'text':re.sub(r'\s+',' ',cell['text']).strip(),'raw_text':cell['text'],'bbox':cell['bbox'],'table':table['index'],'row':row,'source_heading':'PRINCÍPIOS / DIREITOS'})
out={'source_id':D['source_id'],'artifact_sha256':D['artifact_sha256'],'actor_type':'automated','method':'independent literal rights heading to next prose boundary; explicit numbered anchors; separate principles/rights physical columns','items':items,'count':len(items),'by_kind':dict(collections.Counter(i['kind'] for i in items))}
(B/'pb-independent-rights-denominator.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(out['count'],out['by_kind'])
