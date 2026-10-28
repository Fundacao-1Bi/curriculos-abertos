#!/usr/bin/env python3
"""Independent full-source physical trace census of explicit RN field labels."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;P=ROOT/'data/raw/RN/rn-trilhas-aprofundamento.pdf';SHA='fac7333112fcfaac3d99d74f72f206bea8e9a4b256e770a9ea0f2eace99b027a';D=fitz.open(P);body=json.loads((OUT/'trilhas-independent-body-census.json').read_text());overviews={o['page']for o in body['overviews']};rows=[];unknown=[]
def norm(t):return re.sub(r'\s+',' ',''.join(c for c in unicodedata.normalize('NFKD',t).casefold()if not unicodedata.combining(c))).strip()
for n,p in enumerate(D,1):
 if n<33 or n in overviews:continue
 for s in p.get_texttrace():
  if s['type']!=0:continue
  text=''.join(chr(c[0])for c in s['chars']);t=norm(text).rstrip(': ').strip();role=None
  if s['size']>=11.5:
   if t=='ementa':role='ementa'
   elif re.fullmatch(r'objetos?\s+(?:do|de)\s+conhecimentos?',t):role='objetos_conhecimento'
   elif re.fullmatch(r'sugestoes\s+didaticos?[-–— ]*metodologicas',t):role='sugestoes_didaticas'
   elif re.fullmatch(r'sugestoes\s+de\s+avaliacao\s+processual',t):role='avaliacao'
   elif re.fullmatch(r'sugestoes\s+de\s+fontes',t):role='fontes'
   elif re.fullmatch(r'habilidades\s+dos\s+eixos\s+estruturantes',t):role='referencias_eixos'
  if re.match(r'^formacao\s+d(?:o|os)\s+professor(?:es)?\s*:',norm(text)):role='formacao_professor'
  if role:rows.append({'page':n,'role':role,'original_label_span':text,'bbox':list(s['bbox']),'font':s['font'],'size':s['size'],'direction':list(s['dir']),'method':'original-visible-physical-glyph-trace-label'})
  elif s['size']>=11.5 and re.search(r'ementa|sugestoes|objetos.{0,8}conhecimento|eixos.{0,12}estruturantes',t)and len(t)<80:unknown.append({'page':n,'text':text,'bbox':list(s['bbox']),'size':s['size']})
# Parent scopes come from this peer's independently located visible unit headings.
units=[]
for tr in body['trilhas']:
 for i,h in enumerate(tr['unit_headers']):
  end=tr['unit_headers'][i+1]['page']-1 if i+1<len(tr['unit_headers'])else tr['page_end'];units.append({**h,'page_end':end,'trilha_key':tr['toc_key']})
for r in rows:
 owners=[h for h in units if h['page']<=r['page']<=h['page_end']];r['peer_unit_header_page']=owners[0]['page']if len(owners)==1 else None;r['peer_unit_number']=owners[0]['printed_unit_number']if len(owners)==1 else None;r['peer_trilha_key']=owners[0]['trilha_key']if len(owners)==1 else None
v={'source_id':'rn-trilhas-aprofundamento','source_sha256':SHA,'actor_type':'automated','method':'Entire485page get_texttrace census of visible literal field label spans, independently of author census/uncoded output;33overviews excluded. Explicit label aliases only, not verbs or punctuation. Unit scope follows peer large UC-header trace inventory.','all_pages':len(D),'overview_pages_excluded':len(overviews),'headings':rows,'counts':dict(collections.Counter(r['role']for r in rows)),'unclassified_heading_like_spans':unknown,'source_ready':False,'scope':'Explicit header denominator. Unlabeled continuations require full-fragment geometric/text confrontation; absence of a label does not authorize excluding its body.'};(OUT/'trilhas-independent-field-headings.json').write_text(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({'counts':v['counts'],'unknown':unknown,'unowned':sum(r['peer_unit_header_page']is None for r in rows)},ensure_ascii=False,indent=2))
