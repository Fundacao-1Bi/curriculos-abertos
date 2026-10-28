from pathlib import Path
import json,re
B=Path(__file__).parent;D=json.loads((B/'pb-independent-physical-inventory.json').read_text());out=[]
for first,last in [(458,459),(460,460),(463,463)]:
 start=next(l for l in D['pages'][first-1]['lines'] if l['text'].startswith('OBJETIVO GERAL:'))
 end=next(l for l in D['pages'][last-1]['lines'] if l['text']=='OBJETIVOS')
 fr=[]
 for page in D['pages'][first-1:last]:
  for l in sorted(page['lines'],key=lambda q:(q['bbox'][1],q['bbox'][0])):
   if l['bbox'][1]<70 or l['bbox'][3]>787:continue
   if page['page']==first and l['bbox'][1]<start['bbox'][1]:continue
   if page['page']==last and l['bbox'][3]>=end['bbox'][1]:continue
   fr.append({'page':page['page'],**l})
 raw=' '.join(l['text'] for l in fr);out.append({'page':first,'kind':'objetivo_geral','text':raw.split('OBJETIVO GERAL:',1)[1].strip(),'raw_text':raw,'fragments':fr})
(B/'pb-independent-eja-general-denominator.json').write_text(json.dumps({'source_id':D['source_id'],'artifact_sha256':D['artifact_sha256'],'actor_type':'automated','method':'Independent literal OBJETIVO GERAL heading to physical objective-table header; no goal inferred for CycleIV','items':out,'count':len(out)},ensure_ascii=False,indent=2)+'\n');print(len(out))
