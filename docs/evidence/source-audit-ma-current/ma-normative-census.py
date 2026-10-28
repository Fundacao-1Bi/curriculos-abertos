#!/usr/bin/env python3
"""Source-only denominator, executed before adapter construction or reading sidecars."""
from pathlib import Path
import json,hashlib,re,collections
from datetime import datetime,timezone
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
SIDS=['ma-resolucao-211-2026-doe','ma-portaria-181-2026-recomposicao-doe']
EXPECTED=[{'lines':107,'considerandos':8,'articles':6,'chapters':0,'annex_sections':0},{'lines':619,'considerandos':10,'articles':25,'chapters':9,'annex_sections':17}]
def main():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};results=[]
 for sid,expected in zip(SIDS,EXPECTED):
  s=sources[sid];p=ROOT/s['local_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'];doc=fitz.open(p);lines=[];regions=[]
  for spec in s['page_regions']:
   for ri,box in enumerate(spec['regions']):
    text=doc[spec['page']-1].get_text('text',clip=fitz.Rect(box),sort=False);ll=[t.strip() for t in text.splitlines() if t.strip()];regions.append({'page':spec['page'],'region':ri,'bbox':box,'line_count':len(ll),'native_text_sha256':hashlib.sha256(text.encode()).hexdigest()})
    lines.extend({'page':spec['page'],'region':ri,'ordinal_in_region':n,'text':t} for n,t in enumerate(ll))
  counts={'lines':len(lines),'considerandos':sum(l['text'].startswith('CONSIDERANDO') for l in lines),'articles':sum(bool(re.match(r'^Art\.\s*\d+',l['text'])) for l in lines),'chapters':sum(bool(re.fullmatch(r'CAPÍTULO [IVX]+',l['text'])) for l in lines),'annex_sections':sum(bool(re.match(r'^\d+\.\s+D[AO]S?\s+',l['text'])) for l in lines)}
  assert counts==expected,(sid,counts,expected)
  article_numbers=[int(re.match(r'^Art\.\s*(\d+)',l['text'])[1]) for l in lines if re.match(r'^Art\.\s*\d+',l['text'])];assert article_numbers==list(range(1,expected['articles']+1))
  result={'source_id':sid,'artifact_sha256':s['sha256'],'regions':regions,'expected_from_original_visual_reading':expected,'source_only_counts':counts,'article_numbers_in_source_order':article_numbers,'line_fingerprints':[{k:v for k,v in l.items() if k!='text'}|{'text_sha256':hashlib.sha256(l['text'].encode()).hexdigest()} for l in lines]}
  if sid==SIDS[1]:
   tables=[t for t in doc[35].find_tables().tables if t.row_count==8 and t.col_count==3 and 200<t.bbox[1]<240];assert len(tables)==1;t=tables[0];rows=t.extract();assert [r[0].split('.')[0] for r in rows[1:]]==[str(n) for n in range(1,8)];result['annex_flow_table']={'page':36,'bbox':list(t.bbox),'rows_with_header':8,'columns':3,'body_rows':7,'cell_count':24,'column_labels':rows[0],'first_column_source_labels':[r[0] for r in rows[1:]],'cell_text_hashes':[[hashlib.sha256(c.encode()).hexdigest() for c in row] for row in rows]}
  private=ROOT/'var/private-evidence/source-audit-ma-current'/f'{sid}-census-lines.json';private.write_text(json.dumps(lines,ensure_ascii=False,indent=2)+'\n');results.append(result)
 out={'actor_type':'automated','actor_id':'agent:rs_adapter:ma-normative-source-census','at':datetime.now(timezone.utc).isoformat(),'method':'Original native region text and independent visual anchors; no adapter or pipeline learning output read.','sources':results,'scope_limit':'Denominator of selected complete acts and annex, not all MA curriculum or unseen current guides.'};(OUT/'ma-normative-source-census.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{'source_id':r['source_id'],'counts':r['source_only_counts']} for r in results]))
if __name__=='__main__':main()
