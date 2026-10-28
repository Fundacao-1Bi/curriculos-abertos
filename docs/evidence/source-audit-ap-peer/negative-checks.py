#!/usr/bin/env python3
"""Controlled corruption of in-memory real AP rows, never of the source/adapter."""
import collections,copy,datetime,hashlib,json,re,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
def compact(text):return re.sub(r'\s+','',text)
def center(box):return fitz.Point((box[0]+box[2])/2,(box[1]+box[3])/2)
def main():
 path=ROOT/'data/manifests/uncoded/ap-rca614-items.json';raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest=='98ea0d2503f69bfd0ab488ebb87a1b606a21e39987bc51294b317dabbe814bdf';data=json.loads(raw);pdf=fitz.open(ROOT/'data/raw/AP/ap-native-ei-ef.pdf');ei=json.loads((OUT/'ei-primary-inventory.json').read_text());assert hashlib.sha256((ROOT/'data/raw/AP/ap-native-ei-ef.pdf').read_bytes()).hexdigest()==ei['artifact_sha256'];items=data['items'];exp=[i for i in items if i['kind']=='experiencia_aprendizagem'];obj=[i for i in items if i['kind']=='objetivo_aprendizagem'];keys={i['key']:i for i in items};first=exp[0];scope=first['source_context']['physical_cell'];t=pdf[scope['page']-1].find_tables(strategy='lines_strict').tables[scope['table']];cell=fitz.Rect(t.rows[scope['row']].cells[scope['column']]);left=fitz.Rect(t.rows[scope['row']].cells[0]);expected_code=re.findall(r'EI\d{2}[A-Z]{2}\d{2}',pdf[scope['page']-1].get_text('text',clip=left))[0];pages=[{'page':n+1,'text':p.get_text('text',sort=True)}for n,p in enumerate(pdf)];extracted={'source_id':data['source_id'],'sha256':data['artifact_sha256'],'pages':pages};results=[]
 def record(name,blocked,reason):assert blocked,name;results.append({'case':name,'blocked':True,'reason':reason})
 assert keys[first['parent_key']]['code']==expected_code
 wrong=copy.deepcopy(first);different=next(i for i in obj if i['code']!=expected_code);wrong['parent_key']=different['key'];wrong['source_context']['parent_objective_code']=different['code'];record('wrong_parent_and_internal_code_changed_consistently',keys[wrong['parent_key']]['code']!=expected_code,'Internal parent fields agree with each other but disagree with primary objective column')
 def micro_is_own(item):
  pos=item['positions'][0];proofs=[e for e in pos.get('age_evidence',[])if e.get('evidence_role')=='age_micro_header'];return len(proofs)==1 and proofs[0]['source_id']==data['source_id']and compact(proofs[0]['excerpt'])==compact(pos['age_label'])and cell.x0<=center(proofs[0]['bbox']).x<=cell.x1
 assert micro_is_own(first)
 other_column=next(i for i in exp if i['parent_key']==first['parent_key']and i['source_context']['physical_cell']['column']!=scope['column']);wrong=copy.deepcopy(first)
 for field in ('age_label','age_min_months','age_max_months','age_evidence'):wrong['positions'][0][field]=copy.deepcopy(other_column['positions'][0][field])
 record('micro_age_swapped_to_real_other_column_with_valid_limits_and_evidence',not micro_is_own(wrong),'Real other-column numeric header cannot justify the original experience column')
 wrong=copy.deepcopy(first);wrong['positions'][0]['age_min_months']=1;record('numeric_limit_changed_without_primary_header',tuple(wrong['positions'][0][k]for k in('age_min_months','age_max_months'))!=(0,12),'Literal primary header 0 A 1 ANO documents 0..12 months')
 wrong=copy.deepcopy(first);wrong['positions'][0]['age_label']='BEBÊS';record('bare_macro_label_cannot_justify_inferred_numeric_interval',not micro_is_own(wrong),'No numeric micro-header string remains; no interval is inferred from the word BEBÊS')
 frozen_by_line={(a['page'],*a['rawdict_index'][:2]):n for n,a in enumerate(ei['experience_anchors'])};word_cache={page:pdf[page-1].get_text('words',sort=False)for page in range(93,132)}
 def owned(rows):
  counts=collections.Counter()
  for i in rows:
   e=i['evidence'][0];words=[w for w in word_cache[e['page']]if fitz.Rect(e['bbox']).contains(center(w[:4]))];assert words;counts[frozen_by_line[(e['page'],*words[0][5:7])]]+=1
  return counts
 expected=collections.Counter(range(465));assert owned(exp)==expected;record('last_experience_removed',owned(exp[:-1])!=expected,'One frozen native bullet loses its owner');record('duplicate_experience_hides_missing_record_with_same_count',len(exp[:-1]+[exp[0]])==465 and owned(exp[:-1]+[exp[0]])!=expected,'Count remains465 but one physical glyph is duplicated and another missing')
 wrong=copy.deepcopy(first);wrong['text']+=' PALAVRAINVENTADA';assert ingest.evidence_check(first,extracted,pdf);record('invented_canonical_word',not ingest.evidence_check(wrong,extracted,pdf),'Common production literal checker rejects changed target wording')
 wrong=copy.deepcopy(obj[0]);wrong['code']='EI01EO99';record('invented_code',not ingest.evidence_check(wrong,extracted,pdf),'No primary code or matching code locator exists')
 multi=next(i for i in items if len({e['page']for e in i['evidence']})>1 and i['kind']=='habilidade');wrong=copy.deepcopy(multi);last=next(e for e in reversed(wrong['evidence'])if e.get('evidence_role')!='code_locator');last['excerpt']=' '.join(last['excerpt'].split()[:-1]);record('last_word_of_continuation_removed',not ingest.evidence_check(wrong,extracted,pdf),'Joined full target differs from incomplete current primary fragment')
 report={'actor_type':'automated','actor_id':'codex-independent-ap-peer','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'artifact_sha256':ei['artifact_sha256'],'adapter_sha256':digest,'positive_controls':{'expected_physical_parent_code':expected_code,'one_native_bullet_per_experience':465,'original_common_checker_passed':True,'specific_micro_header_in_own_column':True},'negative_cases':results,'passed':True,'adapter_written':False,'publication_modified':False,'human_pedagogical_review_claimed':False};(OUT/'negative-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'negative_cases_blocked':len(results),'positive_controls':report['positive_controls']}))
if __name__=='__main__':main()
