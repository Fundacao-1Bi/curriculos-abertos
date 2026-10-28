#!/usr/bin/env python3
import json,sys,fitz
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'pipeline'),str(OUT)]
from rn_document_roles_proposal import rewrite_page
from ingest import CODE_ANY,make_item,clean_text
sources={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};results=[]
s=sources['rn-dcec-computacao'];D=fitz.open(ROOT/s['local_path'])
for n in [61,574]:
 p=D[n-1];items,r=rewrite_page(s,n,p,[],[],CODE_ANY,make_item,clean_text)
 results.append({'case':'narrative_code_example_not_promoted','page':n,'codes_in_original':CODE_ANY.findall(p.get_text()),'created_learning_records':len(items),'pass':not items})
p=D[75];tables=p.find_tables(strategy='lines').tables
cached=json.loads((ROOT/'data/extracted'/f'{s["sha256"]}-page-cell-v1.4.0.json').read_text());primary=[i for i in cached['items']if i.get('code')=='EF01CO03'and i['evidence'][0]['page']==76 and i['evidence'][0]['method']=='pymupdf-ruled-cell']
items,r=rewrite_page(s,76,p,tables,primary,CODE_ANY,make_item,clean_text);references=[i for i in items if i.get('source_context',{}).get('documentary_role')in('explanation_reference_context','pedagogical_reference_context')]
results.append({'case':'explanation_citations_retained_as_references_primary_preserved','page':76,'reference_codes':[i['code']for i in references],'primary_original_ids':[i['id']for i in primary],'primary_ids_preserved':[i['id']for i in primary if i in items],'all_contexts_retained':all(i.get('source_context',{}).get('original_cell_text')for i in references),'pass':bool(primary)and all(i in items for i in primary)and bool(references)and all(i['kind']=='referencia_no_documento'and i['text']==i['code']for i in references)})
try:rewrite_page({**s,'sha256':'0'*64},76,p,tables,[],CODE_ANY,make_item,clean_text)
except ValueError:results.append({'case':'wrong_original_sha_rejected','pass':True})
else:results.append({'case':'wrong_original_sha_rejected','pass':False})
original=[{'keep':'sentinel'}];got,r=rewrite_page({'id':'unrelated-source'},76,p,[],original,CODE_ANY,make_item,clean_text);results.append({'case':'unrelated_source_unchanged','pass':got is original})
s=sources['rn-trilhas-aprofundamento'];D=fitz.open(ROOT/s['local_path'])
for n in [16,17,18,19,33,35,144,262,378,484,100,300]:
 p=D[n-1];items,r=rewrite_page(s,n,p,[],[],CODE_ANY,make_item,clean_text);defs=[i for i in items if i['kind']=='habilidade'];refs=[i for i in items if i['kind']=='referencia_no_documento']
 if n in[16,17,18,19]:ok=len(defs)==12 and not refs;case='explicit_definition_sheet'
 elif n in[100,300]:ok=not items;case='unmarked_prose_not_promoted'
 else:ok=not defs and bool(refs)and all(i['text']==i['code']for i in refs);case='explicit_reference_code_card'
 results.append({'case':case,'page':n,'definitions':len(defs),'references':len(refs),'pass':ok})
summary={'cases':results,'all_pass':all(r['pass']for r in results),'note':'Source-derived role controls, including primary learning preservation, reference contexts, unrelated source, wrong SHA, unmarked prose and two narrative examples. Not a curriculum completeness assertion.'};(OUT/'negative-and-role-regressions.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
if not summary['all_pass']:raise SystemExit(1)
