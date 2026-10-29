import pathlib,json,sys,collections,datetime
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));sys.path.insert(0,str(O))
import ingest,al_document_roles_proposal as role
s=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==role.SOURCE)
ex=json.loads((R/'data/extracted'/f'{s["sha256"]}-{ingest.EXTRACTION_REVISION}.json').read_text());d=f.open(R/s['local_path']);events=json.loads((O/'al-desdp-header-groups.json').read_text())['events'];role.CACHE[(id(d),s['sha256'])]=events;stats=collections.Counter();pages=[]
for pn,p in enumerate(d,1):
 tables=p.find_tables().tables;old=[i for i in ex['items'] if i['evidence'][0]['page']==pn];new,detail=role.rewrite_page(s,pn,p,tables,old,ingest.CODE_ANY,ingest.make_item,ingest.clean_text)
 refs=[i for i in new if i.get('document_specific_adapter')=='al-desdp-document-roles-v1'];fail=[{'code':i['code'],'bbox':i['evidence'][0].get('bbox'),'locator':i['evidence'][0].get('locator')} for i in refs if not ingest.evidence_check(i,ex,d)]
 stats.update(pages=1,removed_old_candidates=len(detail.get('removed_candidates',[])),references=len(refs),reference_literal_failures=len(fail),primary_anchors=detail.get('primary_anchors',0),unknown_anchors=detail.get('unknown_anchors',0))
 if refs or detail.get('primary_anchors') or fail:pages.append({'page':pn,'removed_candidates':len(detail.get('removed_candidates',[])),'reference_records':len(refs),'primary_anchors':detail.get('primary_anchors',0),'unknown_anchors':detail.get('unknown_anchors',0),'reference_literal_failures':fail})
out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':s['id'],'source_sha256':s['sha256'],'scope':'Every physical page; exact printed DesDP/Habilidades headings and matched physical x-edges only. Existing caches not written. Full local DesDP text remains in each source_context; uncoded DesDP semantic hierarchy not claimed.','header_groups':len(events),'summary':dict(stats),'pages':pages,'limits':['Unknown roles retained, not discarded.','Role census is not complete documentary reconciliation; uncoded DesDP nodes remain required internal work.','Primary old-cache wording not rewritten by this role helper; current glyph-mode reprocessing remains required.']};(O/'al-desdp-full-role-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['summary']))
