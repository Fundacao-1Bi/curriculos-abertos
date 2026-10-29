#!/usr/bin/env python3
"""Reconcile every selected cell's literal content against all semantic fragments.
Independent table.extract values; no adapter/helper import and no normalization of
accents, punctuation or hard hyphens. Only source list/code locators are excluded.
"""
from pathlib import Path
import fitz,json,re,collections,hashlib
R=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent;F=R/'data/manifests/uncoded/ap-rca614-items.json';frozen=F.read_bytes();s=json.loads(frozen);D=fitz.open(R/'data/raw/AP/ap-native-ei-ef.pdf');den=json.loads((A/'ap614-source-denominators.json').read_text())
CODE=r'E[IF]\d{2,3}[A-Z]{2}(?:\s*[-‐‑–]?\s*AP\s*\d{2}|\s*\d{2}(?:\s*[-‐‑–]?\s*AP\s*\d{2})?|\s*[-‐‑–]\s*\d{2})'
code_rx=re.compile(r'\(?\s*'+CODE+r'\s*\)?')
N=lambda t:re.sub(r'\s+',' ',t).strip()
DOWN=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾','0123456789+-=()')
frags=collections.defaultdict(list)
for i in s['items']:
 if i['kind'] not in ('objetivo_aprendizagem','experiencia_aprendizagem','habilidade'):continue
 for e in i['evidence']:
  if e.get('evidence_role')!='code_locator':frags[e['page']].append(e)
by=collections.defaultdict(list)
for c in den['expected_selected_cells']:by[c['page']].append(c)
errors=[];typography_equivalences=[];checked=0;matched_fragments=0
for pn,cells in sorted(by.items()):
 tabs=D[pn-1].find_tables(strategy='lines_strict').tables;values=[t.extract() for t in tabs]
 for c in cells:
  tab=tabs[c['table']];box=tab.rows[c['row']].cells[c['column']];raw=values[c['table']][c['row']][c['column']] or ''
  expected=N(re.sub('[\uf0b7•]','',code_rx.sub('',raw)).translate(DOWN))
  selected=[e for e in frags[pn] if box[0]-.5<=(e['bbox'][0]+e['bbox'][2])/2<=box[2]+.5 and box[1]-.5<=(e['bbox'][1]+e['bbox'][3])/2<=box[3]+.5]
  selected.sort(key=lambda e:(e['bbox'][1],e['bbox'][0]));actual=N(' '.join(e['excerpt'] for e in selected).translate(DOWN));checked+=1;matched_fragments+=len(selected)
  if expected!=actual and expected==actual.replace('ﬂ','fl'):typography_equivalences.append({'page':pn,'table':c['table'],'row':c['row'],'column':c['column'],'native_glyph':'U+FB02','table_extract_expansion':'fl','source_spelling_not_editorially_corrected':True})
  elif expected!=actual:errors.append({'page':pn,'table':c['table'],'row':c['row'],'column':c['column'],'expected_source_without_code_or_bullet':expected,'actual_semantic_fragments':actual})
assert F.read_bytes()==frozen
report={'source_id':s['source_id'],'artifact_sha256':s['artifact_sha256'],'sidecar_sha256':hashlib.sha256(frozen).hexdigest(),'method':'Independent native table.extract content versus semantic evidence fragments in matching physical cells; whitespace, source-proven superscripts and U+FB02→fl compatibility expansion only; no punctuation/accent/hard-hyphen removal','selected_cells':checked,'semantic_fragments_matched_to_cells':matched_fragments,'explicit_native_ligature_expansion_cases':typography_equivalences,'errors':errors,'sidecar_unchanged':True}
(A/'ap614-cell-character-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'checked':checked,'errors':len(errors),'first_errors':errors[:5]},ensure_ascii=False))
