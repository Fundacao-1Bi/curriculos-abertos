#!/usr/bin/env python3
"""Exact text-page address alignment; image blocks affect block/line numbering."""
import collections,gzip,hashlib,json
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(line,text):return (tuple(line),text)
def main():
 census=json.loads((OUT/'physical-census.json').read_text());reports=[]
 for source in census['sources']:
  native=json.loads(gzip.decompress((ROOT/source['private_census']).read_bytes()));mapping={};missing=[];exact_subsets=[]
  with fitz.open(ROOT/source['artifact'])as doc:
   for page,old in zip(doc,native['pages']):
    aligned=collections.defaultdict(list)
    for bi,block in enumerate(page.get_text('dict',flags=fitz.TEXTFLAGS_WORDS)['blocks']):
     for li,line in enumerate(block.get('lines',[])):
      text=''.join(s['text']for s in line['spans']).strip()
      if text:aligned[identity(line['bbox'],text)].append((block.get('number',bi),li))
    for row in old['lines']:
     candidates=aligned.get(identity(row['bbox'],row['text']),[]);indices=[wi for wi,w in enumerate(old['words'])if(w[5],w[6])in candidates]
     if not indices:
      box=fitz.Rect(row['bbox']);within=[wi for wi,w in enumerate(old['words'])if box.contains(fitz.Point((w[0]+w[2])/2,(w[1]+w[3])/2))];target=''.join(row['text'].split());matches=[]
      for start in range(len(within)):
       accumulated=''
       for end in range(start,len(within)):
        accumulated+=''.join(old['words'][within[end]][4].split())
        if accumulated==target:matches.append(within[start:end+1]);break
        if not target.startswith(accumulated):break
      if len(matches)==1:indices=matches[0];exact_subsets.append({'page':old['page'],'row_id':row['id'],'method':'unique_exact_word_subsequence_inside_original_line_bbox','word_indices':indices})
     if not indices:missing.append({'page':old['page'],'row_id':row['id'],'text':row['text']})
     else:mapping[row['id']]=indices
  path=ROOT/'var/private-evidence/es-em-core'/(source['source_id']+'-line-index.json.gz');raw=json.dumps(mapping,separators=(',',':')).encode();path.write_bytes(gzip.compress(raw,mtime=0));reports.append({'source_id':source['source_id'],'artifact_sha256':source['artifact_sha256'],'path':str(path.relative_to(ROOT)),'sha256':sha(path.read_bytes()),'mapped_lines':len(mapping),'missing_lines':missing,'exact_subset_mappings':exact_subsets});print(source['source_id'],len(mapping),len(missing),flush=True)
 (OUT/'line-index-census.json').write_text(json.dumps({'actor_type':'automated','method':'Read the same primary with TEXTFLAGS_WORDS for dictionary and words. Match exact bbox+text to original census lines; no nearest text or lexical replacement. Native word indices remain those of the frozen initial census.','sources':reports},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
