"""All explicit prospective source header rows, including repeated occurrences."""
from pathlib import Path
import collections,hashlib,json,re
OUT=Path('docs/evidence/source-audit-rn-fgb-peer');s=json.loads((OUT/'source-only-structure.json').read_text());cells=[json.loads(line)for line in(OUT/'primary-cells.jsonl').read_text().splitlines()];headers={(h['page'],h['table']):h['header_row']for h in s['headers']};raw=Path('var/ne-rn-fgb-inventory/fgb-physical-complete-candidate.json').read_bytes();r=json.loads(raw);evidence=[]
for i in r['items']:
 for e in i['evidence']:evidence.append({'key':i['key'],'kind':i['kind'],'role':'canonical','e':e})
 for e in i.get('source_context',{}).get('repeated_literal_occurrence_evidence',[]):evidence.append({'key':i['key'],'kind':i['kind'],'role':'repeated_contextual','e':e})
def clean(t):return re.sub(r'\s+',' ',t).strip()
results=[]
for cell in cells:
 key=(cell['page'],cell['table'])
 if key not in headers or cell['row']>headers[key]or not cell['nonempty']:continue
 text=clean(' '.join(w['text']for w in cell['native_words']));matches=[{'key':e['key'],'kind':e['kind'],'role':e['role']}for e in evidence if e['e']['page']==cell['page']and clean(e['e']['excerpt'])==text and all(abs(a-b)<2 for a,b in zip(e['e'].get('bbox',[]),cell['bbox']))];results.append({'page':cell['page'],'table':cell['table'],'row':cell['row'],'column':cell['column'],'bbox':cell['bbox'],'primary_text':text,'matches':matches,'covered':bool(matches)})
r={'candidate_sha256':hashlib.sha256(raw).hexdigest(),'primary_header_nonempty_regions':len(results),'covered':sum(x['covered']for x in results),'missing':[x for x in results if not x['covered']],'records':results};(OUT/'header-comparison.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('HEADERS',len(results),'COVERED',r['covered'],'MISSING',len(r['missing']));print([(x['page'],x['row'],x['primary_text'][:80])for x in r['missing']][:20])
