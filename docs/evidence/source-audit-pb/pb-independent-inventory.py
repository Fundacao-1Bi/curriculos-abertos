"""Independent physical inventory. Does not read or import adapter/sidecar output."""
from pathlib import Path
import pymupdf as pdf, json, hashlib, re, collections
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/source-audit-pb'
PATH=ROOT/'data/raw/PB/pb-proposta-ei-ef.pdf'
SID='pb-proposta-ei-ef'; SHA='b55786376874ab6a46064c44726d578d37f550a99a702069fe7065946ce26383'
def norm(s):return re.sub(r'\s+',' ',s).strip()
def lines(page):
 out=[]
 for bi,b in enumerate(page.get_text('dict')['blocks']):
  for li,l in enumerate(b.get('lines',[])):
   ss=[s for s in l['spans'] if s['text'].strip()];t=norm(''.join(s['text'] for s in ss))
   if t:out.append({'text':t,'bbox':list(l['bbox']),'bold':all(s['flags']&16 for s in ss),'block':bi,'line':li})
 return out
assert hashlib.sha256(PATH.read_bytes()).hexdigest()==SHA
D=pdf.open(PATH); inventory=[]; headings=[]; failures=[]
for pn,page in enumerate(D,1):
 if page.rotation:page.remove_rotation()
 ls=lines(page);ts=[]
 for l in ls:
  if 69<l['bbox'][1]<787 and (l['bold'] or re.search(r'OBJETIV|HABILIDAD|VIVÊNCIAS|CAPAZ|capaz|TEMÁTICA|\d[º°].*ANO',l['text'])):
   headings.append({'page':pn,**l})
 try:
  tables=page.find_tables(strategy='lines_strict').tables
  for ti,t in enumerate(tables):
   rs=t.extract();cells=[];seen=set()
   for ri,row in enumerate(t.rows):
    for ci,b in enumerate(row.cells):
     if b is None:continue
     key=tuple(round(z,2) for z in b)
     if key in seen:continue
     seen.add(key);txt=(rs[ri][ci] or '') if ri<len(rs) and ci<len(rs[ri]) else ''
     cells.append({'row':ri,'column':ci,'bbox':list(b),'text':txt})
   ts.append({'index':ti,'bbox':list(t.bbox),'rows':len(rs),'columns':t.col_count,'cells':cells})
 except Exception as e:failures.append({'page':pn,'error':str(e)})
 inventory.append({'page':pn,'rect':list(page.rect),'text':page.get_text(),'lines':ls,'tables':ts})
 if pn%100==0:print(pn,flush=True)
output={'source_id':SID,'artifact_sha256':SHA,'actor_type':'automated','method':'independent full635page native word/span and strict-line-grid inventory before adapter output','pages':inventory,'table_count':sum(len(p['tables']) for p in inventory),'pages_with_tables':sum(bool(p['tables']) for p in inventory),'failures':failures}
(OUT/'pb-independent-physical-inventory.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
(OUT/'pb-independent-headings.json').write_text(json.dumps({'source_id':SID,'artifact_sha256':SHA,'headings':headings},ensure_ascii=False,indent=2)+'\n')
print('COMPLETE',len(inventory),output['table_count'],output['pages_with_tables'],len(failures),flush=True)
