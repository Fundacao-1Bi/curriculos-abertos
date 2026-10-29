#!/usr/bin/env python3
"""Actual current extraction with cache writes captured in private storage only."""
import argparse,collections,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
SNAPSHOT=Path(sys.argv[sys.argv.index('--snapshot-dir')+1]).resolve()if'--snapshot-dir'in sys.argv else ROOT/'pipeline'
sys.path.insert(0,str(SNAPSHOT));os.environ['SOURCE_SKIP_OCR']='1'
import pymupdf as fitz
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ms_glyphs import rendered_glyph_text

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--group',choices=['ef','em','all'],default='all');ap.add_argument('--pages',type=int,nargs='+');ap.add_argument('--flags-file');ap.add_argument('--snapshot-dir');a=ap.parse_args();flags=json.loads(Path(a.flags_file).read_text())if a.flags_file else {}
 module=SNAPSHOT/'ingest.py';ns={'__file__':str(module),'__name__':'es_isolated_fidelity_probe'};exec(compile(module.read_text(),str(module),'exec'),ns);ns['ROOT']=ROOT
 private=ROOT/'var/private-evidence/source-audit-southeast-fidelity'/hashlib.sha256(ns['canonical'](ns['LOADED_PARSER_FINGERPRINT'])).hexdigest();private.mkdir(parents=True,exist_ok=True)
 candidates={}
 def capture(path,value):
  if not isinstance(value,dict) or not value.get('source_id','').startswith('es-'):raise RuntimeError('Unexpected isolated write')
  target=private/(value['sha256']+'.json');target.write_bytes(ns['canonical'](value));candidates[value['source_id']]=target
 ns['write_extraction_cache']=capture
 def blocked(*args,**kwargs):raise RuntimeError('Isolated probe attempted other write')
 ns['write_json']=blocked
 baseline=json.loads((ROOT/'docs/evidence/data-preflight-native-baseline.json').read_text());ids={f['source_id'] for f in baseline['failures']if f['source_id'].startswith('es-')}
 sources=[s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']in ids and (a.group=='all'or (('vol-0'in s['id'])==(a.group=='ef')))];summaries=[];checks=[]
 for original in sources:
  s={**original,**flags.get(original['id'],{})}
  if a.pages:s['extraction_pages']=a.pages
  prod=ROOT/'data/extracted'/f'{s["sha256"]}-{ns["EXTRACTION_REVISION"]}.json';before=sha(prod);checksum=prod.with_suffix(prod.suffix+'.sha256');checksum_before=sha(checksum) if checksum.exists()else None
  x=ns['extract_pdf'](s,ROOT/s['local_path'],force=True);assert sha(prod)==before;assert (sha(checksum)if checksum.exists()else None)==checksum_before
  D=fitz.open(ROOT/s['local_path']);bad=[];coded=[i for i in x['items']if i.get('code')];fragment_checks=[];page_readers=collections.OrderedDict()
  for i in coded:
   passed=ns['evidence_check'](i,x,D)
   if not passed:bad.append({'id':i['id'],'code':i['code'],'page':i['evidence'][0]['page'],'locator':i['evidence'][0]['locator'],'text':i['text'],'evidence':i['evidence']})
   for ei,e in enumerate(i['evidence']):
    number=e['page']
    if number not in page_readers:
     p=D[number-1];normalize_native_page(p);page_readers[number]=(p,NativeGlyphText(p))
     if len(page_readers)>4:page_readers.popitem(last=False)
    page_readers.move_to_end(number);p,reader=page_readers[number];box=e.get('bbox');raw=reader.text(box) if box else reader.text();trace=rendered_glyph_text(p,box);excerpt=e['excerpt'];fragment_checks.append({'id':i['id'],'code':i['code'],'page':e['page'],'locator':e['locator'],'evidence_index':ei,'bbox':box,'role':e.get('evidence_role','text'),'excerpt':excerpt,'rawdict_cluster_match':ns['normalize'](excerpt)in ns['normalize'](raw),'trace_match':ns['normalize'](excerpt)in ns['normalize'](trace),'actual_evidence_check':passed})
  finalized=ns['finalize_items'](x['items'],[s]);finalpath=private/('finalized-'+s['sha256']+'.json');finalpath.write_bytes(ns['canonical'](finalized))
  old=json.loads(prod.read_text());oldcoded=[i for i in old['items']if i.get('code')and (not a.pages or i['evidence'][0]['page']in a.pages)]
  def leafkey(i):return (i['code'],i['evidence'][0]['page'],i['evidence'][0]['locator'])
  oldmap=collections.defaultdict(list);newmap=collections.defaultdict(list)
  for i in oldcoded:oldmap[leafkey(i)].append(i['text'])
  for i in coded:newmap[leafkey(i)].append(i['text'])
  changed=[{'code':k[0],'page':k[1],'locator':k[2],'old':oldmap[k],'new':newmap[k]}for k in oldmap.keys()|newmap.keys()if oldmap[k]!=newmap[k]]
  invpath=OUT/'inventory'/(s['sha256'][:16]+'.json');inv=json.loads(invpath.read_text());summary={'source_id':s['id'],'artifact_sha256':s['sha256'],'candidate_path':str(candidates[s['id']].relative_to(ROOT)),'candidate_sha256':sha(candidates[s['id']]),'coded_items':len(coded),'finalized_items':len(finalized),'finalized_learning_items':sum(i['kind']in('habilidade','objetivo_aprendizagem')for i in finalized),'finalized_path':str(finalpath.relative_to(ROOT)),'finalized_sha256':sha(finalpath),'coded_fragments':len(fragment_checks),'literal_failed_items':bad,'rawdict_unmatched_fragments':[f for f in fragment_checks if not f['rawdict_cluster_match']],'trace_unmatched_fragments':[f for f in fragment_checks if not f['trace_match']],'canonical_changes_against_old_cache':changed,'production_cache_before_sha256':before,'production_cache_after_sha256':sha(prod),'production_checksum_unchanged':True,'independent_inventory_code_occurrences':inv['code_occurrences'],'independent_inventory_code_cells':inv['cells_with_codes'],'ocr_skipped_explicitly':True,'ocr_pending':x['ocr_pending'],'extraction_warnings':x['warnings']};summaries.append(summary);checks.extend([{'source_id':s['id'],**c}for c in fragment_checks]);print(s['id'],'coded',len(coded),'failed',len(bad),'changes',len(changed),flush=True)
  report={'actor_type':'automated','actor_id':'pr_adapter:es-full-isolated-import','parser_fingerprint':ns['LOADED_PARSER_FINGERPRINT'],'extraction_revision':ns['EXTRACTION_REVISION'],'pipeline_module_sha256':sha(module),'immutable_snapshot_path':str(SNAPSHOT.relative_to(ROOT)),'snapshot_guard_enabled':True,'sources':summaries,'human_review':False,'production_files_modified':False,'native_only_ocr_skipped':True}
  suffix=a.group+('-scoped'if a.pages else '')+('-flags'if a.flags_file else '')
  (OUT/f'probe-{suffix}-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/f'probe-{suffix}-fragments.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
