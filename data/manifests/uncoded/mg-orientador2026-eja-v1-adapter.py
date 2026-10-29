#!/usr/bin/env python3
"""Complete original three EJA tables, heterogeneous objective block and prison offer."""
import collections,datetime,hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-southeast-completeness';sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from geometry import normalize_native_page,words_from_page,clipped_words,words_text
from ingest import clean_text
SID='mg-em-documento-orientador-2026';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);P=ROOT/S['local_path'];assert hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];D=fitz.open(P);assert len(D)==46
peer=OUT/'mg-orientador2026-eja-objectives-semantic-peer.json';assert hashlib.sha256(peer.read_bytes()).hexdigest()=='e50ec5b35caeca6969637d1442abd1393367fe0c71844277e2cb9e02579b2775'
items=[];census=[];checks=[];readers={};norms={};folios={};cells_seen=[]
def flat(t):return' '.join(t.split())
def squash(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t).replace('\u00ad',''))
def ev(pn,box,text=None):
 literal=readers[pn].text(box);text=clean_text(literal)if text is None else text;assert squash(text)in squash(clean_text(literal));checks.append({'page':pn,'bbox':list(box),'literal_checked':True});return{'source_id':SID,'page':pn,'printed_page':folios[pn],'section':'OriginalEJA material-summary table or prison-offer paragraph','excerpt':text,'locator':'bbox:'+','.join(str(round(v,4))for v in box),'bbox':list(box),'coordinate_space':'display_pdf_after_normalization','page_normalization':norms[pn],'method':'pymupdf-native-glyph-cluster-v1'}
def add(key,kind,pn,ee,parent,component,period,context):
 items.append({'source_id':SID,'artifact_sha256':S['sha256'],'key':key,'parent_key':parent,'code':None,'kind':kind,'text':clean_text(' '.join(e['excerpt']for e in ee)),'page':pn,'locator':'mg-orientador2026-eja-v1/'+key,'positions':[{'stage':'EM','component':component,'area':None,'years':None,'year_label':None,'age_group':None,'period':period,'position_origin':'explicit_original_EJA_period_column_or_prison_offer_paragraph','position_note':'1º/2º/3º Período is not converted to school year, semester or age. Whole source material summaries, no fabricated national codes or individual expectations.'}],'evidence':ee,'source_context':{'modality':'Educação de Jovens e Adultos','learning_objective_claim':False,**context},'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','extraction_method':'mg-original-EJA2026-period-component-material-summary-v1'})
for pn in [31,32,33]:
 p=D[pn-1];norms[pn]=normalize_native_page(p);reader=readers[pn]=NativeGlyphText(p);folios[pn]=None
 for cs in reader.lines:
  t=''.join(c['text']for c in cs);bs=[c['box']for c in cs]
  if t.strip().isdigit()and min(b[1]for b in bs)>p.rect.height*.9:folios[pn]=t.strip()
 tables=p.find_tables(strategy='lines').tables;assert len(tables)==1;table=tables[0];assert table.row_count==5 and table.col_count==4
 headers=[flat(reader.text(b))for b in table.rows[0].cells];assert headers==['Período','Componente Curricular','Acesso ao material','Resumo do material'];period_box=table.rows[1].cells[0];period=flat(reader.text(period_box));assert period==f'{pn-30}º Período';period_key=f'mg2026:eja:period:{pn-30}';add(period_key,'periodo_curricular',pn,[ev(pn,period_box)],None,None,period,{'source_role':'Literal merged period cell spanning all four component rows','original_table_headers':headers,'original_header_evidence':[ev(pn,b)for b in table.rows[0].cells]})
 row_records=[];native_words=words_from_page(p)
 for ri in range(1,5):
  row=table.rows[ri];boxes=row.cells;name=flat(reader.text(boxes[1]));unit=f'{period_key}:row:{ri}';assert name;add(unit,'unidade_curricular',pn,[ev(pn,boxes[1])],period_key,name,period,{'source_role':'Explicit Componente Curricular cell; supplementary activities remain separately named curriculum offerings','technical_grid_row':ri,'original_component_label':name})
  material=reader.text(boxes[2]);links=[{'url':l['uri'],'anchor_bbox':list(l['from'])}for l in p.get_links()if l.get('uri')and fitz.Rect(l['from']).intersects(fitz.Rect(boxes[2]))];add(unit+':material','referencia_bibliografica',pn,[ev(pn,boxes[2])],unit,name,period,{'source_role':'Original Acesso ao material cell, abbreviated titles/ellipses preserved; no invented expanded filename','original_embedded_links':links})
  text=reader.text(boxes[3]);independent=words_text(clipped_words(native_words,*boxes[3]));assert squash(clean_text(text))==squash(clean_text(independent)),(pn,ri,text,independent)
  if pn==33 and ri==3:
   rows=[]
   for cs in reader.lines:
    selected=[c for c in cs if boxes[3][0]<=(c['box'][0]+c['box'][2])/2<boxes[3][2]and boxes[3][1]<=(c['box'][1]+c['box'][3])/2<boxes[3][3]]
    if selected:
     t=''.join(c['text']for c in selected);bb=[c['box']for c in selected]
     if t.strip():rows.append({'text':t,'bbox':[min(b[0]for b in bb),min(b[1]for b in bb),max(b[2]for b in bb),max(b[3]for b in bb)]})
   goal=next(i for i,r in enumerate(rows)if flat(r['text'])=='Objetivos específicos:');assert len([r for r in rows[goal:]if r['text'].lstrip().startswith('-')])==3
   add(unit+':summary','contexto_curricular',pn,[ev(pn,r['bbox'],clean_text(r['text']))for r in rows[:goal]],unit,name,period,{'source_role':'Original introduction to three didactic sequences, before explicit objectives block'})
   add(unit+':objectives','objetivo_curricular',pn,[ev(pn,r['bbox'],clean_text(r['text']))for r in rows[goal:]],unit,name,period,{'source_role':'Whole heterogeneous Objetivos específicos block inside Resumo do material','classification':'formative_purpose','grain':'source_material_summary_objectives_block','source_bullets':3,'independent_semantic_peer':{'path':str(peer.relative_to(ROOT)),'sha256':hashlib.sha256(peer.read_bytes()).hexdigest()},'no_isolation_of_last_learner_verb':True})
  else:add(unit+':summary','experiencia_sugerida'if ri in [2,4]else'contexto_curricular',pn,[ev(pn,boxes[3])],unit,name,period,{'source_role':'Whole original supplementary research/proposal summary'if ri in [2,4]else'Whole original material topical summary','grain':'Entire original Resumo do material cell; no atomic activity/verb splitting'})
  row_records.append({'row':ri,'component':name,'period':period,'original_cells':[list(b)if b else None for b in boxes],'summary_native_words_equal':True})
 census.append({'page':pn,'printed_page':folios[pn],'table_bbox':list(table.bbox),'headers':headers,'rows':row_records,'source_period':period})
 if pn==33:
  words=[w for w in native_words if w['top']>table.bbox[3]and w['bottom']<p.rect.height*.9];words.sort(key=lambda w:(w['block'],w['line'],w['word']));assert words and words[0]['text']=='O';group='mg2026:eja:prison-offer';ee=[ev(pn,[w['x0'],w['top'],w['x1'],w['bottom']],w['text'])for w in words];add(group,'oferta_trilha',pn,ee,None,None,None,{'source_role':'Explicit EJA offer for schools in prison units, full original paragraph and material reference','no_period_assumed_from_preceding_third_period_table':True})
  for number in [1,2]:
   st=next(i for i,w in enumerate(words)if w['text']==f'{number})');stop=next(i+1 for i,w in enumerate(words[st:],st)if w['text'].endswith(';'if number==1 else'Comunicação.'));ww=words[st:stop];title=flat(' '.join(w['text']for w in ww[1:])).rstrip(';.');add(group+f':component:{number}','unidade_curricular',pn,[ev(pn,[w['x0'],w['top'],w['x1'],w['bottom']],w['text'])for w in ww],group,title,None,{'source_role':'Original explicitly enumerated prison-offer component title','source_list_number_literal':f'{number})','enumeration_is_not_official_code':True,'overlap_with_parent_paragraph_is_explicit_named_field_granularity':True})
assert len(items)==43;target=ROOT/'data/manifests/uncoded/mg-orientador2026-eja-v1-items.json';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if target.exists():stamp=json.loads(target.read_text())['generated_at']
w={'source_id':SID,'artifact_sha256':S['sha256'],'actor_type':'automated','actor_id':'curriculos-abertos:southeast-completeness','generated_at':stamp,'method':'mg-original-EJA2026-period-component-material-summary-v1','scope':'All3EJA tables31–33:3literal periods,12component rows,12material refs,12whole summaries with heterogeneous objective block kept separate, plus prison offer and2explicit component names. Not individual skills; no year/age conversion from periods. Other chapters preserved and unreconciled.','items':items};target.write_text(json.dumps(w,ensure_ascii=False,separators=(',',':'))+'\n');report={'source_id':SID,'source_sha256':S['sha256'],'all_original_tables':census,'periods':3,'component_table_rows':12,'prison_offer_components':2,'heterogeneous_objective_blocks':1,'semantic_peer_sha256':hashlib.sha256(peer.read_bytes()).hexdigest(),'nodes':len(items),'evidence_fragments':len(checks),'literal_failures':[],'kinds':dict(collections.Counter(i['kind']for i in items)),'sidecar_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source_manifest_edited':False,'source_ready':False};(OUT/'mg-orientador2026-eja-v1-source-denominator.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='all_original_tables'},ensure_ascii=False,indent=2))
