#!/usr/bin/env python3
import pathlib,sys,json,inspect,copy,datetime,unicodedata,collections,os,re
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O));import ingest,geometry
from native_glyphs import NativeGlyphText
from bounded_recovery import recover_within_physical_cells
code=inspect.getsource(ingest.candidates_from_cell).replace("line_prefix=prefix.rsplit('\\n',1)[-1].strip()", "line_prefix=''.join(c for c in prefix.rsplit('\\n',1)[-1] if __import__('unicodedata').category(c)!='Cf').strip()")
namespace=dict(ingest.__dict__);exec(code,namespace);ingest.candidates_from_cell=namespace['candidates_from_cell'];ingest.write_json=lambda *a,**kw:None
geometry.recover_missing_columns=lambda *args:recover_within_physical_cells(*args,ingest.candidates_from_cell)
S={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())};out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','isolated_monkeypatch_only':True,'proposed_changes':['Native cluster source flag','Ignore Cf only while classifying syntactic code-prefix; canonical source Unicode retained','Recovery uses actual whole physical cell; no left/codeword shrink, right-neighbour-code shrink, or later-row extension'],'sources':{}}
os.environ['SOURCE_SKIP_OCR']='1'
for sid in ['al-recal-ef','al-recal-em']:
 s=copy.deepcopy(S[sid]);s['native_text_order']='glyph_cluster_stream';ex=ingest.extract_pdf(s,R/s['local_path'],force=True);(R/'var/private-evidence/source-audit-northeast'/f'candidate-{sid}-bounded-prefix.json').write_text(json.dumps(ex,ensure_ascii=False))
 out['sources'][sid]={'candidate_items':len(ex['items']),'coded':sum(bool(i.get('code')) for i in ex['items']),'pages':ex['page_count'],'ocr_pending':ex['ocr_pending'],'warnings':len(ex['warnings']),'candidate_private':f'var/private-evidence/source-audit-northeast/candidate-{sid}-bounded-prefix.json'}
 print(sid,out['sources'][sid],flush=True)
(O/'al-native-prefix-probe-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
