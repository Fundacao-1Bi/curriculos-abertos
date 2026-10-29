#!/usr/bin/env python3
"""Independent physical marker/heading inventory. Does NOT read sidecar outputs."""
from pathlib import Path
import fitz,json,hashlib,collections,re
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-uncoded/ei-temas/expected-target-ids.json'
sid='es-curriculo-es-2020-vol-01-educacao-infantil-rev2026';doc=fitz.open(ROOT/f'data/raw/ES/{sid}.pdf')
fields=[(70,80,'EO'),(81,92,'TS'),(93,110,'EF'),(111,120,'ET'),(121,130,'CG')]
pairs=[(72,73),(74,75),(76,77),(78,79),(84,85),(86,87),(88,89),(90,91),(96,97),(98,99),(100,101),(102,103),(104,105),(106,107),(108,109),(114,115),(116,117),(118,119),(124,125),(126,127),(128,129)]
expected=[];denom=[]
for cp,pp in pairs:
 ct=doc[cp-1].find_tables().tables[0];age=ct.extract()[1][0];fc=next(c for st,en,c in fields if st<=cp<=en)
 tab=doc[pp-1].find_tables().tables[0]
 for col,kind in[(1,'acao_docente'),(2,'indicador_observacao')]:
  box=tab.rows[1].cells[col];markers=[]
  for b in doc[pp-1].get_text('rawdict')['blocks']:
   for l in b.get('lines',[]):
    chars=[c for sp in l['spans']for c in sp['chars']if box[0]<=(c['bbox'][0]+c['bbox'][2])/2<=box[2]and box[1]<=(c['bbox'][1]+c['bbox'][3])/2<=box[3]]
    if not chars or not ''.join(c['c']for c in chars).lstrip().startswith('•'):continue
    marker=next(c for c in chars if c['c']=='•');y=min(c['bbox'][1]for c in chars if not c['c'].isspace())
    locator=f'quadro:p{pp}:col{col}:y{round(y*10)}';token=f'{sid}|{pp}|{locator}|uncoded|occurrence:0'
    record={'source_id':sid,'page':pp,'kind':kind,'field':fc,'age_label':age,'locator':locator,'id':f'ca:{sid}:'+hashlib.sha256(token.encode()).hexdigest()[:20],'marker_bbox':list(marker['bbox']),'column_bbox':list(box)}
    expected.append(record);markers.append(record)
  denom.append({'field':fc,'age_label':age,'objective_page':cp,'column_page':pp,'column_role':kind,'bullet_markers':len(markers),'body_bbox':list(box)})
# Independently enumerated six explicit card labels in every general/field diagram.
rights={'Conviver','Brincar','Participar','Explorar','Expressar','Conhecer-se'}
for pn in[61,71,82,95,111,112,121,122]:
 for b in doc[pn-1].get_text('blocks'):
  label=b[4].strip()
  if label not in rights:continue
  loc=f'right:p{pn}:{label}';token=f'{sid}|{pn}|{loc}|uncoded|occurrence:0';expected.append({'source_id':sid,'page':pn,'kind':'direito_aprendizagem','locator':loc,'id':f'ca:{sid}:'+hashlib.sha256(token.encode()).hexdigest()[:20],'label_bbox':list(b[:4]),'label':label})
result={'actor_type':'automated','method':'Rawdict bullet glyphs and native card labels independently enumerated from original physical cells; no sidecar or imported record read. IDs derived from source anchors and declared pipeline algorithm.','source_id':sid,'artifact_sha256':hashlib.sha256((ROOT/f'data/raw/ES/{sid}.pdf').read_bytes()).hexdigest(),'counts':dict(collections.Counter(x['kind']for x in expected)),'by_field_age_column':denom,'expected':expected}
assert result['counts']=={'acao_docente':210,'indicador_observacao':259,'direito_aprendizagem':36},result['counts']
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['counts'])
