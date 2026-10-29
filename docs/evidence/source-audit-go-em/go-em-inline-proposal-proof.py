#!/usr/bin/env python3
"""Verify a narrowly scoped parser proposal in memory; never edit production code."""
import ast,collections,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest
from geometry import normalize_native_page
original=(ROOT/'pipeline/ingest.py').read_text();proposed=original.replace("(?:(?:[A-Z]{2})[-.])?", "(?:(?:[A-Z]{2})[-.]\\s*|GO\\s+)?",1)
needle="        if line_prefix not in ('','(','[','•','-') and not re.match(r'^Habilidades?\\b.*:\\s*\\(*$',line_prefix,re.IGNORECASE):continue"
replacement="        local_go_goal=(source or {}).get('id')=='go-dcgoem-portal-atual' and re.match(r'GO(?:[-.]\\s*|\\s+)EM',match.group()) and prefix.rstrip().endswith('(') and cell[match.end():].lstrip().startswith(')')\n        if not local_go_goal and line_prefix not in ('','(','[','•','-') and not re.match(r'^Habilidades?\\b.*:\\s*\\(*$',line_prefix,re.IGNORECASE):continue"
proposed=proposed.replace(needle,replacement,1);tree=ast.parse(proposed);namespace=vars(ingest).copy()
nodes=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='CODE_ANY'for t in n.targets)or isinstance(n,ast.FunctionDef)and n.name=='candidates_from_cell']
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<GO parser proposal>','exec'),namespace)
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual');D=fitz.open(ROOT/source['local_path']);anchors=json.loads((OUT/'comparison-code-anchors.json').read_text());expected={(a['page'],re.sub(r'\s+','',a['code']))for a in anchors if a['code'].startswith('GO')};records=[]
for number in range(193,497):
 page=D[number-1];normalize_native_page(page)
 for ti,table in enumerate(page.find_tables().tables):
  for ri,row in enumerate(table.rows):
   for ci,bbox in enumerate(row.cells):
    if not bbox:continue
    raw=page.get_text('text',clip=fitz.Rect(bbox));decoded=ingest.decode_source_text(source,raw)
    for code,text,_ in namespace['candidates_from_cell'](decoded,source=source):
     if not code.startswith('GO'):continue
     records.append({'page':number,'code':code,'search_form':re.sub(r'\s+','',code),'text':text,'bbox':list(bbox),'locator':f'table:{ti}/row:{ri}/cell:{ci}','literal_text_in_decoded_cell':text in ingest.clean_text(decoded)})
have={(r['page'],r['search_form'])for r in records};missing=sorted(expected-have);extras=sorted(have-expected)
result={'source_id':source['id'],'source_sha256':source['sha256'],'production_modified':False,'production_file_sha256':hashlib.sha256(original.encode()).hexdigest(),'proposal_sha256':hashlib.sha256(proposed.encode()).hexdigest(),'source_independent_local_anchor_pairs':len(expected),'proposed_local_items':len(records),'proposed_distinct_code_page_pairs':len(have),'missing_local_anchors':missing,'extra_local_anchors':extras,'literal_cell_findings':sum(not r['literal_text_in_decoded_cell']for r in records),'note':'Memory-only verification of a proposed parser change against every FGB table. Does not change extraction cache, production module or source manifest.'}
for name,value in [('inline-proposal-summary.json',result),('inline-proposal-items.json',records)]:
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
