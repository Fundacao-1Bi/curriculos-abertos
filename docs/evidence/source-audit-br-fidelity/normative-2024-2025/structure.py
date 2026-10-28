#!/usr/bin/env python3
"""Single-column legal structure from a frozen, exhaustive native-line census.

No pipeline/core/Source mutation. Run census before build. Native wording, labels,
word boxes and physical continuations are retained; no learning is inferred.
"""
import collections,datetime,hashlib,json,re,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
SPECS=[('br-dcn-em-2024','br-dcn-2024-normative.json',44),('br-ifa-parametros-2025','br-ifa-2025-normative-only.json',31),('br-educacao-digital-midiatica-2025','br-digital-2025-normative.json',42)]
ACTOR='curriculos-abertos:independent-native-normative-structure-auditor'
def sha(value):return hashlib.sha256(value).hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def union(boxes):
 rect=fitz.Rect(boxes[0])
 for box in boxes[1:]:rect|=fitz.Rect(box)
 return list(rect)
def classify(text):
 patterns=[('titulo_normativo',r'^(TÍTULO)\s+([IVXLCDM]+)\s*$'),('capitulo_normativo',r'^(CAPÍTULO)\s+([IVXLCDM]+)\s*$'),('subsecao_normativa',r'^(Subseção)\s+([IVXLCDM]+)\s*$'),('secao_ato_normativo',r'^(Seção)\s+([IVXLCDM]+)\s*$'),('artigo_normativo',r'^(Art\.)\s*(\d+)[º°.\s]'),('paragrafo_normativo',r'^(§)\s*(\d+)[º°.\s]'),('paragrafo_normativo',r'^(Parágrafo)\s+(único)\.'),('inciso_normativo',r'^([IVXLCDM]+)\s*([-–—])\s+'),('alinea_normativa',r'^([a-z])\)\s+'),('item_normativo',r'^(\d+)\)\s+')]
 for kind,pattern in patterns:
  match=re.match(pattern,text)
  if match:return kind,(match.group(2) if kind not in ('inciso_normativo','alinea_normativa','item_normativo') else match.group(1))
 return None,None
def census():
 sources={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};output=[]
 for sid,_,expected in SPECS:
  source=sources[sid];path=ROOT/source['local_path'];assert sha(path.read_bytes())==source['sha256'];rows=[]
  with fitz.open(path) as pdf:
   for pi,page in enumerate(pdf):
    grouped=collections.defaultdict(list)
    for wi,w in enumerate(page.get_text('words',sort=False)):grouped[(w[5],w[6])].append({'index':wi,'word':w[4],'bbox':list(w[:4])})
    lines=[]
    for (block,line),words in grouped.items():
     text=' '.join(w['word'] for w in words);box=union([w['bbox'] for w in words]);furniture=(sid=='br-dcn-em-2024' and box[1]>=775) or text.startswith('PROCESSO Nº:') or (text.isdigit() and box[1]>785) or (pi==0 and text.startswith('(*)'))
     kind,label=classify(text);lines.append({'id':f'p{pi+1}:b{block}:l{line}','page':pi+1,'bbox':box,'text':text,'words':words,'furniture':furniture,'marker_kind':kind if not furniture else None,'marker_label':label if not furniture else None,'external_annex_owned':sid=='br-ifa-parametros-2025' and pi>=16 and not furniture})
    rows+=sorted(lines,key=lambda x:(x['page'],round(x['bbox'][1],2),x['bbox'][0]))
   pages=len(pdf)
  articles=[int(r['marker_label']) for r in rows if r['marker_kind']=='artigo_normativo' and not r['external_annex_owned']];assert articles==list(range(1,expected+1)),(sid,articles)
  counts=collections.Counter(r['marker_kind'] for r in rows if r['marker_kind'] and not r['external_annex_owned']);output.append({'source_id':sid,'artifact':source['local_path'],'artifact_sha256':source['sha256'],'pages':pages,'expected_articles':expected,'observed_article_sequence':articles,'native_lines':len(rows),'native_word_occurrences':sum(len(r['words']) for r in rows),'marker_counts':dict(counts),'lines':rows})
 payload={'actor_type':'automated','actor_id':ACTOR,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Complete native words, physical single-column line order and explicit legal markers; denominator fixed before building sidecar nodes. Running furniture retained separately. IFA2025 annex unchanged under its own already-verified58-node adapter.','sources':output};dump(OUT/'normative-census.json',payload);print(json.dumps({'sources':[{k:v for k,v in s.items() if k!='lines'} for s in output]},ensure_ascii=False))
def build():
 path=OUT/'normative-census.json';raw=path.read_bytes();census=json.loads(raw);stamp=census['generated_at'];summaries=[]
 for source,(_,filename,_) in zip(census['sources'],SPECS):
  sid=source['source_id'];assert sha((ROOT/source['artifact']).read_bytes())==source['artifact_sha256'];nodes=[];claims={};current=None;stack={};article=paragraph=inciso=alinea=None;body_started=False;root_key='norma';headers={};kind_counter=collections.Counter();parent_counters=collections.Counter()
  def add(kind,parent,row,label=None,key=None):
   nonlocal current
   kind_counter[kind]+=1;parent_counters[(parent,kind)]+=1;key=key or f'{parent or "root"}-{kind}-{label or parent_counters[(parent,kind)]}'
   assert not any(n['key']==key for n in nodes),key
   node={'key':key,'parent_key':parent,'kind':kind,'source_number':label,'rows':[]};nodes.append(node);current=node;attach(node,row);return node
  def attach(node,row):assert row['id'] not in claims;claims[row['id']]=node['key'];node['rows'].append(row)
  for row in source['lines']:
   if row['external_annex_owned']:continue
   text=row['text'];kind=row['marker_kind'];label=row['marker_label']
   if row['furniture']:
    # Separate physical publication marks from the legal clause that crosses the page.
    previous=current
    if row['page'] not in headers:headers[row['page']]=add('credito_documental',root_key,row,key=f'publicacao-p{row["page"]}')
    else:attach(headers[row['page']],row)
    current=previous;continue
   if text.startswith('RESOLUÇÃO CNE/CEB Nº'):
    assert not any(n['key']==root_key for n in nodes);add('ato_normativo',None,row,key=root_key);continue
   if text.startswith('MARIA DO PILAR LACERDA'):
    add('assinatura_ato_normativo',root_key,row,key='assinatura-ato');article=paragraph=inciso=alinea=None;continue
   if kind in ('titulo_normativo','capitulo_normativo','secao_ato_normativo','subsecao_normativa'):
    levels=['titulo_normativo','capitulo_normativo','secao_ato_normativo','subsecao_normativa'];level=levels.index(kind);parent=next((stack[k] for k in reversed(levels[:level]) if k in stack),root_key)
    for k in levels[level:]:stack.pop(k,None)
    n=add(kind,parent,row,label);stack[kind]=n['key'];article=paragraph=inciso=alinea=None;body_started=True;continue
   if kind=='artigo_normativo':
    parent=next((stack[k] for k in ['subsecao_normativa','secao_ato_normativo','capitulo_normativo','titulo_normativo'] if k in stack),root_key);n=add(kind,parent,row,label,key=f'artigo-{label}');article=n['key'];paragraph=inciso=alinea=None;body_started=True;continue
   if kind=='paragrafo_normativo':assert article;paragraph=add(kind,article,row,label)['key'];inciso=alinea=None;continue
   if kind=='inciso_normativo':assert article;inciso=add(kind,paragraph or article,row,label)['key'];alinea=None;continue
   if kind=='alinea_normativa':assert inciso or paragraph or article;alinea=add(kind,inciso or paragraph or article,row,label)['key'];continue
   if kind=='item_normativo':assert alinea or inciso or paragraph or article;add(kind,alinea or inciso or paragraph or article,row,label);continue
   if current is None or (current['kind']=='ato_normativo'):
    # A preamble is source documentary context, not part of the first article.
    if not any(n['key']=='preambulo' for n in nodes):add('preambulo_normativo',root_key,row,key='preambulo')
    else:current=next(n for n in nodes if n['key']=='preambulo');attach(current,row)
   else:attach(current,row)
  keys={n['key'] for n in nodes};assert root_key in keys;assert all(not n['parent_key'] or n['parent_key'] in keys for n in nodes);items=[]
  for n in nodes:
   evidence=[]
   for index,row in enumerate(n['rows']):
    evidence.append({'source_id':sid,'page':row['page'],'printed_page':None,'section':n['key'],'locator':f'{sid}:normative:{n["key"]}:fragment:{index+1}','excerpt':row['text'],'bbox':row['bbox'],'regions':[w['bbox'] for w in row['words']],'native_line_ids':[row['id']],'method':'pymupdf-native-legal-line-fragments-v1'})
   item={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'key':n['key'],'parent_key':n['parent_key'],'code':None,'kind':n['kind'],'source_number':n['source_number'],'page':n['rows'][0]['page'],'text':'\n'.join(e['excerpt'] for e in evidence),'locator':f'{sid}:normative:{n["key"]}','positions':[],'evidence':evidence,'source_order':len(items)+1,'actor_type':'automated','actor_id':ACTOR,'technical_validation_status':'primary_legal_marker_and_all_native_fragments_checked','source_context':{'documentary_role':'normative_provision_not_learning','wording_policy':'Primary native words and punctuation unchanged; whitespace/line breaks only serialized between physically ordered source lines.','native_line_ids':[r['id'] for r in n['rows']],'census_sha256':sha(raw),'heading_contains_own_label_and_caption':n['kind'] in ('titulo_normativo','capitulo_normativo','secao_ato_normativo','subsecao_normativa')}}
   if n['kind'] in ('titulo_normativo','capitulo_normativo','secao_ato_normativo','subsecao_normativa','ato_normativo'):item['title']=item['text']
   items.append(item)
  expected={r['id'] for r in source['lines'] if not r['external_annex_owned']};assert set(claims)==expected
  payload={'source_id':sid,'artifact_sha256':source['artifact_sha256'],'actor_type':'automated','actor_id':ACTOR,'generated_at':stamp,'method':'exhaustive-primary-native-legal-hierarchy-v1','expected_inventory':{'articles':source['expected_articles'],'marker_counts':source['marker_counts'],'census_sha256':sha(raw),'native_lines_owned':len(expected),'native_word_occurrences_owned':sum(len(r['words']) for r in source['lines'] if not r['external_annex_owned'])},'items':items};out=ROOT/'data/manifests/uncoded'/filename;dump(out,payload);summaries.append({'source_id':sid,'path':str(out.relative_to(ROOT)),'sha256':sha(out.read_bytes()),'items':len(items),'kinds':dict(collections.Counter(i['kind'] for i in items))})
  dump(OUT/(sid+'-line-ownership.json'),{'source_id':sid,'artifact_sha256':source['artifact_sha256'],'census_sha256':sha(raw),'owners':claims,'unowned_native_lines':[],'duplicate_owned_native_lines':[]})
  if sid=='br-ifa-parametros-2025':
   old_path=ROOT/'data/manifests/uncoded/br-ifa-2025-annex.json';original=json.loads(old_path.read_text());assert original['artifact_sha256']==source['artifact_sha256'];labels=annex_labels(source,original,stamp);wrapper={**payload,'method':'exhaustive-primary-native-legal-hierarchy-v1+unchanged-ifa-annex-v1','preserved_annex':{'path':str(old_path.relative_to(ROOT)),'sha256':sha(old_path.read_bytes()),'items':len(original['items']),'policy':'All58 records, keys, parents, texts, positions and evidence included unchanged. Additional52 literal labels retain physical numbering and explicit capacity headings without changing the learning records.','additional_literal_label_nodes':len(labels)},'items':payload['items']+original['items']+labels};assert len({i['key'] for i in wrapper['items']})==len(wrapper['items']);wrapper_path=ROOT/'data/manifests/uncoded/br-ifa-2025-normative-with-annex.json';dump(wrapper_path,wrapper);summaries[-1]['source_wrapper_path']=str(wrapper_path.relative_to(ROOT));summaries[-1]['source_wrapper_sha256']=sha(wrapper_path.read_bytes())
 dump(OUT/'structure-build.json',{'actor_type':'automated','generated_at':stamp,'census_sha256':sha(raw),'sources':summaries,'source_manifest_modified':False,'publication_modified':False,'human_pedagogical_review_claimed':False});print(json.dumps(summaries,ensure_ascii=False))
def group_pages(rows):
 result=[]
 for row in rows:
  if not result or result[-1][0]!=row['page']:result.append((row['page'],[]))
  result[-1][1].append(row)
 return result
def annex_labels(source,original,stamp):
 rows=[r for r in source['lines'] if r['external_annex_owned']];by_box={(r['page'],tuple(w['bbox'])):(r,w) for r in rows for w in r['words']};claimed=set();labels=[]
 for item in original['items']:
  for e in item['evidence']:
   for b in e['regions']:
    key=(e['page'],tuple(b));assert key in by_box and key not in claimed;claimed.add(key)
 missing=set(by_box)-claimed
 def append(parent,row,words,suffix):
  key='normative-literal-label-'+suffix+'-'+parent;excerpt=' '.join(w['word'] for w in words);bounds=union([w['bbox'] for w in words]);proof={'source_id':source['source_id'],'page':row['page'],'printed_page':None,'section':key,'locator':f'ifa-2025:literal-label:{key}','excerpt':excerpt,'bbox':bounds,'regions':[w['bbox'] for w in words],'method':'pymupdf-native-legal-label-v1'};labels.append({'source_id':source['source_id'],'artifact_sha256':source['artifact_sha256'],'key':key,'parent_key':parent,'code':None,'kind':'rotulo_documental','page':row['page'],'text':excerpt,'locator':proof['locator'],'positions':[],'evidence':[proof],'actor_type':'automated','actor_id':ACTOR,'source_context':{'documentary_role':'literal_number_or_capacity_label_not_additional_learning','native_word_ids':[f'p{row["page"]}:w{w["index"]}' for w in words],'corresponding_existing_item_key':parent,'existing_annex_record_unchanged':True}})
  for w in words:assert (row['page'],tuple(w['bbox'])) in missing;missing.remove((row['page'],tuple(w['bbox'])))
 for item in original['items']:
  first=item['evidence'][0];row,_=by_box[(first['page'],tuple(first['regions'][0]))]
  if item.get('source_number') is not None:
   candidates=[w for w in row['words'] if (row['page'],tuple(w['bbox'])) in missing];assert len(candidates)==1 and candidates[0]['word']==str(item['source_number'])+'.';append(item['key'],row,candidates,'number')
  if item['kind']=='conjunto_capacidades_demonstradas':
   previous=rows[rows.index(row)-1];assert previous['text']=='Demonstrando a capacidade de:';append(item['key'],previous,previous['words'],'capacity-heading')
 assert not missing and len(labels)==52
 return labels
if __name__=='__main__':
 if sys.argv[1:] == ['census']:census()
 elif sys.argv[1:] == ['build']:build()
 else:raise SystemExit('usage: structure.py census|build')
