#!/usr/bin/env python3
"""Original PDF geometry scan only. No sidecar or pipeline item output read."""
from pathlib import Path
from datetime import datetime,timezone
import fitz,json,re,hashlib,collections,gzip
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;PRIVATE=ROOT/'var/private-evidence/source-audit-rn-uncoded';P=ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf'
def main():
 d=fitz.open(P);assert len(d)==485;assert hashlib.sha256(P.read_bytes()).hexdigest()=='fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a';pages=[];heads=[];units=[];modules=[]
 for pi,p in enumerate(d,1):
  lines=[]
  for bi,b in enumerate(p.get_text('dict')['blocks']):
   for li,l in enumerate(b.get('lines',[])):
    t=''.join(s['text'] for s in l['spans']).strip()
    if not t:continue
    q={'text':t,'bbox':list(l['bbox']),'dir':list(l['dir']),'spans':[{'text':s['text'],'bbox':list(s['bbox']),'origin':list(s['origin']),'font':s['font'],'size':s['size'],'flags':s['flags']} for s in l['spans']],'source_order':[bi,li]};lines.append(q)
    if re.match(r'^Objetivos?\s+(?:geral|espec)',t,re.I):heads.append({'page':pi,'text':t,'bbox':q['bbox'],'max_size':max(s['size'] for s in q['spans'])})
    if re.match(r'^UC\s*\d+\s*[-–:]',t,re.I) and max(s['size'] for s in q['spans'])>=14:units.append({'page':pi,'text':t,'bbox':q['bbox'],'max_size':max(s['size'] for s in q['spans'])})
    if re.match(r'^M[óo]dulo\s*\d+',t,re.I):modules.append({'page':pi,'text':t,'bbox':q['bbox'],'dir':q['dir']})
  pages.append({'page':pi,'rect':list(p.rect),'lines':lines,'native_text_sha256':hashlib.sha256(p.get_text().encode()).hexdigest()})
 PRIVATE.mkdir(parents=True,exist_ok=True)
 with gzip.open(PRIVATE/'source-page-lines.json.gz','wt',encoding='utf-8') as stream:json.dump(pages,stream,ensure_ascii=False,separators=(',',':'))
 result={'actor_type':'automated','actor_id':'agent:rs_adapter:rn-source-scan','at':datetime.now(timezone.utc).isoformat(),'source_id':'rn-trilhas-aprofundamento','artifact_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'pages':485,'objective_heading_occurrences':heads,'candidate_unit_primary_heading_occurrences':units,'all_module_label_occurrences':modules,'private_line_inventory':'var/private-evidence/source-audit-rn-uncoded/source-page-lines.json.gz','scope_limit':'Initial source-only geometry inventory; candidate heading counts are not yet effective unit/module or objective denominators.'};(OUT/'rn-trilhas-initial-source-scan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'objective_headings':len(heads),'objective_pages':sorted(set(h['page'] for h in heads)),'candidate_UC_headings':len(units),'UC_pages':len(set(h['page'] for h in units)),'module_occurrences':len(modules),'module_labels':dict(collections.Counter(h['text'] for h in modules))},ensure_ascii=False))
if __name__=='__main__':main()
