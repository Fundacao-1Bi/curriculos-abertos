"""Source-only complete EI right subsections in native physical reading order."""
from pathlib import Path
import json,re,pymupdf as pdf
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf');groups=[]
for pn in range(39,42):
 lines=[]
 for b in D[pn-1].get_text('dict')['blocks']:
  for l in b.get('lines',[]):
   box=l['bbox'];t=''.join(s['text']for s in l['spans']).strip()
   if 45<=box[1]<790 and t:lines.append({'page':pn,'bbox':list(box),'text':t,'column':0 if box[0]<290 else 1})
 for line in sorted(lines,key=lambda l:(l['column'],l['bbox'][1],l['bbox'][0])):
  m=re.match(r'^3\.4\.([1-6])\s+(.+)',line['text'])
  if m:groups.append({'number':int(m[1]),'title':m[2],'page':pn,'lines':[]})
  if groups:groups[-1]['lines'].append(line)
for g in groups:g['full_text']=' '.join(l['text']for l in g['lines'])
obj={'source_id':'pb-proposta-ei-ef-cedoc','artifact_sha256':'af4f4447ecf26f5c09728be93702d50e44ec714ef84f8bcfc2c9289452eca453','method':'Source subsection3.4.1..6, reading left column then right then next page, retaining title/prose/BNCC quotations. Pedagogical paragraphs are context of labelled right, never independent skills.','sections':groups,'count':len(groups)}
(B/'pb-independent-392-ei-right-sections.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print([(g['number'],g['title'],len(g['lines']))for g in groups])
