"""AC EM PV/Pós-Médio: only explicit Habilidades-column objectives, original occurrences."""
from pathlib import Path
import json,hashlib,datetime,re,sys,collections
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'data/manifests/uncoded/ac-em-pv-items.json';BASE=ROOT/'docs/evidence/source-audit-ac-em';SID='ac-cru-em'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==SID);doc=fitz.open(ROOT/source['local_path']);assert sha(ROOT/source['local_path'])==source['sha256']
# Primary physical right-column edges. Interior pages63/68 lack detectable ruling;
# actual word positions and neighbouring ruled boundaries establish the same column.
specs=[
 ('body-pv-1',1,'Projeto de Vida',(61,0),[(61,401.47,306.65,538,771.46),(62,401.47,72,538,774),(63,401.47,72,538,784),(64,401.47,72,538,784),(65,401.47,72,538,758),(66,401.47,72,538,670.06)],'bullet'),
 ('body-pv-2',2,'Projeto de Vida',(66,1),[(67,394.27,72,531,764),(68,394.27,72,531,784),(69,394.27,72,531,781),(70,394.27,72,531,140.47)],'bullet'),
 ('body-post-3',3,'Pós-Médio',(71,0),[(71,337.27,536.71,566,767),(72,337.27,72,566,781),(73,337.27,72,566,535.97)],'number'),
 ('annex-pv-1',1,'Projeto de Vida',(452,0),[(453,295.85,72,531,768),(454,295.85,72,531,778),(455,295.85,72,531,584.29)],'number'),
 ('annex-pv-2',2,'Projeto de Vida',(455,1),[(455,267.53,716.5,531,766),(456,267.53,72,531,745),(457,267.53,72,531,462.01)],'number'),
 ('annex-post-3',3,'Pós-Médio',(457,1),[(457,267.53,594.19,538,759),(458,267.53,72,538,769),(459,267.53,72,538,356.63)],'number')]
items=[];audit=[];clock=json.loads(OUT.read_text())['generated_at']if OUT.exists()else datetime.datetime.now(datetime.timezone.utc).isoformat()
def evidence(pn,words,key,idx):
 lines=[]
 for w in words:
  if not lines or abs(lines[-1][0][1]-w[1])>2:lines.append([w])
  else:lines[-1].append(w)
 text='\n'.join(' '.join(w[4]for w in sorted(line,key=lambda x:x[0]))for line in lines)
 return {'source_id':SID,'page':pn,'printed_page':str(pn-3),'section':key,'excerpt':text,'bbox':[min(w[0]for w in words),min(w[1]for w in words),max(w[2]for w in words),max(w[3]for w in words)],'locator':f'ac-pv:{key}:fragment:{idx}','method':'native-word-habilidades-column-complete-marker-stream'}
def add(key,parent,kind,text,page,ev,position,context):
 r={'source_id':SID,'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':None,'text':text,'page':page,'locator':'ac-pv:'+key,'positions':[position],'evidence':ev,'source_order':len(items)+1,'actor_type':'automated','actor_id':'curriculos-abertos:ac-em-pv-primary','source_context':context};items.append(r);return r
for key,year,component,(hp,ti),regions,marker in specs:
 table=doc[hp-1].find_tables().tables[ti];title=table.extract()[0][0];hb=table.rows[0].cells[0];he={'source_id':SID,'page':hp,'printed_page':str(hp-3),'section':key,'excerpt':title,'bbox':list(hb),'locator':'ac-pv:'+key+':primary-title','method':'native-physical-primary-title'}
 pos={'stage':'EM','component':component,'area':None,'years':[year],'year_label':f'{year}ª SÉRIE DO ENSINO MÉDIO','age_group':None,'period':None,'position_origin':'explicit_primary_table_header','position_evidence':he}
 add(key,None,'secao_normativa',title,hp,[he],pos,{'part':'anexo'if key.startswith('annex')else'corpo_principal','definition_scope':'explicit Habilidades column; content/competency/dimension columns are not relabelled as learning objectives'})
 current=None;records=[];fragments=[];tokens=0
 def close():
  global current
  if current is None:return
  ev=[evidence(pn,ww,key,len(records)+1)for pn,ww in current['chunks']];text='\n'.join(e['excerpt']for e in ev);r=add(f'{key}-objective-{len(records)+1:02}',key,'objetivo_aprendizagem',text,ev[0]['page'],ev,pos,{'local_objective_without_published_code':True,'original_marker':current['marker'],'column_role':'Habilidades','part':'anexo'if key.startswith('annex')else'corpo_principal','duplicate_occurrences_between_publication_parts_not_merged':True});records.append(r);current=None
 for pn,x0,y0,x1,y1 in regions:
  words=[w for w in doc[pn-1].get_text('words')if x0-0.1<=w[0]and w[2]<=x1+0.2 and y0-0.2<=w[1]and w[3]<=y1+0.2];words.sort(key=lambda w:(round(w[1],1),w[0]));tokens+=len(words)
  for w in words:
   is_marker=w[4]=='●' if marker=='bullet'else bool(re.match(r'^\d+\.',w[4]))
   if is_marker:
    close();current={'marker':w[4],'chunks':[]}
   assert current is not None,(key,pn,w)
   if not current['chunks']or current['chunks'][-1][0]!=pn:current['chunks'].append((pn,[]))
   current['chunks'][-1][1].append(w)
 close()
 audit.append({'part':key,'header_page':hp,'year_explicit':year,'component_literal':component,'column_regions':regions,'objective_marker_count':len(records),'native_words':tokens,'fragments':sum(len(r['evidence'])for r in records),'objective_keys':[r['key']for r in records]})
# All six explicitly named COMPETÊNCIA cells in the annex, including split cells.
competency_specs=[('annex-pv-1',1,'Projeto de Vida',[(453,0,0,0)]),('annex-pv-1',1,'Projeto de Vida',[(453,0,6,0)]),('annex-pv-1',1,'Projeto de Vida',[(454,0,9,0),(455,0,0,0)]),('annex-pv-2',2,'Projeto de Vida',[(455,1,2,0),(456,0,0,0)]),('annex-pv-2',2,'Projeto de Vida',[(456,0,1,0)]),('annex-post-3',3,'Pós-Médio',[(457,1,2,0),(458,0,0,0)])]
for number,(parent,year,component,cells)in enumerate(competency_specs,1):
 ev=[]
 for pn,ti,ri,ci in cells:
  table=doc[pn-1].find_tables().tables[ti];bbox=table.rows[ri].cells[ci];text=table.extract()[ri][ci];assert text and bbox
  ev.append({'source_id':SID,'page':pn,'printed_page':str(pn-3),'section':parent,'excerpt':text,'bbox':list(bbox),'locator':f'ac-pv:competency-{number}:fragment-{len(ev)+1}','method':'native-physical-COMPETENCIA-cell-with-continuation'})
 root=next(r for r in items if r['key']==parent)
 add(f'{parent}-competency-{number}',parent,'competencia','\n'.join(e['excerpt']for e in ev),ev[0]['page'],ev,root['positions'][0],{'column_role':'COMPETÊNCIA','part':'anexo','not_relabelled_as_ability':True})
items.sort(key=lambda r:(r['page'],r['evidence'][0]['bbox'][1],r['evidence'][0]['bbox'][0],r['key']))
for order,r in enumerate(items,1):r['source_order']=order
adapter={'source_id':SID,'artifact_sha256':source['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:ac-em-pv-primary','generated_at':clock,'method':'All Habilidades markers in six explicit body/annex tables; preserve original numbered/bullet tokens and cross-page continuation; no text borrowed from duplicate parts or national document. Other curriculum parts remain outside this adapter.','expected_inventory':{'physical_parts':6,'physical_source_page_regions':sum(len(s[4])for s in specs)},'items':items}
OUT.write_text(json.dumps(adapter,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
extracted={'source_id':SID,'sha256':source['sha256'],'pages':[{'page':i+1,'text':p.get_text('text',sort=True)}for i,p in enumerate(doc)]};bad=[r['key']for r in items if not ingest.evidence_check(r,extracted,doc)];assert not bad,bad
proposed={**source,'uncoded_items_path':str(OUT.relative_to(ROOT))};parsed=ingest.source_uncoded_items([proposed],{SID:extracted});final=ingest.finalize_items(parsed,[proposed]);assert len(items)==len(parsed)==len(final)
from validate_artifact import validators
schema=validators(ROOT)['Learning'];errors=[e.message for r in final for e in schema.iter_errors(r)];assert not errors,errors[:10]
report={'actor_type':'automated','source_id':SID,'source_sha256':source['sha256'],'sidecar_path':str(OUT.relative_to(ROOT)),'sidecar_sha256':sha(OUT),'part_inventory':audit,'records':len(items),'kinds':dict(collections.Counter(r['kind']for r in items)),'all_native_fragment_checks_passed':True,'loader_finalizer_schema_passed':True,'independent_reconciliation':'pending_peer_source_only_denominator','annex_competency_cells_processed':6,'other_knowledge_dimension_columns_and_curriculum_parts_processed':False,'source_binding_applied':False,'whole_document_ready':False}
(BASE/'pv-adapter-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['records','kinds','part_inventory']},ensure_ascii=False))
