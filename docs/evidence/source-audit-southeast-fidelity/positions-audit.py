#!/usr/bin/env python3
"""Independent ES explicit-caption/component proof; readonly primary and candidates.

Only positions-* evidence files are written. No code, source, cache, manifest,
learning wording or live publication is modified.
"""
from __future__ import annotations
import collections,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import pymupdf as fitz
from geometry import normalize_native_page

COMPONENTS=['Língua Portuguesa','Língua Inglesa','Educação Física','Ensino Religioso','Matemática','Geografia','História','Filosofia','Sociologia','Química','Física','Biologia','Ciências','Arte','Artes']
AREAS=['Linguagens e suas Tecnologias','Ciências da Natureza e suas Tecnologias','Ciências Humanas e Sociais Aplicadas']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ws(value):return' '.join(value.split())
def norm(value):return' '.join(unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().casefold().split())
def write(name,value):
 p=OUT/name;tmp=p.with_name(p.stem+'.tmp'+p.suffix);tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(p);return sha(p)
def main():
 prior=json.loads((OUT/'position-inventory.json').read_text());physical=json.loads((OUT/'filtered-physical-objectives-inventory.json').read_text());manifest={s['id']:s for s in json.loads((ROOT/'data/manifests/bncc-southeast.json').read_text())};pages=collections.defaultdict(list)
 for item in physical['items']:pages[item['source_id'],item['page']].append(item)
 docs={};headings={};caption_checks=[];contexts=[];conflicts=[]
 for sid in sorted({p['source_id']for p in prior['page_evidence']}):
  source=manifest[sid];path=ROOT/source['local_path'];assert sha(path)==source['sha256'];D=fitz.open(path);docs[sid]=D;headings[sid]=[]
  for pn,p in enumerate(D,1):
   normalize_native_page(p)
   for block in p.get_text('dict')['blocks']:
    for line in block.get('lines',[]):
     text=''.join(span['text']for span in line['spans']).strip();size=max([span['size']for span in line['spans']]or[0]);component=next((c for c in COMPONENTS if norm(text)==norm(c)),None)
     if component and size>=13:
      headings[sid].append({'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'bbox':list(line['bbox']),'excerpt':text,'component':component if component!='Artes'else'Arte','source_component_label':text,'font_sizes':[span['size']for span in line['spans']],'method':'Exact printed standalone component heading, font>=13pt; not inferred from skill code.'})
  print('component-headings',sid,len(headings[sid]),flush=True)
 for original in prior['page_evidence']:
  sid=original['source_id'];pn=original['page'];source=manifest[sid];p=docs[sid][pn-1];normalize_native_page(p);box=original['caption_bbox'];caption=p.get_text('text',clip=fitz.Rect(box),sort=True).strip();tight=[]
  for block in p.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    text=''.join(s['text']for s in line['spans']).strip()
    if text and line['bbox'][1]<box[3]and line['bbox'][3]<=box[3]+1:tight.append({'text':text,'bbox':list(line['bbox'])})
  proofbox=[min(l['bbox'][0]for l in tight),min(l['bbox'][1]for l in tight),max(l['bbox'][2]for l in tight),max(l['bbox'][3]for l in tight)]if tight else box
  exact=ws(caption)==ws(original['caption_text']);assert exact
  match=re.search(r'([1-9])\s*[ºª°o]?\s*(Ano|S[eé]rie)',caption,re.I);year=int(match.group(1))if match else None;stage='EF'if re.search(r'Ensino\s+Fundamental',caption,re.I)else'EM'if re.search(r'Ensino\s+M[eé]dio',caption,re.I)else None
  # Most specific named school subject precedes generic Ciências in a caption.
  specific=[c for c in COMPONENTS if c!='Ciências']+['Ciências'];direct=next((c for c in specific if re.search(r'(?<!\w)'+re.escape(norm(c))+r'(?!\w)',norm(caption))),None)
  if direct:
   component='Arte'if direct=='Artes'else direct;component_proof={'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'bbox':proofbox,'excerpt':caption,'component':component,'source_component_label':direct,'method':'Component named in the same actual primary-page caption.'}
  else:
   candidates=[h for h in headings[sid]if h['page']<pn or h['page']==pn and h['bbox'][3]<=box[3]+1]
   component_proof=max(candidates,key=lambda h:(h['page'],h['bbox'][1]))if candidates else None;component=component_proof['component']if component_proof else None
  area=next((a for a in AREAS if norm(a)in norm(caption)),None)
  evidence=[{'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'bbox':proofbox,'excerpt':caption,'section':'Cabeçalho curricular explícito acima da tabela','method':'Independent primary native caption re-read; exact whitespace-only agreement with prior physical inventory.'}]
  if component_proof and component_proof['page']!=pn:evidence.append({'source_id':sid,'artifact_sha256':source['sha256'],**{k:component_proof[k]for k in['page','bbox','excerpt','method']},'section':'Componente explícito no banner/capa do capítulo, mantido até o próximo título de componente.'})
  conflict=(source['sha256']=='04cf2e73e969a862e1fb8f7e439844d6a7914c2e4a6501a4d32480b29377d149' and pn==132 and year==1)
  context={'source_id':sid,'artifact_sha256':source['sha256'],'id':f'primary-position-page-{pn}','actor_type':'automated','actor_id':'pr_adapter:independent-es-primary-position-proof','page':pn,'stage':stage,'component':component,'area':area,'years':None if conflict or year is None else[year],'year_label':None if conflict or year is None else f'{year}ª Série'if stage=='EM'else f'{year}º ano','age_group':None,'period':None,'evidence':evidence,'source_component_label':component_proof.get('source_component_label')if component_proof else None,'source_context':{'literal_page_caption':caption,'caption_bbox':proofbox,'component_evidence':component_proof,'position_scope':'Only primary code/text cells on this exact source page; no code convention used to choose local grade.'},'physical_objectives':len(pages[sid,pn]),'documentary_conflict':conflict}
  if conflict:
   adjacent=[q for q in prior['page_evidence']if q['source_id']==sid and q['page']in(130,134)];codes=[i['original_code_cell_text']for i in pages[sid,pn]]
   context['source_context'].update({'source_caption_year':year,'source_code_year_candidates':[6],'source_code_year_candidate_basis':'Code prefix EF06 is retained only as a candidate convention, not chosen as local year.','source_codes':codes,'adjacent_page_captions':adjacent,'conflict_note':'The actual PDF caption prints1º Ano inside the anos finais Mathematics chapter; adjacent source captions and EF06 identifiers indicate6. Neither year is selected automatically.','automated_visual_inspection':{'path':f'var/private-evidence/source-audit-southeast-fidelity/renders/{source["sha256"]}/page-{pn:04d}.png','actor_type':'automated','method':'Model visually inspected actual primary PDF raster;1º caption visible, not extraction substitution.','human_review':False}})
   for original_item in pages[sid,pn]:context['evidence'].append({'source_id':sid,'artifact_sha256':source['sha256'],'page':pn,'bbox':original_item['code_bbox'],'excerpt':original_item['original_code_cell_text'],'section':'Identificador literal na coluna própria; somente candidato de convenção de ano, sem escolha automática.','method':'Primary physical code cell, independently paired before candidate comparison.'})
   for adjacent_caption in adjacent:context['evidence'].append({'source_id':sid,'artifact_sha256':source['sha256'],'page':adjacent_caption['page'],'bbox':adjacent_caption['caption_bbox'],'excerpt':adjacent_caption['caption_text'],'section':'Cabeçalho adjacente do capítulo, preservado como evidência do conflito.','method':'Primary adjacent page caption, also independently re-read in the complete677-page caption audit.'})
   context['evidence'][0]['position_conflict']={'source_caption_year':year,'adjacent_caption_years':[q['explicit_year_or_series']for q in adjacent],'source_code_year_candidates':[6],'resolution':'No year selected automatically; source ambiguity preserved as null.'}
   context['position_note']='Conflito documental preservado: a fonte imprime1º Ano, mas o capítulo/páginas adjacentes e códigos EF06 indicam6; não há correção silenciosa.'
   context['position_unknown_reason']='Conflito interno da fonte entre cabeçalho local impresso1º Ano, capítulo/páginas vizinhas do6º ano e identificadores EF06; ano mantido nulo até reconciliação documental.';conflicts.append(context)
  contexts.append(context);caption_checks.append({'source_id':sid,'page':pn,'caption_bbox':proofbox,'caption_excerpt':caption,'exact_caption_reverified':exact,'explicit_stage':stage,'explicit_year':year,'component':component,'component_proof':component_proof,'proposed_years':context['years'],'documentary_conflict':conflict,'objective_count':len(pages[sid,pn])})
 write('positions-primary-contexts.json',{'input_physical_inventory_sha256':sha(OUT/'filtered-physical-objectives-inventory.json'),'input_position_inventory_sha256':sha(OUT/'position-inventory.json'),'contexts':contexts,'caption_checks':caption_checks,'conflicts':conflicts})
 # Compare only physical independently expected leaves; finalized files may arrive while running.
 current={};candidate_files=[]
 for group in['ef','em']:
  report_path=OUT/f'probe-{group}-summary.json';summary=json.loads(report_path.read_text())
  for source in summary['sources']:
   relative=source.get('finalized_path')
   if not relative:continue
   fp=ROOT/relative
   if not fp.exists():continue
   items=json.loads(fp.read_text());candidate_files.append({'source_id':source['source_id'],'path':relative,'sha256':sha(fp),'parser_fingerprint':summary.get('parser_fingerprint')});current[source['source_id']]=items
 bycontext={(c['source_id'],c['page']):c for c in contexts};checks=[]
 for expected in physical['items']:
  sid=expected['source_id'];pn=expected['page'];context=bycontext[sid,pn];candidates=[i for i in current.get(sid,[])if i.get('code')and ''.join(i['code'].split())==expected['code']and any(e.get('page')==pn and e.get('locator')==expected['locator']for e in i.get('evidence',[]))]
  failures=[]
  if sid not in current:result='pending_finalized_source'
  elif not candidates:result='missing_expected_leaf'
  else:
   for i in candidates:
    positions=i.get('positions',[])
    if not any(p.get('stage')==context['stage']for p in positions):failures.append('explicit_stage_missing')
    if not any(p.get('component')==context['component']for p in positions):failures.append('explicit_component_missing_or_different')
    if context['documentary_conflict']:
     if any(p.get('years')for p in positions):failures.append('internal_source_year_conflict_not_preserved_as_unknown')
    elif not any(p.get('years')==context['years']for p in positions):failures.append('explicit_local_year_missing_or_different')
   result='positions_match_primary_proposal'if not failures else'position_difference'
  checks.append({'source_id':sid,'page':pn,'code':expected['code'],'original_code_cell_text':expected['original_code_cell_text'],'locator':expected['locator'],'expected_stage':context['stage'],'expected_component':context['component'],'expected_years':context['years'],'documentary_conflict':context['documentary_conflict'],'result':result,'issues':sorted(set(failures)),'candidate_ids':[i['id']for i in candidates],'actual_positions':[i.get('positions',[])for i in candidates]})
 grouped=collections.defaultdict(list)
 for c in contexts:grouped[c['evidence'][0]['source_id']].append(c)
 proposal={'actor_type':'automated','human_review':False,'status':'reviewable_metadata_proposal_only_not_integrated','input_physical_inventory_sha256':sha(OUT/'filtered-physical-objectives-inventory.json'),'input_position_inventory_sha256':sha(OUT/'position-inventory.json'),'method':'Explicit stage/year from the actual caption; school subject from the same caption or the latest exact standalone component banner/capa in this source. Conflicting source year is null. No learning text, codes, IDs, evidence or source bytes changed.','scope':'2513 independently inventoried physical code/text cells,677pages,11sources; does not cover prefixed-only matrices, introductory prose or uncoded competencies.','sources':[{'source_id':sid,'artifact_sha256':manifest[sid]['sha256'],'position_contexts':values}for sid,values in grouped.items()]}
 write('positions-metadata-proposal.json',proposal)
 report={'actor_type':'automated','human_review':False,'method':proposal['method'],'physical_objectives':len(physical['items']),'pages':len(contexts),'sources':len(grouped),'all_captions_exactly_reverified':all(c['exact_caption_reverified']for c in caption_checks),'pages_without_explicit_stage':[c for c in caption_checks if not c['explicit_stage']],'pages_without_explicit_grade':[c for c in caption_checks if not c['explicit_year']],'pages_without_documented_component':[c for c in caption_checks if not c['component']],'source_internal_year_conflicts':conflicts,'candidate_files':candidate_files,'comparison_counts':dict(collections.Counter(c['result']for c in checks)),'issue_counts':dict(collections.Counter(issue for c in checks for issue in c['issues'])),'caption_proofs':caption_checks,'checks':checks,'proposal_path':'docs/evidence/source-audit-southeast-fidelity/positions-metadata-proposal.json','proposal_sha256':sha(OUT/'positions-metadata-proposal.json'),'limitations':['Position proof is automated documentary extraction, not human pedagogical review.','The4 objectives on vol06p132 keep null local year due the printed1º/neighboring6º/codeEF06 conflict.','Any source lacking a finalized candidate remains pending in this comparison; rerun positions-audit.py after final snapshots.','Source-header conflict policy is explicit and does not silently correct the official text.']}
 write('positions-audit-report.json',report)
 print(json.dumps({k:report[k]for k in['physical_objectives','pages','sources','all_captions_exactly_reverified','comparison_counts','issue_counts']},ensure_ascii=False));print('missing_components',len(report['pages_without_documented_component']),'conflicts',len(conflicts),'proposal_sha256',report['proposal_sha256'])
if __name__=='__main__':main()
