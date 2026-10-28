"""Source-only trailing/whole uncodedMath expectations; not derived from sidecar."""
from pathlib import Path
import json,re,pymupdf as pdf
B=Path(__file__).parent;ROOT=B.parents[2];D=pdf.open(ROOT/'data/raw/PB/pb-proposta-ei-ef-cedoc.pdf');C=json.loads((B/'pb-independent-392-cell-denominator.json').read_text())['cells'];out=[]
for c in C:
 if c['scope']!='Matemática':continue
 b=c['bbox'];ws=[w for w in D[c['page']-1].get_text('words',sort=True)if b[0]<=(w[0]+w[2])/2<=b[2]and b[1]<=(w[1]+w[3])/2<=b[3]];compact='';index=[]
 for wi,w in enumerate(ws):
  for char in w[4]:
   if char.isalnum():compact+=char;index.append(wi)
 codes=list(re.finditer(r'EF\d{2}MA\d{2}',compact));tail=ws[index[codes[-1].end()-1]+1:]if codes else ws
 if not tail:continue
 text=' '.join(w[4]for w in tail)
 if not re.match(r'^(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]*(?:ar|er|ir|or))\b',text):continue
 out.append({'page':c['page'],'scope':'Matemática','cell_id':c['cell_id'],'type':'explicit_uncoded_math_goal','bbox':list(tail[0][:4]),'text':text,'source_column_bbox':b,'basis':'Whole local-objective cell without a code'if not codes else'Independent trailing infinitive paragraph after final own inlinecode; no code assigned'})
obj={'method':'Native first-column word occurrences; split-code char-to-word map; collect whole no-code cells or trailing uppercase-infinitive paragraph after last inlineMathcode. No sidecar imported.','development_timing':'source-only supplementary audit after provisional output','anchors':out,'total':len(out)}
(B/'pb-independent-392-math-uncoded.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(obj['total'],[(x['page'],x['text'])for x in out])
