#!/usr/bin/env python3
"""Exact multi-column legal hierarchy of SEDUC156 in the original DOE page."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from ingest import clean_text
SID='sp-seduc156-corpo-2026';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];raw=P.read_bytes();assert hashlib.sha256(raw).hexdigest()==S['sha256'];D=fitz.open(P);assert len(D)==1;p=D[0];normalization=normalize_native_page(p);reader=NativeGlyphText(p);rows=[]
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
for li,cs in enumerate(reader.lines):
 t=''.join(c['text']for c in cs);bs=[c['box']for c in cs];b=[min(v[0]for v in bs),min(v[1]for v in bs),max(v[2]for v in bs),max(v[3]for v in bs)]
 if t.strip():rows.append({'text':t,'bbox':b,'native_line':li})
title=next(r for r in rows if r['text'].startswith('RESOLUÇÃO SEDUC Nº 156,'));nextact=next(r for r in rows if r['text'].startswith('RESOLUÇÃO SEDUC Nº 158,'));bounds=[(0,[28, title['bbox'][1],289,1140]),(1,[293,25,554,1140]),(2,[558,25,819,nextact['bbox'][1]])];selected=[]
for col,b in bounds:
 rs=[r for r in rows if b[0]<=(r['bbox'][0]+r['bbox'][2])/2<b[2]and b[1]<=r['bbox'][1]<b[3]];selected.extend(sorted(rs,key=lambda r:(r['bbox'][1],r['bbox'][0])))
assert selected[0]==title and selected[-2]['text'].strip()=='Anexo(s):'and 'Matriz Curriculares do Ensino Médio.pdf'in selected[-1]['text']
def role(t):
 t=t.strip()
 if t.startswith('RESOLUÇÃO SEDUC Nº 156,'):return'ato_normativo'
 if re.match(r'^CAPÍTULO\s+[IVX]+$',t):return'capitulo_normativo'
 if re.match(r'^Artigo\s+\d+',t):return'artigo_normativo'
 if re.match(r'^(?:§\s*\d+|Parágrafo único)',t):return'paragrafo_normativo'
 if re.match(r'^[IVX]+\s*[-–]',t):return'inciso_normativo'
 if re.match(r'^[a-z]\)',t):return'alinea_normativa'
 if t.startswith('– '):return'considerando_normativo'
 if t=='Resolve:':return'marcador_normativo'
 if t=='Anexo(s):':return'anexo_normativo'
 if t.startswith('Estabelece as diretrizes'):return'ementa_normativa'
 if t.startswith('O Secretário da Educação'):return'preambulo_normativo'
 return None
anchors=[(i,r,role(r['text']))for i,r in enumerate(selected)if role(r['text'])];article_numbers=[int(re.match(r'Artigo\s+(\d+)',r['text'])[1])for _,r,k in anchors if k=='artigo_normativo'];assert article_numbers==list(range(1,17));chapters=[r['text']for _,r,k in anchors if k=='capitulo_normativo'];assert chapters==['CAPÍTULO I','CAPÍTULO II','CAPÍTULO III','CAPÍTULO IV','CAPÍTULO V','CAPÍTULO VI']
# Independently reproduce the complete selected character stream from get_texttrace,
# by original physical columns and baselines; output records are not expectations.
trace_rows=[]
for col,b in bounds:
 buckets={}
 for sp in p.get_texttrace():
  if sp.get('type')==3 or sp.get('dir',(1,0))[0]<.9:continue
  for c in sp['chars']:
   x,y=c[2]
   # Native bbox-top and trace baseline differ by font ascent. Use the physical
   # caption baseline for the top/bottom title boundaries rather than guessed y.
   if c[0]>=0 and b[0]<=x<b[2]and b[1]+9<=y<b[3]+9:buckets.setdefault(round(y,1),[]).append((x,chr(c[0])))
 for y,cs in sorted(buckets.items()):trace_rows.append({'column':col,'baseline':y,'text':' '.join([])or''.join(ch for _,ch in sorted(cs))})
trace_original=''.join(r['text']for r in trace_rows);ligature_count=trace_original.count('ﬁ');trace_text=squash(trace_original.replace('ﬁ','fi'));native_text=squash(''.join(r['text']for r in selected));assert trace_text==native_text,('Selected full original character stream mismatch',len(trace_text),len(native_text))
items=[];checked=[];act='sp-seduc156:act';chapter=None;article=None;paragraph=None;inciso=None
def evidence(r):
 t=clean_text(r['text']);literal=reader.text(r['bbox']);assert squash(t)==squash(clean_text(literal)),(t,literal);checked.append(r['native_line']);return{'source_id':SID,'page':1,'printed_page':'21/139','section':'Resolução SEDUC156/2025, hierarchy from original three-column DOE page','excerpt':t,'locator':f'native-line:{r["native_line"]}','bbox':r['bbox'],'coordinate_space':'display_pdf_after_normalization','page_normalization':normalization,'method':'pymupdf-native-glyph-cluster-v1'}
for n,(start,r,kind)in enumerate(anchors):
 end=anchors[n+1][0]if n+1<len(anchors)else len(selected);rs=selected[start:end];key=f'sp-seduc156:line:{r["native_line"]}';parent=act;number=None
 if kind=='ato_normativo':key=act;parent=None
 elif kind=='capitulo_normativo':chapter=key;article=None;paragraph=None;inciso=None
 elif kind=='artigo_normativo':parent=chapter or act;article=key;paragraph=None;inciso=None;number=re.match(r'Artigo\s+(\d+[°º]?)',r['text'])[1]
 elif kind=='paragrafo_normativo':parent=article;assert parent;paragraph=key;inciso=None
 elif kind=='inciso_normativo':parent=paragraph or article;assert parent;inciso=key
 elif kind=='alinea_normativa':parent=inciso;assert parent
 elif kind=='anexo_normativo':parent=act
 items.append({'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(x['text']for x in rs)),'page':1,'locator':'sp-seduc156-act-v1/'+key,'positions':[{'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'explicit_original_act_scope_Ensino_Medio','position_note':'Legal provisions are not individual learning outcomes; no series assigned from article numerals.'}],'evidence':[evidence(x)for x in rs],'source_context':{'source_role':'Original legal provision or labelled part of SEDUC156; legal hierarchy does not create student learning expectations','source_number_literal':number,'grain':'Caput or explicit paragraph/inciso/alínea; article children remain distinct, all source lines represented exactly once.','reading_order':'Original left column from156title, middle column, right column before158title','learning_objective_claim':False,'adjacent_acts_not_part_of_this_156_adapter':True},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'sp-original-three-column-SEDUC156-legal-hierarchy-v1'})
assert sorted(checked)==sorted(r['native_line']for r in selected)and len(set(checked))==len(checked)
target=ROOT/'data/manifests/uncoded/sp-seduc156-act-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
w={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'sp-original-three-column-SEDUC156-legal-hierarchy-v1','scope':'Only full original SEDUC156act on DOEphysicalpage1/printed21. Preceding PEPact and following158 are documented adjacent exclusions; unchanged generic page is preserved, no page authority claimed. Annex matrices are in a separate Source and not fabricated here.','items':items};target.write_text(json.dumps(w,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':S['sha256'],'original_physical_pages':1,'source_article_numbers':article_numbers,'source_chapters':chapters,'source_native_lines':len(selected),'independent_nonwhite_character_count':len(trace_text),'independent_full_character_stream_equal':trace_text==native_text,'independent_stream_typographic_equivalence':{'from':'U+FB01 ﬁ','to':'fi','occurrences':ligature_count,'scope':'Comparison only: get_texttrace retains the ligature glyph while original RAWDICT emits its two Unicode characters. No spelling/code/source-file substitution.'},'selected_original_regions':bounds,'nodes':len(items),'kinds':dict(collections.Counter(i['kind']for i in items)),'source_lines_exactly_once':True,'sidecar_path':str(target.relative_to(ROOT)),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_manifest_edited':False,'source_ready':False};(OUT/'sp-seduc156-act-v1-source-denominator.json').write_text(json.dumps({'summary':report,'source_labelled_anchors':[{'native_line':r['native_line'],'text':r['text'],'kind':k,'bbox':r['bbox']}for _,r,k in anchors]},ensure_ascii=False,indent=2)+'\n');(OUT/'sp-seduc156-act-v1-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
