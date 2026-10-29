#!/usr/bin/env python3
"""DATA-ONLY RJ EM native paragraph bodies; no MF/cache/core mutation."""
from pathlib import Path
import json,re,sys,hashlib,copy,collections,importlib.util
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf
from geometry import normalize_native_page
from native_glyphs import NativeGlyphText
from ingest import clean_text,finalize_items,source_uncoded_items,evidence_check,make_item
from validate_artifact import validators
from prepare import prepare
B=prepare();S=B['source'];D=pymupdf.open(ROOT/S['local_path'])
CODE=re.compile(r'(?<![A-Z0-9])EM[A-Z0-9]+(?:\.RJ\d+)?(?![A-Z0-9])')
HEADER=re.compile(r'(?<![\w])(?:Habilidades?(?:\s+[^:\n]{1,70})?\s*:|Objetos?\s+de\s+conhecimento\s*:|Campos?\s+de\s+Atua[çc][ãa]o\s+Social\s*:|Compet[êe]ncias?\s+espec[íi]ficas?\s*\d*|Unidade\s+tem[áa]tica\s*:)',re.I)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def physical_rows(p):
 groups=[]
 for word in sorted(p.get_text('words'),key=lambda w:((w[1]+w[3])/2,w[0])):
  cy=(word[1]+word[3])/2;g=next((r for r in reversed(groups[-3:]) if abs(r['cy']-cy)<2),None)
  if g is None:g={'cy':cy,'words':[]};groups.append(g)
  g['words'].append(word)
 out=[];offset=0
 for g in groups:
  words=sorted(g['words'],key=lambda w:w[0]);text='';tokens=[]
  for w in words:
   if text:text+=' '
   start=offset+len(text);text+=w[4];tokens.append({'word':w,'start':start,'end':offset+len(text)})
  out.append({'text':text,'start':offset,'end':offset+len(text),'tokens':tokens});offset+=len(text)+1
 return out

def fullpage(p):
 rows=physical_rows(p);return rows,'\n'.join(r['text'] for r in rows)

def extract(p,pn):
 norm=normalize_native_page(p);rows,text=fullpage(p);glyph=NativeGlyphText(p);headers=list(HEADER.finditer(text));events=[];issues=[]
 for ci,m in enumerate(CODE.finditer(text)):
  # Literal code syntax broad enough for printed EMLGG303/EM1313CNT305.RJ02.
  if not re.search(r'\d',m.group()):continue
  prior=[h for h in headers if h.end()<=m.start()];heading=prior[-1] if prior else None
  between=text[heading.end():m.start()] if heading else ''
  labelled=heading and not between.strip(' \n\t(')
  role='habilidade' if labelled and heading.group().casefold().startswith('habilidad') else 'referencia_no_documento'
  if not labelled:
   issues.append({'page':pn,'code':m.group(),'issue':'code_not_immediately_after_explicit_heading','prefix':text[max(0,m.start()-120):m.start()]})
   continue
  end=min([h.start() for h in headers if h.start()>=m.end()]+[len(text)])
  # Every next native identifier is also a hard end; no cached-only closure.
  after=[x.start() for x in CODE.finditer(text) if x.start()>m.start()]
  if after:end=min(end,min(after))
  raw=text[m.end():end];leading=re.match(r'^[\s()\-–—:;.]*',raw).end();start=m.end()+leading
  raw=text[start:end].rstrip();end=start+len(raw)
  if not raw:issues.append({'page':pn,'code':m.group(),'issue':'empty_body'});continue
  fragments=[];errors=[]
  for row in rows:
   if row['end']<=start or row['start']>=end:continue
   tokens=[t for t in row['tokens'] if t['end']>start and t['start']<end]
   if not tokens:continue
   box=[min(t['word'][0] for t in tokens)-.05,min(t['word'][1] for t in tokens)-.05,max(t['word'][2] for t in tokens)+.05,max(t['word'][3] for t in tokens)+.05]
   independent=text[max(row['start'],start):min(row['end'],end)]
   native=glyph.text(box)
   # Boundary words can contain literal code/parenthesis/dash. Strip only
   # exactly the source segment outside this fragment, never body characters.
   first=tokens[0];last=tokens[-1]
   if start>first['start']:
    prefix=text[first['start']:start]
    native=native[len(prefix):] if native.startswith(prefix) else native
   if end<last['end']:
    suffix=text[end:last['end']]
    native=native[:-len(suffix)] if suffix and native.endswith(suffix) else native
   if clean_text(native)!=clean_text(independent):errors.append({'bbox':box,'words':independent,'glyphs':native})
   fragments.append({'source_id':S['id'],'page':pn,'printed_page':None,'section':heading.group().strip(),'excerpt':clean_text(independent),'locator':f'native-paragraph:{ci}/line:{len(fragments)}','bbox':box,'method':'pymupdf-native-glyph-cluster-v1','artifact_sha256':S['sha256'],'page_normalization':norm})
  body=clean_text(raw)
  if clean_text(' '.join(f['excerpt'] for f in fragments))!=body:errors.append({'issue':'fragment_join_mismatch'})
  events.append({'page':pn,'code':m.group(),'kind':role,'text':body,'heading':heading.group().strip(),'heading_bbox':p.search_for(heading.group())[:1],'anchor_y':next(t['word'][1] for r in rows for t in r['tokens'] if t['start']<=m.start()<t['end']),'source_order':ci,'evidence':fragments,'proof_errors':errors,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'boundary_next_header':text[end:end+100]})
 return events,issues,text,norm

def ranges(ns):
 result=[]
 for n in sorted(ns):
  if result and n==result[-1][1]+1:result[-1][1]=n
  else:result.append([n,n])
 return result

def main():
 assert digest(ROOT/S['local_path'])==S['sha256']
 baseline=finalize_items(copy.deepcopy(B['items']),[S]);old_by_page=collections.defaultdict(list)
 for old in baseline:old_by_page[old['evidence'][0]['page']].append(old)
 records=[];proofs=[];blocked=[];superseded=[];new=[];pages_text=[];denom=[];unchanged=0
 for pn in range(1,len(D)+1):
  events,issues,text,norm=extract(D[pn-1],pn);pages_text.append({'page':pn,'text':text})
  if not events and not old_by_page[pn]:continue
  denom.extend({k:v for k,v in e.items() if k in ('page','code','kind','heading','source_order','body_sha256')} for e in events)
  failures=[{'code':e['code'],'errors':e['proof_errors']} for e in events if e['proof_errors']]
  if issues or failures:blocked.append({'page':pn,'issues':issues,'proof_failures':failures});continue
  remaining=list(events);assignments=[];unused_old=list(old_by_page[pn])
  # Global minimum geometric pairing within the same literal code, before
  # inspecting leftover extractor duplicates. Never consume the real anchor
  # for an earlier phantom record whose bbox begins on the national code.
  pairs=[]
  for old in unused_old:
   box=old['evidence'][0].get('bbox');y=box[1]+2 if box else 0
   for event in remaining:
    if event['code']==old['code']:pairs.append((abs(event['anchor_y']-y),old,event))
  for distance,old,event in sorted(pairs,key=lambda pair:pair[0]):
   if old in unused_old and event in remaining:
    assignments.append((event,old));unused_old.remove(old);remaining.remove(event)
  page_superseded=[]
  for old in unused_old:
   matched=[(e,o) for e,o in assignments if e['code']==old['code']]
   if not matched:
    failures.append({'old_id':old['id'],'code':old['code'],'error':'old_code_not_found_literal'});continue
   event,correct=min(matched,key=lambda pair:abs(pair[0]['anchor_y']-(old['evidence'][0]['bbox'][1]+2)))
   old_y=old['evidence'][0]['bbox'][1]+2
   if abs(old_y-event['anchor_y'])<5:
    failures.append({'old_id':old['id'],'error':'duplicate_at_same_primary_anchor_requires_manual_resolution'});continue
   page_superseded.append({'page':pn,'code':old['code'],'invalid_duplicate_id':old['id'],'superseded_by_id':correct['id'],'invalid_locator':old['evidence'][0]['locator'],'retained_locator':correct['evidence'][0]['locator'],'invalid_anchor_y':old_y,'literal_code_anchor_y':event['anchor_y'],'old_text':old['text'],'old_evidence':old['evidence'],'method':'One printed native identifier; extra cache record originated at another identifier anchor. Retain the actual-code-anchor occurrence and supersede only the phantom technical duplicate.'})
  if failures:blocked.append({'page':pn,'proof_failures':failures});continue
  superseded.extend(page_superseded)
  assignments+= [(e,None) for e in remaining]
  for event,old in sorted(assignments,key=lambda pair:pair[0]['source_order']):
   locator=old['evidence'][0]['locator'] if old else f'native-rj-em-code:{event["source_order"]}/y:{event["anchor_y"]:.2f}'
   evidence=copy.deepcopy(event['evidence']);evidence[0]['locator']=locator
   # Separate literal identifier evidence; body excerpts never include code.
   anchorboxes=D[pn-1].search_for(event['code']);anchor=min(anchorboxes,key=lambda b:abs(b.y0-event['anchor_y']))
   evidence.append({'source_id':S['id'],'page':pn,'printed_page':None,'section':'Identificador literal impresso','excerpt':event['code'],'locator':locator+'/literal-code','bbox':list(anchor),'method':'pymupdf-native-glyph-cluster-v1','evidence_role':'code_locator','artifact_sha256':S['sha256']})
   positions=copy.deepcopy(old['positions']) if old else finalize_items([make_item(S,event['code'],event['text'],pn,'native-rj-em-new-anchor',locator)],[S])[0]['positions']
   if event['kind']=='referencia_no_documento':positions=[]
   record={'source_id':S['id'],'page':pn,'locator':locator,'kind':event['kind'],'code':event['code'],'text':event['text'],'positions':positions,'evidence':evidence,'parent_id':old.get('parent_id') if old else None,'source_order':event['source_order'],'source_context':{'printed_role_label':event['heading'],'native_body_revision':'rj-em-native-paragraph-body-v1','body_character_sha256':event['body_sha256'],'technical_correction_only':True,'upstream_extraction':{'id':old['id'],'text':old['text'],'evidence':old['evidence']} if old else None}}
   if old:
    unchanged+=int(old['text']==record['text']);proofs.append({'old_id':old['id'],'page':pn,'code':event['code'],'locator':locator,'body_changed':old['text']!=record['text'],'old_text':old['text'],'new_text':record['text'],'new_text_sha256':event['body_sha256'],'native_word_vs_glyph_characters_equal':True,'printed_role':event['heading']})
   else:new.append({'page':pn,'code':event['code'],'locator':locator,'printed_role':event['heading']})
   records.append(record)
 out=ROOT/'data/manifests/uncoded/rj-coded-body-rj-em-curriculo-referencial-v1-items.json';out.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 (OUT/'native-body-proofs.json').write_text(json.dumps(proofs,ensure_ascii=False,indent=2)+'\n')
 summary={'source_id':S['id'],'source_sha256':S['sha256'],'cache_sha256':B['cache_sha256'],'actor_type':'automated','revision':'rj-em-native-paragraph-body-v1','source_pages':len(D),'native_code_denominator':len(denom),'native_role_counts':dict(collections.Counter(e['kind'] for e in denom)),'baseline_coded_records':len(baseline),'records':len(records),'unchanged_old_bodies':unchanged,'changed_old_bodies':len(proofs)-unchanged,'added_occurrences':new,'technical_duplicate_supersessions':superseded,'blocked_pages':blocked,'proposed_authority':{'coded_learning_ranges':ranges({r['page'] for r in records})},'sidecar_path':str(out.relative_to(ROOT)),'sidecar_sha256':digest(out),'denominator':denom,'not_claimed':['human_review','UF_ready','SourceWhole','official_change']}
 (OUT/'recovery-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 # Keep only native pages required by actual sidecar verification; compact text.
 # Native page text remains only in memory, never a persisted full-PDF dump.
 print(json.dumps({k:v for k,v in summary.items() if k not in ('denominator','added_occurrences','technical_duplicate_supersessions','blocked_pages')},ensure_ascii=False));print('BLOCKED',json.dumps(blocked[:8],ensure_ascii=False));print('NEW',len(new))
if __name__=='__main__':main()
