#!/usr/bin/env python3
"""Probe shared core against independent preselected anchors, without cache writes."""
import pathlib,sys,json,copy,datetime,os
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));import ingest
S={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())};audit=json.loads((O/'audit-recheck.json').read_text());scans=json.loads((O/'proposals/geometry-scan.json').read_text());out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','scope':'Selected native page probes, shared core invoked, all cache writes disabled. Not complete source reprocessing.','sources':{}}
os.environ['SOURCE_SKIP_OCR']='1';ingest.write_json=lambda *args,**kwargs:None
BA=[x for x in audit['samples'] if x['source_id']=='ba-dcrb-ei-ef' and x['result']=='unrepresented_code_occurrence_requires_semantic_classification']
PE=scans['sources']['pe-curriculo-em-2021']['cells']
for sid,pages in [('ce-dcrc-em-2021',[208,373]),('pe-curriculo-em-2021',sorted({c['page'] for c in PE})),('se-curriculo-em',[235,327]),('ba-dcrb-ei-ef',sorted({x['page'] for x in BA}))]:
 source=copy.deepcopy(S[sid]);source['extraction_pages']=pages
 ex=ingest.extract_pdf(source,R/source['local_path'],force=True);checks=[]
 if sid.startswith('ce-'):
  for page,code in [(208,'EM13LGG703'),(208,'EM13LP29'),(373,'EMIFCG12')]:
   matches=[i for i in ex['items'] if i.get('code')==code and any(e['page']==page for e in i['evidence'])]
   checks.append({'page':page,'code':code,'expectation':'reference-only code occurrence must not borrow later prose','passed':not matches,'matches':matches})
 elif sid.startswith('pe-'):
  for expected in PE:
   matches=[i for i in ex['items'] if i.get('code')==expected['codes'][0] and i.get('source_context',{}).get('joint_source_codes')==expected['codes'] and i['evidence'][0]['page']==expected['page'] and abs(i['evidence'][0]['bbox'][1]-expected['bbox'][1])<2]
   # Continuations may legitimately append another page's verified fragment.
   checks.append({'page':expected['page'],'codes':expected['codes'],'passed':len(matches)==1 and matches[0]['text'].startswith(expected['prose']),'matches':[{'id':i['id'],'text':i['text'],'bbox':i['evidence'][0]['bbox'],'joint_source_codes':i['source_context']['joint_source_codes']} for i in matches]})
 elif sid.startswith('se-'):
  matches=[i for i in ex['items'] if i.get('code')=='EMIFCG04' and i['evidence'][0]['page']==327]
  checks.append({'page':327,'code':'EMIFCG04','passed':len(matches)==1 and 'manifestações criati-' in matches[0]['text'] and 'presenciais e virtu-' in matches[0]['text'],'matches':[{'id':i['id'],'text':i['text'],'bbox':i['evidence'][0]['bbox']} for i in matches]})
 else:
  for anchor in BA:
   matches=[i for i in ex['items'] if i.get('code')==anchor['code'] and i['evidence'][0]['page']==anchor['page']]
   checks.append({'page':anchor['page'],'code':anchor['code'],'passed':len(matches)==1,'matches':[{'id':i['id'],'text':i['text'],'bbox':i['evidence'][0]['bbox']} for i in matches]})
 out['sources'][sid]={'selected_pages':pages,'page_count':ex['page_count'],'candidate_count':len(ex['items']),'warnings':ex.get('warnings'),'checks':checks,'passed':sum(c['passed'] for c in checks),'total':len(checks)}
 print(sid,out['sources'][sid]['passed'],len(checks),flush=True)
(O/'proposals/integrated-core-probes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
