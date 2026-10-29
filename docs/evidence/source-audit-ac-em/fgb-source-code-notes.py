#!/usr/bin/env python3
"""Original native asterisk census and explicit out-of-grid code adaptation footnote."""
from pathlib import Path
import json,re
import fitz
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';D=fitz.open(R/'data/raw/AC/ac-cru-em.pdf');tokens=[]
for n in range(112,386):
 for w in D[n-1].get_text('words'):
  if '*'in w[4]:tokens.append({'page':n,'bbox':list(w[:4]),'text':w[4]})
assert len(tokens)==2 and[t['page']for t in tokens]==[209,210]
ws=[list(w[:5])for w in sorted(D[209].get_text('words'),key=lambda w:(w[1],w[0]))if 439<=w[1]<458];f={'page':210,'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)],'words':ws,'text':re.sub(r'\s+',' ',' '.join(w[4]for w in ws)).strip()}
assert f['text'].startswith('* .A habilidade é própria da Língua Inglesa')and f['text'].endswith('Língua Espanhola.')
out={'source_id':'ac-cru-em','artifact_sha256':'9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad','method':'Native word scan of all physical pages112–385 for every asterisk. Call and note localized independently of sidecar. Note lies between physical table borders438.71 and458.05 on210, so strict-cell inventory alone does not include it.','primary_inventory_revision':'Explicit out-of-grid footnote extension after native visual/code-literal review; 240/60/447/240 source-unit denominators unchanged. No observed output count used as denominator.','asterisk_tokens':tokens,'guidance_notes':[{'literal_code':'EM13LGG40','code_call':tokens[0],'source_role':'explicit_adaptation_footnote_not_equivalence','fragments':[f],'text':f['text']}],'guidance_note_denominator':1,'no_silent_code_correction':True,'no_parser_OCR_cache_import':True};(O/'fgb-native-code-note-inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'asterisk_tokens':len(tokens),'guidance_notes':1,'note':f['text']},ensure_ascii=False))
