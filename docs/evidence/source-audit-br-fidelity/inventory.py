#!/usr/bin/env python3
"""Read-only, independent native code inventory before any BR evidence proposal."""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
CODE=re.compile(r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2,3}|EM\d{2}[A-Z]{2,3}\d{2,3})')
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
 baseline=ROOT/'docs/evidence/data-preflight-native-baseline.json';report=json.loads(baseline.read_text());failures=[r for r in report['failures'] if r['source_id'] in ('br-bncc-2018','br-bncc-computacao-2022')]
 assert len(failures)==394
 sources=json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text());sources=sources if isinstance(sources,list) else sources['sources'];by_id={s['id']:s for s in sources};inventory=[];frozen=[]
 # Enumerate primary code glyph occurrences without consulting the dataset texts or expected pages.
 for sid in sorted({r['source_id'] for r in failures}):
  source=by_id[sid];path=ROOT/source['local_path'];assert digest(path)==source['sha256'];pages=[]
  with fitz.open(path) as doc:
   page_count=len(doc)
   for index,page in enumerate(doc):
    words=page.get_text('words',sort=False);anchors=[]
    for word in words:
     for match in CODE.finditer(word[4]):anchors.append({'code':match.group(0),'word':word[4],'bbox':[round(v,4) for v in word[:4]],'block':word[5],'line':word[6],'word_index':word[7]})
    if anchors:pages.append({'page':index+1,'width':page.rect.width,'height':page.rect.height,'rotation':page.rotation,'words':len(words),'anchors':anchors})
  inventory.append({'source_id':sid,'artifact':source['local_path'],'artifact_sha256':source['sha256'],'edition':source.get('edition'),'page_count':page_count,'pages_with_codes':pages,'code_occurrences':sum(len(p['anchors']) for p in pages)})
 # Freeze the failing canonical payloads only after the independent inventory is formed.
 for entry in inventory:
  sid=entry['source_id'];cache=ROOT/next(r['cache'] for r in report['sources'] if r['source_id']==sid);payload=json.loads(cache.read_text());items={i['id']:i for i in payload['items']};required=[r for r in failures if r['source_id']==sid]
  frozen.append({'source_id':sid,'source':by_id[sid],'cache':str(cache.relative_to(ROOT)),'cache_sha256':digest(cache),'records':[items[r['id']] for r in required],'extra_immutable_regressions':[i for i in payload['items'] if i.get('code')=='EF05CO011'],'failures':required})
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();save('native-inventory.json',{'actor_type':'automated','actor_id':'codex-independent-br-fidelity-auditor','generated_at':stamp,'method':'Primary native word code glyph inventory over complete PDFs, independent of dataset expected text and page. No OCR inference or text replacement.','baseline_report_sha256':digest(baseline),'denominator':394,'sources':inventory,'publication_modified':False});save('baseline-records.json',{'generated_at':stamp,'baseline_report_sha256':digest(baseline),'denominator':394,'sources':frozen,'immutable_fields':['id','code','text','source_id','source_dataset','code_aliases'],'publication_modified':False});print(json.dumps({'failures':len(failures),'by_source':dict(collections.Counter(r['source_id'] for r in failures)),'inventory_codes':{r['source_id']:r['code_occurrences'] for r in inventory}}))
if __name__=='__main__':main()
