#!/usr/bin/env python3
"""Read-only SC hierarchy enrichment. Leaves are preserved byte-for-value.
Only literal, source-verifiable labels become structural nodes; no official code
or grade is invented. Outputs are separate source wrappers, never input edits.
"""
from pathlib import Path
import json,re,hashlib,collections,sys,copy,argparse,datetime
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-sc-hierarchy';sys.path.insert(0,str(ROOT/'pipeline'))
from ingest import normalize,evidence_check,source_uncoded_items
from geometry import normalize_native_page
REV='sc-literal-hierarchy-v1.0.0'
INPUTS=['data/manifests/uncoded/sc-eief-items.json','data/manifests/uncoded/sc-em-items.json','data/manifests/uncoded/sc-trilhas-all-items.json']
def dump(path,x):path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bbox_union(boxes):return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
class Enricher:
 def __init__(self,source):
  self.source=source;self.sid=source['id'];self.d=fitz.open(ROOT/source['local_path']);self.cache={};self.nodes={};self.failures=[];self.links=[]
  assert digest(ROOT/source['local_path'])==source['sha256']
 def page(self,pn):
  if pn not in self.cache:
   p=self.d[pn-1];normalize_native_page(p);ls=[]
   for block in p.get_text('dict')['blocks']:
    for line in block.get('lines',[]):
     ss=[s for s in line['spans'] if s['text'].strip()]
     if ss:ls.append({'text':' '.join(''.join(s['text'] for s in ss).split()),'bbox':list(line['bbox']),'size':max(s['size'] for s in ss),'bold':any(s['flags']&16 for s in ss)})
   self.cache[pn]={'page':pn,'text':p.get_text(),'words':p.get_text('words'),'lines':sorted(ls,key=lambda l:(l['bbox'][1],l['bbox'][0]))}
  return self.cache[pn]
 def find(self,label,pn=None,box=None,before=None,minpage=1,heading=False):
  if not label or not str(label).strip():return None
  label=str(label).strip();needle=normalize(label)
  if pn and box:
   pg=self.page(pn);ww=[w for w in pg['words'] if box[0]-.5<=(w[0]+w[2])/2<=box[2]+.5 and box[1]-.5<=(w[1]+w[3])/2<=box[3]+.5]
   if needle in normalize(' '.join(w[4] for w in ww)):return {'source_id':self.sid,'page':pn,'printed_page':None,'section':label,'excerpt':label,'bbox':list(box),'coordinate_space':'source_page_display_coordinates','method':REV}
  upper=before[0] if before else pn or len(self.d);numbers=[pn] if pn else list(range(upper,max(minpage,upper-200)-1,-1));matches=[]
  for np in numbers:
   pg=self.page(np);ls=pg['lines'];limit=before[1] if before and np==before[0] else 1e9
   for i,line in enumerate(ls):
    if line['bbox'][1]>=limit:continue
    for count in range(1,5):
     group=ls[i:i+count]
     if len(group)!=count or group[-1]['bbox'][3]>limit:break
     if count>1 and any(group[j+1]['bbox'][1]-group[j]['bbox'][3]>20 or abs(group[j+1]['bbox'][0]-group[j]['bbox'][0])>100 for j in range(count-1)):break
     text=' '.join(l['text'] for l in group)
     if needle not in normalize(text):continue
     if heading and len(text)>max(len(label)*2+40,180):continue
     score=(max(l['size'] for l in group),int(all(l['bold'] for l in group)),-len(text),np)
     matches.append((score,np,bbox_union([l['bbox'] for l in group])))
   # Parallel cover columns interleave in page y-order. Read each native
   # x-aligned/font-aligned stream before considering multi-line labels.
   streams=collections.defaultdict(list)
   for line in ls:streams[(round(line['bbox'][0]/3),round(line['size']))].append(line)
   for stream in streams.values():
    stream.sort(key=lambda l:l['bbox'][1])
    for i,line in enumerate(stream):
     for count in range(1,7):
      group=stream[i:i+count]
      if len(group)!=count or group[-1]['bbox'][3]>limit:break
      if count>1 and any(group[j+1]['bbox'][1]-group[j]['bbox'][3]>20 for j in range(count-1)):break
      text=' '.join(l['text'] for l in group)
      if needle not in normalize(text):continue
      if heading and len(text)>max(len(label)*2+40,180):continue
      cover_priority=1 if pn and group[-1]['bbox'][3]<160 else 0
      score=(100*cover_priority+max(l['size'] for l in group),int(all(l['bold'] for l in group)),-len(text),np);matches.append((score,np,bbox_union([l['bbox'] for l in group])))
   if matches and pn is None and not heading:break
  if not matches:return None
  _,np,box=max(matches,key=lambda m:m[0]);return {'source_id':self.sid,'page':np,'printed_page':None,'section':label,'excerpt':label,'bbox':box,'coordinate_space':'source_page_display_coordinates','method':REV}
 def node(self,role,label,evidence,parent,position,scope=None):
  if not evidence:return parent
  # Node identity includes its literal source label, parent and physical scope.
  token=json.dumps([self.sid,role,label,parent,scope or [evidence['page'],[round(v,1) for v in evidence['bbox']]]],ensure_ascii=False,separators=(',',':'));key='sc-h-'+hashlib.sha256(token.encode()).hexdigest()[:20]
  if key not in self.nodes:
   node={'source_id':self.sid,'artifact_sha256':self.source['sha256'],'key':key,'parent_key':parent,'code':None,'kind':'secao_normativa','title':label,'text':label,'page':evidence['page'],'locator':'sc-hierarchy:'+key,'positions':[copy.deepcopy(position)] if position else [],'evidence':[dict(evidence,locator='sc-hierarchy:'+key)],'source_context':{'structural_role':role,'label_origin':'literal_original_source','hierarchy_origin':'declared_document_structure_or_geometric_row_group','not_a_new_learning':True,'official_code_absent':True},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:pr_adapter','technical_validation_status':'literal_source_label_and_bbox_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'}
   self.nodes[key]=node
  return key
 def add_label(self,role,label,parent,position,pn=None,box=None,before=None,minpage=1,scope=None,required=False):
  if scope is not None and label:
   token=json.dumps([self.sid,role,label,parent,scope],ensure_ascii=False,separators=(',',':'));cached='sc-h-'+hashlib.sha256(token.encode()).hexdigest()[:20]
   if cached in self.nodes:return cached
  ev=self.find(label,pn,box,before,minpage,heading=role not in ['row_context','unit_title'])
  if not ev:
   self.failures.append({'role':role,'label':label,'page':pn,'before':before,'required':required});return parent
  return self.node(role,label,ev,parent,position,scope)
 def enrich(self,leaf):
  c=leaf.get('source_context') or {};p=copy.deepcopy((leaf.get('positions') or [{}])[0]);pn=leaf['page'];y=min((e.get('bbox') or [0,0,0,0])[1] for e in leaf['evidence'] if e['page']==pn);before=(pn,y);parent=None
  # Structural nodes do not add a year/age/period inferred from a chapter.
  rootpos=copy.deepcopy(p);rootpos.update(years=None,year_label=None,age_group=None,period=None)
  if self.sid in ['sc-cb-eief-2019-atual','sc-lingua-inglesa-ai']:
   part=c.get('document_part')
   if self.sid=='sc-lingua-inglesa-ai':part='Língua Inglesa'
   parent=self.add_label('chapter',part,parent,rootpos,before=before,scope=['chapter',part],required=True)
   if p.get('age_group'):parent=self.add_label('age_group',p['age_group'],parent,p,before=before,scope=['age_group',p['age_group'],parent],required=True)
   if p.get('year_label'):parent=self.add_label('year_or_block',p['year_label'],parent,p,before=before,scope=['year',p['year_label'],parent],required=True)
  elif self.sid=='sc-cb-em-caderno-2':
   for label in ['Formação Geral Básica',p.get('component')]:parent=self.add_label('chapter',label,parent,rootpos,before=before,scope=['chapter',label,parent],required=True)
  elif self.sid=='sc-cb-em-caderno-4':
   cover=c.get('course_cover_page');group=c.get('course_group');course=c.get('course_title')
   parent=self.add_label('course_group',group,parent,rootpos,pn=cover,scope=['course_group',group],required=True)
   parent=self.add_label('course',course,parent,rootpos,pn=cover,scope=['course',cover,course,parent],required=True)
   if c.get('unit_title'):
    title=c['unit_title'];up=c.get('unit_title_page',pn);uev=c.get('unit_title_evidence');ub=None
    if isinstance(uev,list) and uev:up=uev[0].get('page',up);ub=uev[0].get('bbox')
    elif isinstance(uev,dict):up=uev.get('page',up);ub=uev.get('bbox')
    cells=c.get('unit_source_context') or []
    if not ub:ub=next((x.get('bbox') for x in cells if normalize(title) in normalize(x.get('text',''))),None)
    parent=self.add_label('unit_title',title,parent,p,pn=up,box=ub,scope=['unit',cover,title,parent],required=True)
  elif self.sid=='sc-cb-em-caderno-3':
   for h in c.get('source_heading_path',[]):
    if h.get('page') and h.get('bbox') and (h['page']<pn or h['bbox'][3]<=y):parent=self.add_label('source_heading',h.get('title'),parent,rootpos,pn=h['page'],box=h['bbox'],scope=['heading',h['page'],h.get('title'),parent],required=True)
   for row in c.get('table_source_context') or []:
    for text,box in zip(row.get('texts',[]),row.get('cells',[])):
     if text and box and normalize(text).startswith('quadro'):
      tp=c.get('table_context_page') or c.get('column_header_page') or pn;parent=self.add_label('table_caption',text,parent,p,pn=tp,box=box,required=True)
   unit=c.get('unit_title');uid=c.get('unit_identifier');up=c.get('unit_title_page',pn)
   rows=c.get('table_source_context') or []
   if uid:
    ub=next((box for row in rows for text,box in zip(row.get('texts',[]),row.get('cells',[])) if text and box and normalize(uid) in normalize(text)),None);parent=self.add_label('unit_identifier',uid,parent,p,pn=up,box=ub,scope=['unit_identifier',up,uid,parent],required=True)
   if unit:
    ub=next((box for row in rows for text,box in zip(row.get('texts',[]),row.get('cells',[])) if text and box and normalize(unit) in normalize(text)),None);parent=self.add_label('unit_title',unit,parent,p,pn=up,box=ub,scope=['unit_title',up,unit,parent],required=True)
  # Nominal cells to the left are explicit row labels, not converted contents or
  # adjacent skill paragraphs. Long contents remain unchanged on each leaf.
  own=c.get('cell_bbox') or c.get('unit_learning_cell_bbox');left=[]
  for cell in c.get('other_source_cells') or []:
   text=cell.get('text','').strip();b=cell.get('bbox')
   if b and own and b[2]<=own[0]+1 and 2<len(text)<=160 and not re.search(r'[.;]',text) and not re.match(r'^(?:[→●•-]|Identificar|Compreender|Investigar|Selecionar|Reconhecer|Utilizar|Levantar)',text,re.I):left.append(cell)
  for cell in sorted(left,key=lambda x:x['bbox'][0]):parent=self.add_label('row_context',cell['text'],parent,p,pn=pn,box=cell['bbox'],scope=['row',pn,[round(v,1) for v in cell['bbox']],parent],required=False)
  enriched=copy.deepcopy(leaf)
  if parent:enriched['parent_key']=parent
  else:self.failures.append({'role':'leaf_parent','source_id':self.sid,'page':pn,'locator':leaf['locator'],'required':True})
  self.links.append({'page':pn,'locator':leaf['locator'],'parent_key':parent})
  return enriched

def run(include_c3=False):
 manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())};all_leaves=[];fingerprints=[]
 for relative in INPUTS:
  if not include_c3 and 'trilhas' in relative:continue
  path=ROOT/relative;raw=json.loads(path.read_text());fingerprints.append({'path':relative,'sha256':digest(path),'records':len(raw)});all_leaves.extend(raw)
 report=[]
 for sid in sorted(set(r['source_id'] for r in all_leaves)):
  if sid not in ['sc-cb-eief-2019-atual','sc-lingua-inglesa-ai','sc-cb-em-caderno-2','sc-cb-em-caderno-3','sc-cb-em-caderno-4']:raise ValueError(sid)
  e=Enricher(manifest[sid]);original=[r for r in all_leaves if r['source_id']==sid];leaves=[e.enrich(r) for r in original];nodes=list(e.nodes.values());bykey={n['key']:n for n in nodes}
  for a,b in zip(original,leaves):assert a=={k:v for k,v in b.items() if k!='parent_key'},'Leaf mutation'
  for n in nodes+leaves:
   if n.get('parent_key'):assert n['parent_key'] in bykey,'Unresolved parent'
  for n in nodes:
   seen=set();p=n['key']
   while p:
    assert p not in seen,'Cycle';seen.add(p);p=bykey[p].get('parent_key')
  path=ROOT/f'data/manifests/uncoded/sc-hierarchy-{sid}.json';wrapper={'source_id':sid,'artifact_sha256':manifest[sid]['sha256'],'actor_type':'automated','actor_id':'agent:pr_adapter','method':REV,'items':nodes+leaves};dump(path,wrapper)
  extracted={'source_id':sid,'sha256':manifest[sid]['sha256'],'pages':[dict(e.page(pn)) for pn in range(1,len(e.d)+1)]}
  checksource=dict(manifest[sid],uncoded_items_path=str(path.relative_to(ROOT)));import_error=None
  try:imported=source_uncoded_items([checksource],{sid:extracted});assert len(imported)==len(nodes)+len(leaves)
  except Exception as ex:import_error=str(ex)
  entry={'source_id':sid,'source_sha256':manifest[sid]['sha256'],'original_leaves':len(original),'enriched_leaves':len(leaves),'nodes':len(nodes),'role_counts':dict(collections.Counter(n['source_context']['structural_role'] for n in nodes)),'leaves_unchanged_except_parent_key':True,'all_parents_resolved':True,'no_cycles':True,'leaves_with_parent':sum(bool(r.get('parent_key')) for r in leaves),'literal_import_pass':import_error is None,'import_error':import_error,'unlocated_labels':e.failures,'output':str(path.relative_to(ROOT)),'output_sha256':digest(path)};report.append(entry);dump(OUT/f'{sid}-audit.json',entry);print(json.dumps({k:v for k,v in entry.items() if k!='unlocated_labels'},ensure_ascii=False),flush=True)
 for fp in fingerprints:assert digest(ROOT/fp['path'])==fp['sha256'],'Input changed during run'
 dump(OUT/'hierarchy-report.json',{'revision':REV,'actor_type':'automated','input_fingerprints':fingerprints,'sources':report,'human_review_performed':False,'ready_uf':False})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--include-c3',action='store_true');a=p.parse_args();run(a.include_c3)
