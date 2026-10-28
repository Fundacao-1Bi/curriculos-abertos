#!/usr/bin/env python3
"""Verify the final small integration patch in memory against all affected cells."""
import ast,hashlib,json,re,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));import ingest,geometry
patch=(OUT/'go-emif-recovery-position-proposal.patch').read_text()
def patched(path):
 original=(ROOT/path).read_text();lines=original.splitlines(True);section=patch.split('--- a/'+path+'\n',1)[1].split('--- a/',1)[0].splitlines(True);out=[];cursor=0;active=False
 for line in section:
  if line.startswith('+++'):continue
  if line.startswith('@@'):
   start=int(re.match(r'@@ -(\d+)',line)[1])-1;out.extend(lines[cursor:start]);cursor=start;active=True;continue
  if not active:continue
  if line.startswith(' '):
   if lines[cursor]!=line[1:]:raise RuntimeError('Patch context drift')
   out.append(lines[cursor]);cursor+=1
  elif line.startswith('-'):
   if lines[cursor]!=line[1:]:raise RuntimeError('Patch removal drift')
   cursor+=1
  elif line.startswith('+'):out.append(line[1:])
 out.extend(lines[cursor:]);return ''.join(out)
def functions(source,names,namespace):
 nodes=[node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef)and node.name in names];exec(compile(ast.Module(body=nodes,type_ignores=[]),'<GO verified proposal>','exec'),namespace)
ingest_text=patched('pipeline/ingest.py');geo_text=patched('pipeline/geometry.py');ns=vars(ingest).copy();gs=vars(geometry).copy();functions(ingest_text,{'candidates_from_cell','national_position'},ns);functions(geo_text,{'recover_missing_columns'},gs)
source=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text())if s['id']=='go-dcgoem-portal-atual');D=fitz.open(ROOT/source['local_path']);six=json.loads((OUT/'inline-emif-six-cells.json').read_text());sixproof=[]
for cell in six:
 decoded=ingest.decode_source_text(source,cell['raw_text']);candidates=ns['candidates_from_cell'](decoded,source=source,cell_header=cell['cell_header']);target=[(code,text)for code,text,_ in candidates if code==cell['code']]
 if len(target)!=1 or target[0][1]not in ingest.clean_text(decoded):raise RuntimeError('EMIF cell not recovered literally')
 sixproof.append({'page':cell['page'],'code':cell['code'],'text':target[0][1],'header':cell['cell_header'],'literal_cell_verified':True})
cache=json.loads((ROOT/'data/extracted'/f'{source["sha256"]}-page-cell-v1.4.0.json').read_text());extras=json.loads((OUT/'comparison-extra-codes.json').read_text());page_numbers=sorted({x['page']for x in extras});recoveries=[]
for number in page_numbers:
 page=D[number-1];geometry.normalize_native_page(page);words=geometry.words_from_page(page);tables=page.find_tables().tables;existing=[i for i in cache['items']if i['evidence'][0]['page']==number and i['evidence'][0]['method']!='ruled-column-continuation-recovery']
 recovered=gs['recover_missing_columns'](source,number,page,words,tables,existing,ingest.CODE_ANY,ingest.make_item,ingest.clean_text);recoveries.extend({'page':number,'code':i['code']}for i in recovered)
position=ns['national_position']('GO-EMLP02A')
if recoveries or position['component']!='Língua Portuguesa'or position['area']!='Linguagens e suas Tecnologias'or position['years']is not None:raise RuntimeError('Recovery/position proposal failed')
result={'source_id':source['id'],'source_sha256':source['sha256'],'production_modified':False,'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'six_literal_emif_definitions':sixproof,'prefix_duplicate_affected_pages':page_numbers,'new_recoveries_on_those_pages':recoveries,'LP_position':position,'all_checks_passed':True,'note':'Proposal applied only to in-memory function ASTs. Central owner must review/apply, force re-extract and confront complete source before claiming integrated correction.'};(OUT/'emif-recovery-position-proposal-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
