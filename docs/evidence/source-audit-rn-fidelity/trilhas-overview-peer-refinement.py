#!/usr/bin/env python3
"""Refine only33 overview regions; reuse proved198 unit trace headers unchanged."""
import collections,json,re
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;path=OUT/'trilhas-independent-body-census.json';v=json.loads(path.read_text());D=fitz.open(ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf')
def ws(x):return re.sub(r'\s+',' ',x).strip()
def txt(s):return''.join(chr(c[0])for c in s['chars'])
def box(sp):return[min(s['bbox'][0]for s in sp),min(s['bbox'][1]for s in sp),max(s['bbox'][2]for s in sp),max(s['bbox'][3]for s in sp)]if sp else None
prose=[];structural=0
for t in v['trilhas']:
 for h in t['unit_headers']:
  allmentions=h.get('all_module_mentions',h['module_labels']);h['all_module_mentions']=allmentions;h['module_labels']=[m for m in allmentions if abs(m['direction'][0])<.2 and m['direction'][1]<-.8];h['module_prose_mentions']=[m for m in allmentions if m not in h['module_labels']];h['distinct_printed_module_numbers']=sorted({m['printed_module_number']for m in h['module_labels']});structural+=len(h['module_labels']);prose.extend(h['module_prose_mentions'])
 t['module_label_count']=sum(len(h['module_labels'])for h in t['unit_headers'])
for o in v['overviews']:
 p=D[o['page']-1];spans=[s for s in p.get_texttrace()if s['type']==0];blocks=[b for b in p.get_text('blocks')if len(b)>6 and b[6]==0]
 def labels(pattern):return[s for s in spans if re.fullmatch(pattern,ws(txt(s)),re.I)]
 general=labels(r'Objetivo\s+geral\s*:');specific=labels(r'Objetivos\s+espec[ií]ficos\s*:');units=labels(r'Unidades\s+curriculares\s*:')
 unitblocks=[b for b in blocks if re.search(r'(?m)^\s*UC\s*[1-6]\s*[-–:]',b[4],re.I)];unitnumbers=[int(m.group(1))for b in unitblocks for m in re.finditer(r'(?m)^\s*UC\s*([1-6])\s*[-–:]',b[4],re.I)]
 o['listed_unit_numbers']=unitnumbers;o['listed_units']=[{'text':ws(b[4]),'bbox':list(b[:4])}for b in unitblocks]
 for key,ss in [('general_headers',general),('specific_headers',specific),('units_headers',units)]:o[key]=[{'bbox':list(s['bbox']),'text':ws(txt(s))}for s in ss]
 if len(general)==len(specific)==1:
  g,s=general[0],specific[0]
  def region_spans(label):
   b=label['bbox'];isleft=(b[0]+b[2])/2<p.rect.width/2;left=b[0]-3;right=p.rect.width/2-8 if isleft else p.rect.width-30
   roles=[x for x in spans if re.fullmatch(r'(?:Objetivo\s+geral|Objetivos\s+espec[ií]ficos|Unidades\s+curriculares|Temas\s+Contempor[aâ]neos\s+Transversais|Problem[aá]tica)\s*:',ws(txt(x)),re.I)and x['bbox'][1]>b[3]and ((x['bbox'][0]+x['bbox'][2])/2<p.rect.width/2)==isleft]
   bottoms=[x['bbox'][1]for x in roles]+[z[1]for z in unitblocks if z[1]>b[3]and ((z[0]+z[2])/2<p.rect.width/2)==isleft]
   bottom=min(bottoms)if bottoms else p.rect.height-35
   selected=[x for x in spans if x is not label and abs(x['dir'][0])>.9 and x['size']<16 and x['bbox'][0]>=left and x['bbox'][2]<=right+5 and (x['bbox'][1]+x['bbox'][3])/2>b[3]-.5 and (x['bbox'][1]+x['bbox'][3])/2<bottom]
   return selected,{'bbox':[left,b[3],right,bottom],'column':'left'if isleft else'right'}
  gg,greg=region_spans(g);ss,sreg=region_spans(s);o['independent_general_region']=greg;o['independent_specific_region']=sreg
  o['general_text']=ws(' '.join(txt(x)for x in gg));o['specific_text']=ws(' '.join(txt(x)for x in ss));o['general_bbox']=box(gg);o['specific_bbox']=box(ss);o['specific_semicolon_segments']=[x.strip()for x in o['specific_text'].split(';')if x.strip()];o['specific_punctuation_segment_count']=len(o['specific_semicolon_segments']);o['bounded_objective_text_method']='Visible horizontal get_texttrace body spans between exact physical label baselines, excluding UC list. Semicolon segments independent of vector markers; not yet individual-objective approval.'
v['general_objective_headers']=sum(len(o['general_headers'])for o in v['overviews']);v['specific_objective_headers']=sum(len(o['specific_headers'])for o in v['overviews']);v['overview_listed_unit_counts']=dict(collections.Counter(len(o.get('listed_unit_numbers',[]))for o in v['overviews']));v['specific_punctuation_segments']=sum(o.get('specific_punctuation_segment_count',0)for o in v['overviews']);v['module_label_occurrences']=structural;v['module_prose_mentions']=prose;v['module_total_mentions_in_trace']=structural+len(prose);v['units_with_printed_module_number_set']=dict(collections.Counter(','.join(map(str,h['distinct_printed_module_numbers']))for t in v['trilhas']for h in t['unit_headers']));v['anomalies']=[{'page':o['page'],'general_headers':len(o['general_headers']),'specific_headers':len(o['specific_headers']),'empty_general':not o.get('general_text'),'empty_specific':not o.get('specific_text'),'listed_units':len(o['listed_unit_numbers'])}for o in v['overviews']if len(o['general_headers'])!=1 or len(o['specific_headers'])!=1 or not o.get('general_text')or not o.get('specific_text')or len(o['listed_unit_numbers'])!=6];v['method']+=' Refinement reads only33overview pages; trace labels/body replace merged native-block header assumptions. Rotated structural module labels are separated from7 horizontal prose citations.';path.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:x for k,x in v.items()if k not in('trilhas','overviews','module_prose_mentions')},ensure_ascii=False,indent=2))
