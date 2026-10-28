#!/usr/bin/env python3
"""Attach DF objective leaves to literal source headings; never invent codes.

Inputs remain untouched. Every new node has an original-PDF quotation/box and
every objective retains its text, evidence, locator, positions and technical ID.
"""
from pathlib import Path
import json,re,hashlib,collections,sys,copy
import fitz
from extract_df_uncoded import ROOT,SOURCES,lines_in,norm,AGES
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
REV='df-literal-heading-hierarchy-v1.0.0'
def sha(v):return hashlib.sha256(v).hexdigest()
def digest_leaves(items):return sha(json.dumps([(x['source_id'],x['page'],x['locator'],x['text'],x['evidence'],x['positions']) for x in items],ensure_ascii=False,sort_keys=True).encode())
def union(boxes):return [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
def main():
 raw_path=ROOT/'data/manifests/uncoded/df-items.json';raw=json.loads(raw_path.read_text());leaves=copy.deepcopy(raw);nodes={};docs={};line_cache={};pending=[];seen_types=collections.Counter()
 audits=json.loads((ROOT/'docs/evidence/source-audit-central-south/df-adapter-audit.json').read_text())
 clips={(a['source_id'],a['page'],c['column']):c['clip'] for a in audits['page_audit'] for c in a['columns']}
 for sid in {x['source_id'] for x in raw}:
  docs[sid]=fitz.open(ROOT/SOURCES[sid]['local_path'])
  for p in docs[sid]:
   if p.rotation:p.remove_rotation()
 def page(sid,pn):return docs[sid][pn-1]
 def locate(sid,pn,text,col=None,prefer_right=False):
  text=norm(text)
  for number in [pn,pn-1,pn-2,pn-3]:
   if number<1:continue
   p=page(sid,number);rects=[]
   for term in dict.fromkeys([text,text.upper(),text.lower()]):
    rects=p.search_for(term)
    if rects:break
   if rects:
    if col is not None:
     box=clips.get((sid,number,col)) or clips.get((sid,pn,col))
     if box:
      good=[r for r in rects if box[0]-3<=(r.x0+r.x1)/2<=box[2]+3]
      if good:rects=good
      else:rects=[]
    if rects:
     if prefer_right:
      maximum=max(r.x0 for r in rects);rects=[r for r in rects if r.x0>maximum-3]
     return {'page':number,'text':text,'bbox':union([list(r) for r in rects])}
   if col is not None:
    box=clips.get((sid,number,col)) or clips.get((sid,pn,col))
    if not box:continue
    key=(sid,number,col)
    if key not in line_cache:line_cache[key]=lines_in(p,[box[0],0,box[2],box[3]])
    ls=line_cache[key]
    # This also covers bold headings painted as separate native blocks.
    for start in range(len(ls)):
     for end in range(start+1,min(len(ls),start+14)+1):
      actual=norm(' '.join(l['text'] for l in ls[start:end]))
      if ingest.normalize(actual)==ingest.normalize(text):return {'page':number,'text':actual,'bbox':union([l['bbox'] for l in ls[start:end]])}
  return None
 def node(sid,signature,kind,title,pn,parent,pos,col=None,found=None,prefer_right=False):
  key='df-'+kind+'-'+sha(signature.encode())[:16]
  if (sid,key) in nodes:return key
  found=found or locate(sid,pn,title,col,prefer_right)
  if not found:
   pending.append({'source_id':sid,'page':pn,'kind':kind,'title':title,'parent_key':parent});return parent
  loc='df-structure:'+key;ev={'source_id':sid,'page':found['page'],'printed_page':None,'section':'Cabeçalho estrutural literal do currículo','excerpt':found['text'],'bbox':found['bbox'],'locator':loc,'method':REV,'coordinate_space':'page display coordinates after remove_rotation'}
  nodes[(sid,key)]={'key':key,'parent_key':parent,'source_id':sid,'artifact_sha256':SOURCES[sid]['sha256'],'code':None,'kind':kind,'title':found['text'],'text':found['text'],'page':found['page'],'locator':loc,'positions':[pos],'evidence':[ev],'source_context':{'official_code_absent':True,'structure_origin':'literal_source_heading','technical_key_is_not_official_code':True},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:data_central_south','technical_validation_status':'literal_source_heading_and_geometry_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'};seen_types[kind]+=1
  return key
 for item in leaves:
  sid=item['source_id'];pn=item['page'];pos=copy.deepcopy(item['positions'][0]);comp=pos['component'];ctx=item['source_context'];col=ctx['column'];base={**pos,'years':None,'year_label':None,'age_group':None,'period':None};stage=pos['stage'];signature=sid+'|'+comp
  parent=node(sid,signature,'campo_experiencia' if stage=='EI' else 'componente_curricular',comp,pn,None,base,prefer_right=True)
  original_header=ctx.get('original_component_header') or ''
  if comp=='Arte' and re.search(r'ARTE\s*[–-]',original_header):
   language=re.split(r'ARTE\s*[–-]\s*',original_header,maxsplit=1)[-1];signature+='|'+language;parent=node(sid,signature,'linguagem_artistica',language,pn,parent,base,prefer_right=True)
  dimension_signature=signature
  cycle=re.search(r'([1-3]\s*[º°]\s*CICLO)',page(sid,pn).get_text())
  if cycle:
   signature+='|'+norm(cycle.group(1));parent=node(sid,signature,'ciclo_escolar',norm(cycle.group(1)),pn,parent,base)
  if stage=='EI':
   clip=clips[(sid,pn,col)];p=page(sid,pn);root='BEBÊS' if col==0 else 'CRIANÇAS';ww=[w for w in p.get_text('words') if clip[0]<=(w[0]+w[2])/2<=clip[2] and clip[1]-80<=w[1]<=clip[1]-1 and w[4].upper()==root]
   if not ww:pending.append({'source_id':sid,'page':pn,'kind':'grupo_etario','age_group':pos['age_group']});item['parent_key']=parent;continue
   y=min(w[1] for w in ww)-0.5;ls=lines_in(p,[clip[0],y,clip[2],clip[1]-1]);text=norm(' '.join(l['text'] for l in ls));found={'page':pn,'text':text,'bbox':union([l['bbox'] for l in ls])};signature=dimension_signature+'|'+pos['age_group'];parent=node(sid,signature,'grupo_etario',text,pn,parent,pos,found=found)
  else:
   signature=dimension_signature+'|years:'+str(pos['years']);parent=node(sid,signature,'ano_escolar',pos['year_label'],pn,parent,pos)
   theme=ctx.get('unit_theme')
   if theme:
    signature+='|'+theme;parent=node(sid,signature,'unidade_tematica',theme,pn,parent,pos,col=col)
  item['parent_key']=parent
  item.setdefault('source_context',{})['hierarchy_method']=REV
 output=list(nodes.values())+leaves;all_keys={(x['source_id'],x['key']) for x in output if x.get('key')};unresolved=[{'source_id':x['source_id'],'locator':x['locator'],'parent_key':x.get('parent_key')} for x in output if x.get('parent_key') and (x['source_id'],x['parent_key']) not in all_keys]
 failures=[];extracts={sid:{'pages':[{'page':i+1,'text':p.get_text()} for i,p in enumerate(doc)]} for sid,doc in docs.items()}
 for item in output:
  if not ingest.evidence_check(item,extracts[item['source_id']],docs[item['source_id']]):failures.append({'source_id':item['source_id'],'page':item['page'],'locator':item['locator'],'kind':item['kind'],'text':item['text'],'evidence':item['evidence']})
 leaf_identity=digest_leaves(raw)==digest_leaves(leaves);out=ROOT/'data/manifests/uncoded/df-hierarchy-items.json';out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 report={'actor_type':'automated','actor_id':'agent:data_central_south','method':REV,'input_sha256':sha(raw_path.read_bytes()),'output_sha256':sha(out.read_bytes()),'leaf_count':len(leaves),'node_count':len(nodes),'nodes_by_kind':dict(seen_types),'leaf_text_evidence_position_locator_identity':leaf_identity,'leaf_content_sha256':digest_leaves(leaves),'unresolved_parent_keys':unresolved,'unlocated_headings':pending,'literal_failures':failures,'records':len(output),'readiness_claim':False}
 (ROOT/'docs/evidence/source-audit-central-south/df-hierarchy-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('unlocated_headings','literal_failures')},ensure_ascii=False));print('unlocated',len(pending),'literal_failures',len(failures));return bool(unresolved or failures or not leaf_identity)
if __name__=='__main__':raise SystemExit(main())
