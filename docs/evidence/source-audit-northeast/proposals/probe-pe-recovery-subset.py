import pathlib,sys,json,copy,os,datetime
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O));import ingest,geometry
from bounded_recovery import recover_within_physical_cells
S={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())};original=geometry.recover_missing_columns;ingest.write_json=lambda *a,**kw:None;os.environ['SOURCE_SKIP_OCR']='1';out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','isolated_proposal_only':True,'cache_writes_disabled':True,'cases':{}}
for variant in ['current_core','bounded_physical_cells']:
 geometry.recover_missing_columns=original if variant=='current_core' else lambda *a:recover_within_physical_cells(*a,ingest.candidates_from_cell)
 for sid,pages in [('pe-cedim-2026',[69,71,386,559,642])]:
  s=copy.deepcopy(S[sid]);s['native_text_order']='glyph_cluster_stream';s['extraction_pages']=pages
  try:
   ex=ingest.extract_pdf(s,R/s['local_path'],force=True);records=[{'code':i.get('code'),'text':i['text'],'page':i['evidence'][0]['page'],'method':i['evidence'][0]['method'],'bbox':i['evidence'][0].get('bbox'),'evidence':i['evidence']} for i in ex['items'] if i.get('code')]
   out['cases'][variant+':'+sid]={'records':records,'items':len(ex['items']),'coded':len(records),'pages':ex['page_count'],'warnings':ex['warnings'],'ocr_pending':ex['ocr_pending']};print(variant,sid,len(records),flush=True)
  except Exception as error:out['cases'][variant+':'+sid]={'error':str(error)};print(variant,sid,str(error),flush=True)
(O/'pe-recovery-subset-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
