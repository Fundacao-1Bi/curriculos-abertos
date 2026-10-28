#!/usr/bin/env python3
"""ES EM core: immutable source-only physical census before sidecar generation."""
import collections,datetime,gzip,hashlib,json,re
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
IDS=['es-em-texto-introdut-rio','es-em-linguagens','es-em-l-ngua-portuguesa','es-em-ci-ncias-da-natureza','es-em-ci-ncias-humanas','es-em-matem-tica']
PRIVATE=ROOT/'var/private-evidence/es-em-core'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};OUT.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True);sources=[]
 for sid in IDS:
  source=manifest[sid];path=ROOT/source['local_path'];assert sha(path.read_bytes())==source['sha256'];pages=[];public_pages=[];coded=0
  with fitz.open(path)as doc:
   for pi,p in enumerate(doc):
    assert p.rotation==0;lines=[]
    for bi,block in enumerate(p.get_text('dict')['blocks']):
     for li,line in enumerate(block.get('lines',[])):
      text=''.join(s['text']for s in line['spans']).strip()
      if not text:continue
      lines.append({'id':f'p{pi+1}:b{bi}:l{li}','page':pi+1,'block':bi,'line':li,'text':text,'bbox':list(line['bbox']),'direction':list(line['dir']),'fonts':[{'name':s['font'],'size':s['size'],'flags':s['flags'],'text':s['text']}for s in line['spans']]})
    words=[list(w)for w in p.get_text('words',sort=False)];plain=p.get_text('text',sort=False);codes=[{'literal':m.group(),'offset':m.start()}for m in re.finditer(r'(?<![A-Z0-9])(?:EM\d{2}[A-Z]{2,3}\d{2,3}(?:[-/][A-Za-z0-9]+)*)(?![A-Z0-9])',plain)];coded+=len(codes);pages.append({'page':pi+1,'rect':list(p.rect),'rotation':p.rotation,'lines':lines,'words':words,'native_text_sha256':sha(plain.encode())})
    candidates=[r for r in lines if re.search(r'(?:[Cc]ompetência|[Oo]bjetivo|[Oo]rganizador|[Cc]apítulo|[Ss]eção|COMPETÊNCIA|OBJETIVO)',r['text'])or re.match(r'^\s*(?:\d+(?:\.\d+)*[.)]?\s*|C\s*0?\d\b|[IVXLCDM]+\s*[–-])',r['text'])];public_pages.append({'page':pi+1,'rect':list(p.rect),'native_text_sha256':sha(plain.encode()),'native_line_count':len(lines),'native_word_count':len(words),'literal_code_occurrences':codes,'physical_heading_or_number_candidates':[{'id':r['id'],'text':r['text'],'bbox':r['bbox'],'font_sizes':sorted({round(s['size'],3)for s in r['fonts']})}for r in candidates]})
  payload={'source_id':sid,'artifact':source['local_path'],'artifact_sha256':source['sha256'],'pages':pages};raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode();private=PRIVATE/(sid+'.json.gz');private.write_bytes(gzip.compress(raw,mtime=0));sources.append({'source_id':sid,'artifact':source['local_path'],'artifact_sha256':source['sha256'],'document_pages':len(pages),'native_lines':sum(len(p['lines'])for p in pages),'native_words':sum(len(p['words'])for p in pages),'native_characters_in_lines':sum(len(r['text'])for p in pages for r in p['lines']),'literal_code_occurrences_not_learning_denominator':coded,'private_census':str(private.relative_to(ROOT)),'private_census_sha256':sha(private.read_bytes()),'private_decoded_sha256':sha(raw),'private_decoded_bytes':len(raw),'page_inventory':public_pages})
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();report={'actor_type':'automated','actor_id':'codex-independent-es-em-core-auditor','generated_at':stamp,'method':'Every physical native line/word and source SHA, before creating any new adapter. Candidate headings/numbers are an inventory for documentary role classification, not an asserted learning denominator. Coded skills will not be edited or duplicated by the uncoded adapter.','sidecar_generated':False,'source_manifest_modified':False,'publication_modified':False,'human_pedagogical_review_claimed':False,'sources':sources};(OUT/'physical-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:v for k,v in s.items()if k!='page_inventory'}for s in sources],ensure_ascii=False))
if __name__=='__main__':main()
