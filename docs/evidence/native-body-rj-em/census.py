from pathlib import Path
import json,re,sys,collections,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf
from geometry import normalize_native_page
OUT=Path(__file__).parent
from prepare import prepare
B=prepare();S=B['source'];D=pymupdf.open(ROOT/S['local_path'])
CODE=re.compile(r'(?<![A-Z0-9])EM[A-Z0-9]+(?:\.RJ\d+)?(?![A-Z0-9])')
def rows(page):
 lines=[]
 for block in page.get_text('dict',flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)['blocks']:
  for line in block.get('lines',[]):
   text=''.join(s['text'] for s in line['spans']);box=line['bbox']
   if text.strip():lines.append({'text':text,'bbox':list(box),'spans':line['spans']})
 return sorted(lines,key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]))
if __name__=='__main__':
 results=[];unusual=[]
 for n in range(1,len(D)+1):
  p=D[n-1];norm=normalize_native_page(p);ls=rows(p)
  for ri,l in enumerate(ls):
   for m in CODE.finditer(l['text']):
    if not re.search(r'\d',m.group()):continue
    prefix=l['text'][:m.start()];kind='heading' if re.search(r'Habilidades?[^:]{0,80}:\s*\(*\s*$',prefix,re.I) else 'bare' if not prefix.strip(' ()') else 'other'
    event={'page':n,'code':m.group(),'row':ri,'prefix':prefix,'suffix':l['text'][m.end():],'bbox':l['bbox'],'role':kind};results.append(event)
    if kind=='other':unusual.append(event)
 (OUT/'native-code-census.json').write_text(json.dumps({'source_sha256':S['sha256'],'pages':len(D),'native_code_occurrences':len(results),'counts':dict(collections.Counter(e['role'] for e in results)),'events':results},ensure_ascii=False,indent=2)+'\n')
 print('COUNTS',len(results),collections.Counter(e['role'] for e in results));print(json.dumps(unusual[:50],ensure_ascii=False,indent=2))
