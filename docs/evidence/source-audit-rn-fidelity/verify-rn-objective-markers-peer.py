#!/usr/bin/env python3
"""Independent original-path marker denominator; no author census as expected list."""
import collections,hashlib,json,re
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;body=json.loads((OUT/'trilhas-independent-body-census.json').read_text());P=ROOT/'data/manifests/uncoded/rn-trilhas-items.json';raw=P.read_bytes();side=json.loads(raw);D=fitz.open(ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf');markers=[];findings=[];pages=[]
for region in body['overviews']:
 n=region['page'];p=D[n-1];r=region['independent_specific_region']['bbox'];textleft=region['specific_bbox'][0];source=[]
 for index,path in enumerate(p.get_drawings()):
  b=path['rect'];fill=path.get('fill')
  if path['type']not in('f','fs')or fill is None or max(fill)>.01 or not .8<b.width<4 or not .8<b.height<4:continue
  x,y=(b.x0+b.x1)/2,(b.y0+b.y1)/2
  if not(r[0]-3<=x<=textleft-1 and r[1]<=y<=r[3]):continue
  source.append({'page':n,'path_index':index,'bbox':list(b),'vector_shape_commands':[v[0]for v in path['items']]})
 source.sort(key=lambda z:z['bbox'][1]);actual=[i for i in side['items']if i['kind']=='objetivo_aprendizagem'and i['page']==n and i.get('source_context',{}).get('objective_role')=='especifico'];assigned=[]
 for marker in source:
  mm=[i for i in actual if i.get('source_context',{}).get('source_bullet_path',{}).get('path_index')==marker['path_index']];ok=len(mm)==1
  if ok:
   node=mm[0];b=node['evidence'][0]['bbox'];y=(marker['bbox'][1]+marker['bbox'][3])/2;ok=b[1]-2<=y<=b[3]+2 and node.get('source_number')is None and node['source_context'].get('source_marker_is_unnumbered')is True;assigned.append(node['key'])
  if not ok:findings.append({'page':n,'check':'printed_marker_objective_assignment','marker':marker,'matches':[i['key']for i in mm]})
 for node in actual:
  if node['key']not in assigned:findings.append({'page':n,'check':'objective_without_independent_original_marker','key':node['key']})
 markers.extend(source);pages.append({'page':n,'independent_original_markers':len(source),'assigned_source_objectives':len(assigned)})
summary={'actor_type':'automated','source_id':'rn-trilhas-aprofundamento','source_sha256':'fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a','sidecar_sha256':hashlib.sha256(raw).hexdigest(),'method':'Original black-filled tiny paths in the independent33specific-objective text regions, before text indent. Raw vector operator types and boxes retained. Denominator not copied from author output; only afterward each source marker is matched to one objective and first-line location. Semicolon/internal verbs do not split an objective.','all_overviews':len(pages),'independent_marker_count':len(markers),'assigned_objectives':sum(p['assigned_source_objectives']for p in pages),'general_objectives':33,'markers':markers,'pages':pages,'findings':findings,'passed':not findings and len(markers)==sum(p['assigned_source_objectives']for p in pages),'source_ready':False};(OUT/'rn-uncoded-peer-objective-markers.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in summary.items()if k not in('markers','pages')})
