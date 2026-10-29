#!/usr/bin/env python3
"""Replay the complete existing source cache with the proposed narrow authority in memory."""
import copy,hashlib,json,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'))
import ingest
from runtime import parser_fingerprint
SID='rj-em-integral-tecnico';S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']==SID);SHA=S['sha256'];cache=ROOT/f'data/extracted/{SHA}-page-cell-v1.5.0.json';raw=cache.read_bytes();pin=hashlib.sha256(raw).hexdigest();C=json.loads(raw);before=parser_fingerprint();baseline=ingest.finalize_items(copy.deepcopy(C['items']),[S]);authority=copy.deepcopy(S.get('adapter_authority')or{});authority.setdefault('coded_learning_ranges',[]).append([669,669]);source=copy.deepcopy(S);source['adapter_authority']=authority;source['uncoded_items_path']='data/manifests/uncoded/rj-integral-p669-coded-body-v1-items.json';extract={'source_id':SID,'sha256':SHA,'pages':[]}
with fitz.open(ROOT/S['local_path'])as d:
 for pn in [669,670]:extract['pages'].append({'page':pn,'text':d[pn-1].get_text('text',sort=False)})
errors=[];added=ingest.source_uncoded_items([source],{SID:extract},errors);assert not errors and len(added)==4
result=ingest.finalize_items(copy.deepcopy(C['items'])+added,[source]);byid={i['id']:i for i in result};old_page669=[i for i in baseline if i.get('code')and i['evidence'][0]['page']==669];old_ids={i['id']for i in old_page669};unaffected=[i for i in baseline if i['id']not in old_ids];changed_unaffected=[i['id']for i in unaffected if byid.get(i['id'])!=i];checks=[]
def check(name,ok):checks.append({'name':name,'passed':bool(ok)})
check('ThreePriorIDsPreserved',len(old_ids)==3 and old_ids<=set(byid))
check('AllOtherFinalRecordsExactlyPreserved',not changed_unaffected)
check('OnlyOneNewMissingDefinitionAdded',len(result)==len(baseline)+1)
check('NoDuplicateFinalIDs',len(result)==len(byid))
check('PriorCodesKindsPositionsParentsUnchanged',all(all(byid[i['id']].get(k)==i.get(k)for k in ('code','kind','positions','parent_id'))for i in old_page669))
check('TwoNeighboringCodedTextsExactlyPreserved',all(byid[i['id']]['text']==i['text']for i in old_page669 if i['code']!='EM13LGG204'))
check('OnlyTwoForeignWordFragmentsRemoved',all(byid[i['id']]['text']==i['text'].replace('democracia T','democracia').removesuffix(' C')for i in old_page669 if i['code']=='EM13LGG204'))
check('Code304RecoveredWithContinuation670',any(i['code']=='EM13LGG304'and i['evidence'][0]['page']==669 and any(e['page']==670 for e in i['evidence'])for i in result))
check('NoAuthority668',not ingest.authority_covers(authority,'coded_learning',668))
check('NoAuthority670',not ingest.authority_covers(authority,'coded_learning',670))
check('NoGenericContextSuppression',not ingest.authority_covers(authority,'uncoded_page_sections',669))
check('NoReferenceDemotion',not ingest.authority_covers(authority,'generic_coded_reference',669))
other=copy.deepcopy(next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']=='sp-curriculo-em-isbn'));check('OtherSourceUnmodified',not ingest.authority_covers(other.get('adapter_authority')or{},'coded_learning',669))
after=parser_fingerprint();check('ParserUnchanged',before==after);check('OldCacheUnchanged',hashlib.sha256(cache.read_bytes()).hexdigest()==pin);assert all(c['passed']for c in checks),checks
report={'source_id':SID,'source_sha256':SHA,'old_cache_sha256':pin,'previous_records':len(baseline),'new_records':len(result),'unaffected_records':len(unaffected),'unaffected_changed_ids':changed_unaffected,'old_page669_ids':sorted(old_ids),'new_definition_ids':[i['id']for i in result if i['id']not in {x['id']for x in baseline}],'checks':checks,'passed':True,'proposed_authority':authority,'parser_fingerprint':before,'source_metadata_only_in_memory':True,'source_manifest_edited':False,'production_cache_modified':False,'source_ready':False};(OUT/'rj-integral-v2-scope-replay-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:report[k]for k in ('previous_records','new_records','unaffected_records','passed')},ensure_ascii=False))
