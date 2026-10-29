#!/usr/bin/env python3
"""Account for every original competence-field glyph, not just marker counts."""
import collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def ws(v):return ' '.join(v.split())
def strip_label(v):return ws(re.sub(r'\(\s*Continuação\s*\)','',v))
def main():
 census=json.loads((OUT/'competence-field-denominator.json').read_text());by=collections.defaultdict(list);checks=[];fail=[];seen=set()
 for a in census['positive_anchors']:
  b=(a.get('description_cell')or{}).get('bbox')or a['source_cell_bbox'];by[a['source_id'],a['page'],tuple(b)].append(a)
 for f in sorted((ROOT/'data/manifests/uncoded').glob('es-ef-competencies-vol*.json')):
  data=json.loads(f.read_text());sid=data['source_id'];inv=json.loads((OUT/'inventory'/f'{data["artifact_sha256"][:16]}.json').read_text());records=[r for r in data['items']if r.get('code')];cells={(c['page'],tuple(c['bbox'])):c for c in inv['cells']}
  for(s,pn,b),anchors in by.items():
   if s!=sid:continue
   original=cells[pn,b]['cluster_text'];rr=[r for r in records if r['page']==pn and tuple(r['source_context']['physical_cell_bbox'])==b];parts=[]
   for r in rr:
    parts.append((r['evidence'][0]['bbox'][1],r['text']))
    for e in r['source_context'].get('embedded_ability_reference_fragments',[]):parts.append((e['bbox'][1],e['excerpt']))
   reconstructed=ws(' '.join(t for y,t in sorted(parts)));expected=strip_label(original);ok=expected==reconstructed;check={'source_id':sid,'page':pn,'bbox':list(b),'physical_definitions':len(anchors),'output_definitions':len(rr),'original_text':original,'reconstructed_text':reconstructed,'only_excluded_text':'Printed (Continuação) label, if present; all embedded ability-reference prose remains separately evidenced.','exact_whitespace_accounting':ok};checks.append(check)
   if not ok:fail.append(check)
   seen.add((sid,pn,b))
  # Header-only continuation cells contain no learning definition.
  hh={(h['page'],h['table'],h['column']):h for h in census['competence_headers']if h['source_id']==sid}
  for c in inv['cells']:
   h=hh.get((c['page'],c['table'],c['cell']))
   if not h or c['bbox'][1]<h['bbox'][3]-.2 or(sid,c['page'],tuple(c['bbox']))in seen:continue
   text=strip_label(c['cluster_text'])
   # Pure identifier cells are already independently proved by code_locator.
   if re.fullmatch(r'[A-Za-z]{2,10}\s*\d{1,3}',text):continue
   if text:fail.append({'source_id':sid,'page':c['page'],'bbox':c['bbox'],'unaccounted_field_text':text})
 report={'actor_type':'automated','method':'Compare complete original NativeGlyphText cell transcription with canonical output segments plus separately evidenced references in physical vertical order; whitespace only. Count-only marker coverage is insufficient.','source_column_body_cells':len(checks),'physical_definitions':sum(c['physical_definitions']for c in checks),'checks':checks,'failures':fail,'passed':not fail,'human_review':False};(OUT/'full-cell-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['passed'],len(checks),len(fail))
if __name__=='__main__':main()
