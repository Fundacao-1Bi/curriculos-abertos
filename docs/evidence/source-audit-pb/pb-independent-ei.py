"""Independent EI denominator from literal section headings and paragraph gaps."""
from pathlib import Path
import json,re,collections
BASE=Path(__file__).parent
P=json.loads((BASE/'pb-independent-physical-inventory.json').read_text())
out=[];regions=[]
for p in P['pages'][47:65]:
 ls=sorted(p['lines'],key=lambda l:(l['bbox'][1],l['bbox'][0]))
 heads=[l for l in ls if l['text']=='OBJETIVOS DE APRENDIZAGEM E DESENVOLVIMENTO']
 for h in heads:
  top=h['bbox'][3];bottom=min([l['bbox'][1] for l in ls if l['bbox'][1]>top and l['text'].startswith('VIVÊNCIAS QUE')] or [784])
  prior=[l for l in ls if l['bbox'][3]<=h['bbox'][1] and ('CAMPO DE EXPERI' in l['text'].upper() or 'TRANSFORMAÇÕES'==l['text'])]
  context=' '.join(l['text'] for l in prior[-2:])
  age='zero a 1 ano e seis meses' if p['page']<54 else '1 ano e7meses a3anos e11meses' if p['page']<60 else '4anos a5anos e11meses'
  selected=[l for l in ls if l['bbox'][1]>=top and l['bbox'][3]<=bottom and l['text'].strip()]
  pars=[]
  for l in selected:
   if not pars or l['bbox'][1]-pars[-1][-1]['bbox'][3]>6:pars.append([])
   pars[-1].append(l)
  regions.append({'page':p['page'],'bbox':[80,top,545,bottom],'field_context':context,'age':age,'paragraphs':len(pars)})
  for lines in pars:
   b=[min(l['bbox'][0] for l in lines),min(l['bbox'][1] for l in lines),max(l['bbox'][2] for l in lines),max(l['bbox'][3] for l in lines)]
   out.append({'page':p['page'],'bbox':b,'text':' '.join(l['text'] for l in lines),'field_context':context,'age':age,'method':'native paragraph gap within literal objective/vivencia heading boundaries'})
obj={'source_id':P['source_id'],'artifact_sha256':P['artifact_sha256'],'actor_type':'automated','kind':'independent EI expected paragraph denominator before output','objective_regions':regions,'paragraphs':out,'expected_paragraphs':len(out)}
(BASE/'pb-independent-ei-denominator.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print('TOTAL',len(out));print([(r['page'],r['paragraphs']) for r in regions])
