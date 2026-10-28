"""Page-scoped physical baseline reader proposal, no lexical substitution.

The reviewed ES Energias p47 source splits end letters into earlier content
objects whose true baselines differ by .48pt. Join physical runs within .75pt,
far below the10.56pt source row spacing. Never enable this globally.
"""
import re
from ms_glyphs import rendered_glyph_runs

def physical_lines(page,bbox=None,tolerance=.75):
 rows=[]
 for run in rendered_glyph_runs(page,bbox):
  row=next((r for r in reversed(rows)if abs(r[0]['baseline']-run['baseline'])<=tolerance),None)
  if row is None:rows.append([run])
  else:row.append(run)
 out=[]
 for row in rows:
  row.sort(key=lambda r:r['bbox'][0]);text='';prior=None
  for r in row:
   if prior and text and not text[-1].isspace()and not r['text'][0].isspace()and r['bbox'][0]-prior['bbox'][2]>1:text+=' '
   text+=r['text'];prior=r
  out.append({'text':re.sub(r'\s+',' ',text).strip(),'bbox':[min(r['bbox'][0]for r in row),min(r['bbox'][1]for r in row),max(r['bbox'][2]for r in row),max(r['bbox'][3]for r in row)],'baselines':[r['baseline']for r in row],'font_runs':[{'text':r['text'],'bbox':r['bbox'],'baseline':r['baseline'],'seqno':r['seqno'],'font':r['font']}for r in row]})
 return out

def physical_text(page,bbox=None):return'\n'.join(r['text']for r in physical_lines(page,bbox))
