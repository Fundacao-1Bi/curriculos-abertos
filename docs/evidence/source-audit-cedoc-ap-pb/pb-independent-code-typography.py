"""Comparison-only code search; no production normalization or code assignment."""
from pathlib import Path
import json,re
B=Path(__file__).parent;sets={};locations={}
for label in ['validated635','cedoc392']:
 d=json.loads((B/f'pb-independent-{label}-inventory.json').read_text());occ={}
 for p in d['page_data']:
  compact=re.sub(r'\s+','',p['text'].replace('\u00ad',''))
  for m in re.finditer(r'(?:EI|EF)[0-9]{2}[A-Z]{2}[0-9]{2}',compact):occ.setdefault(m[0],[]).append(p['page'])
 sets[label]=set(occ);locations[label]=occ
summary=json.loads((B/'pb-independent-comparison-summary.json').read_text());split={c:locations['cedoc392'].get(c) for c in summary['codes']['only_validated635']}
obj={'method':'Exploratory typography-normalized search strips whitespace and U+00AD only, then finds tokens of strict EI/EF two-digit grade/component/two-digit form. No validity assertion about the grade or code; no production repair or identity assignment. Each split code needs its literal source excerpt and geometry when ingested.','validated635_regular_shaped_unique':len(sets['validated635']),'cedoc392_regular_shaped_unique':len(sets['cedoc392']),'only_validated635':sorted(sets['validated635']-sets['cedoc392']),'only_cedoc392':sorted(sets['cedoc392']-sets['validated635']),'35_apparent_missing_code_locations_after_typographic_join':split,'locations':locations}
(B/'pb-independent-code-typography-check.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(obj['validated635_regular_shaped_unique'],obj['cedoc392_regular_shaped_unique'],obj['only_validated635'],obj['only_cedoc392'])
