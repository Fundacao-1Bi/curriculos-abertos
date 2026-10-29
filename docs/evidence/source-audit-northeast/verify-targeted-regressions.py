#!/usr/bin/env python3
"""Independent targeted source-cell regression checks, without claiming whole-source completion."""
import json,pathlib,re,unicodedata,datetime
import pymupdf as fitz
ROOT=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent;ss={s['id']:s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())};rev='page-cell-v1.4.0'
def norm(t):return ''.join(unicodedata.normalize('NFKD',re.sub(r'(?<=[a-zà-ÿ])[-\u00ad]\s+(?=[a-zà-ÿ])','',t.replace('\u00ad',''))).encode('ascii','ignore').decode().casefold().split())
def source(sid):
 s=ss[sid];doc=fitz.open(ROOT/s['local_path']);cache=json.loads((ROOT/'data/extracted'/f'{s["sha256"]}-{rev}.json').read_text());return s,doc,cache
checks=[]
s,d,r=source('ce-dcrc-ei-ef-2019');rows=d[343].find_tables().tables[0].extract();assert rows[3][0]=='HABILIDADES'
for code in ['EF89EF05','EF89EF06','EF89EF07','EF89EF08']:
 original=next(v for v in rows[3] if v and code in v);expected=original.split(code,1)[1].lstrip(') \n');actual=[i for i in r['items'] if i.get('code')==code and i['evidence'][0]['page']==344];assert len(actual)==1 and norm(actual[0]['text'])==norm(expected)
 checks.append({'source_id':s['id'],'page':344,'code':code,'expected_from':'Original physical semantic HABILIDADES row, independent of extracted IDs','result':'source_skill_code_prose_preserved','extracted_text':actual[0]['text'],'source_cell':original,'item_id':actual[0]['id']})
for code in ['EF67EF06','EF67EF07']:
 assert not [i for i in r['items'] if i.get('code')==code and i['evidence'][0]['page']==344 and i.get('kind') in ['habilidade','objetivo_aprendizagem','habilidade_ifa','habilidade_projeto_vida']]
 checks.append({'source_id':s['id'],'page':344,'code':code,'result':'reference_not_fabricated_as_learning','limitation':'Generic source relations still need explicit structural representation; their disappearance as fake skills is not full source reconciliation.'})
s,d,r=source('pb-proposta-ei-ef');cell=d[309].find_tables().tables[1].extract()[6][0];expected=cell.split('(EF06MA06)',1)[1].split('(EF06MA07)',1)[0].strip();actual=[i for i in r['items'] if i.get('code')=='EF06MA07' and i['evidence'][0]['page']==310];assert len(actual)==1 and norm(actual[0]['text'])==norm(expected)
checks.append({'source_id':s['id'],'page':310,'code':'EF06MA07','result':'trailing_code_preceding_objective_preserved','item_id':actual[0]['id'],'source_cell':cell,'extracted_text':actual[0]['text']})
local_objective='Pesquisar, apreciar e analisar formas contemporâneas de representação artística visual de artistas paraibanos, nordestinos, brasileiros e estrangeiros, em diferentes contextos históricos e matrizes estéticas e culturais'
structured=[i for i in r['items'] if i['evidence'][0]['page']==139 and i.get('kind') not in ['secao_normativa','referencia_no_documento'] and norm(local_objective) in norm(i['text'])]
checks.append({'source_id':s['id'],'page':139,'result':'local_uncoded_objective_structuring_pending' if not structured else 'local_objective_found_requires_relation_review','source_local_objective':local_objective,'limitation':'No national code may be fabricated for local objective; preserve documented row references separately.'})
assert '6º Ano' in d[98].get_text() and 'EF67PB01' in d[99].get_text()
checks.append({'source_id':s['id'],'page':100,'literal_code':'EF67PB01','heading_evidence_page':99,'heading':'6º Ano','result':'literal_non_national_code_requires_source_classification','limitation':'Preserve literal identifier and local objective context; no PB national component or6+7year mapping inferred.'})
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'codex:data_northeast','extraction_revision':rev,'checks':checks,'summary':{'correct_source_code_prose_pairs':5,'reference_codes_no_longer_fabricated':2,'open_structure_classification_checks':2,'whole_sources_reconciled_by_this_test':0},'scope':'Specific regression anchors only; requires affected-range reprocessing/reconciliation before source-level acceptance.'};(O/'targeted-regressions-v1.4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary'],ensure_ascii=False,indent=2))
