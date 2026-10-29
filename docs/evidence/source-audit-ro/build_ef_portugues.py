#!/usr/bin/env python3
"""LP full physical-cell bodies, parallel columns and literal source blocks.

Stops before adapter output if any continuation/context cell has no defensible
owner. Does not modify the manifest, cache or database.
"""
import collections
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import fitz
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
from census_ef_portugues import CODE
sha=lambda b:hashlib.sha256(b).hexdigest()
norm=lambda s:re.sub(r'\s+','',s)
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def rect_contains(outer,inner):return fitz.Rect(outer).contains(fitz.Rect(inner)+(.5,.5,-.5,-.5))

def main():
    census_path=BASE/'ef-lp-primary-cell-census.json';c=json.loads(census_path.read_text())
    assert c['primary_code_occurrences']==c['physical_code_occurrences']==394 and not c['missing_code_occurrences']and not c['extra_code_occurrences']
    source=next(s for s in json.loads((ROOT/'data/manifests/north.json').read_text())if s['id']==c['source_id']);assert sha((ROOT/source['local_path']).read_bytes())==source['sha256']==c['artifact_sha256']
    doc=fitz.open(ROOT/source['local_path']);coded=[f for f in c['all_physical_fields']if f['code_events']]
    candidates=[f for f in c['all_physical_fields']if not f['code_events']and f['bbox'][0]>=290]+c['noncode_right_column_candidates_requiring_role_review']
    kept=[]
    for f in sorted(candidates,key=lambda f:-(f['bbox'][2]-f['bbox'][0])*(f['bbox'][3]-f['bbox'][1])):
        if any(g['page']==f['page']and rect_contains(g['bbox'],f['bbox'])and norm(f['text'])in norm(g['text'])for g in coded+kept):continue
        kept.append(f)
    titles=c['source_block_titles'];annual=[]
    for f in kept:
        match=re.fullmatch(r'([1-9])º',f['text'].strip())
        if match:annual.append({'page':f['page'],'bbox':f['bbox'],'text':f['text'],'year':int(match.group(1))})
    groups=[]
    for header in sorted(annual,key=lambda h:(h['page'],h['bbox'][1],h['bbox'][0])):
        group=next((g for g in groups if g['page']==header['page']and abs(g['y']-header['bbox'][1])<3),None)
        if group:group['headers'].append(header)
        else:groups.append({'page':header['page'],'y':header['bbox'][1],'headers':[header]})
    assert groups and all(len(g['headers'])==2 for g in groups),groups
    def block_for(f):
        previous=[t for t in titles if(t['page'],t['bbox'][1])<=(f['page'],f['bbox'][1])]
        assert previous,(f['page'],'no explicit component block');return previous[-1]
    def placement(f):
        block=block_for(f);previous=[g for g in groups if(block['page'],block['bbox'][1])<(g['page'],g['y'])<(f['page'],f['bbox'][1])]
        if previous:
            group=previous[-1];headers=[h for h in group['headers']if f['bbox'][0]-2<=(h['bbox'][0]+h['bbox'][2])/2<=f['bbox'][2]+2]
            if headers:return sorted({h['year']for h in headers}),block,headers
        return block['years'],block,[]
    records=[];keys={};body_active=[];context_active=None;phase='context';proofs=[];unattached=[];markers=[]
    def evidence(key,text,f,index=1,role=None):
        e={'source_id':source['id'],'page':f['page'],'printed_page':None,'section':key,'excerpt':text,'bbox':f['bbox'],'locator':'ro-lp:'+key+':fragment-'+str(index),'method':'pymupdf-native-glyph-cluster-v1'}
        if role:e['evidence_role']=role
        return e
    def add(key,parent,kind,text,f,years=None,code=None,context=None):
        r={'source_id':source['id'],'artifact_sha256':source['sha256'],'key':key,'parent_key':parent,'kind':kind,'code':code,'text':text,'page':f['page'],'locator':'ro-lp:'+key,'positions':[{'stage':'EF','component':'Língua Portuguesa','area':'Linguagens','years':years,'year_label':' / '.join(str(y)+'º ano'for y in years)if years else None,'age_group':None,'period':None}],'evidence':[evidence(key,text,f)],'source_context':context or {},'actor_type':'automated','actor_id':'curriculos-abertos:ro-lp-primary-audit','technical_validation_status':'complete_cell_and_continuation_pending_independent_readback'}
        records.append(r);keys[key]=r;return r
    roots=[(pn,b)for pn in range(121,144)for b in doc[pn-1].get_text('blocks')if re.match(r'9\.1\.3\s+Língua Portuguesa',b[4].strip())];assert len(roots)==1,roots
    pn,b=roots[0];g=NativeGlyphText(doc[pn-1]);add('lp-component-root',None,'componente_curricular',g.text(list(b[:4])).strip(),{'page':pn,'bbox':list(b[:4])})
    for title in titles:add('lp-block-p'+str(title['page']),'lp-component-root','grupo_curricular',title['text'],title,title['years'],context={'explicit_source_year_block':True,'annual_allocation_not_inferred_from_code':True})
    def append(r,text,f):
        r['text']+='\n'+text;r['evidence'].append(evidence(r['key'],text,f,len(r['evidence'])+1))
    def continuation(text,f,years):
        eligible=[r for r in body_active if r['_last']['page']in[f['page'],f['page']-1]and r['positions'][0]['years']==years and abs(r['_last']['bbox'][0]-f['bbox'][0])<3 and abs(r['_last']['bbox'][2]-f['bbox'][2])<3 and(r['_last']['page']==f['page']and r['_last']['bbox'][3]<=f['bbox'][1]+2 or r['_last']['page']==f['page']-1 and r['_last']['bbox'][3]>700)]
        if len(eligible)!=1:unattached.append({'page':f['page'],'bbox':f['bbox'],'text':text,'candidate_keys':[r['key']for r in eligible]});return
        r=eligible[0];append(r,text,f);r['_last']=f
    events=[{'role':'field',**f}for f in coded+kept]+[{'role':'block',**t}for t in titles]
    for f in sorted(events,key=lambda f:(f['page'],f['bbox'][1],f['bbox'][0],f['role'])):
        if f['role']=='block':body_active=[];context_active=None;phase='context';continue
        text=f['text'];literal=norm(text).casefold()
        if literal in['habilidades','habilidade']:
            phase='context';body_active=[];context_active=None;proofs.append({'role':'literal_column_header','page':f['page'],'bbox':f['bbox'],'text_sha256':sha(text.encode())});continue
        if re.fullmatch(r'[1-9]º',text.strip()):continue
        years,block,headers=placement(f);parent='lp-block-p'+str(block['page']);events=f['code_events']
        if not events:
            assert not re.search(r'EF\d{2}LP',text),(f['page'],'unclassified code fragment',text)
            if phase=='body':continuation(text,f,years);role='body_continuation'
            else:
                if context_active and context_active['_last']['page']in[f['page'],f['page']-1]and context_active['parent_key']==parent and abs(context_active['_last']['bbox'][0]-f['bbox'][0])<3 and abs(context_active['_last']['bbox'][2]-f['bbox'][2])<3:append(context_active,text,f)
                else:context_active=add('lp-context-p'+str(f['page'])+'-n'+str(len(records)),parent,'secao_normativa',text,f,years,context={'literal_role':'uncoded_documentary_field_context','objective_decomposition_pending':True,'not_a_coded_learning_definition':True})
                context_active['_last']=f;role='documentary_field_context'
            proofs.append({'role':role,'page':f['page'],'bbox':f['bbox'],'text_sha256':sha(text.encode())});continue
        prefix=text[:events[0]['start']].strip()
        if prefix:
            if f['page']==168 and prefix=='0':markers.append({'page':168,'bbox':f['bbox'],'literal':'0','role':'printed_marker_before_code_unresolved','source_fidelity_preserved':True})
            else:continuation(prefix,f,years)
        units=[]
        for index,event in enumerate(events):
            end=events[index+1]['start']if index+1<len(events)else len(text);body=text[event['after']:end].strip();assert body,(f['page'],event['code'],'code-only not a definition')
            key='lp-definition-p'+str(f['page'])+'-n'+str(len(records));r=add(key,parent,'habilidade',body,f,years,event['code'],{'source_block_header':block,'annual_column_headers':headers,'position_origin':'explicit_annual_column'if len(years)==1 and headers else'explicit_source_year_block','annual_allocation_not_inferred_from_code':True,'column_annual_labels_available':bool(headers),'literal_code_wrapper':event['wrapper'],'semantic_equivalence_asserted':False,'geometry_origin':f['geometry_origin']})
            r['evidence'].append(evidence(key,event['code'],f,role='code_locator'));r['_last']=f
            # A new physical row closes stale overlapping columns. Disjoint
            # parallel columns retain their own independent continuation owner.
            body_active=[old for old in body_active if old['_last']['bbox'][2]<=f['bbox'][0]+2 or old['_last']['bbox'][0]>=f['bbox'][2]-2]+[r]
            units.append({'key':key,'code':event['code'],'event':event,'body':body,'body_sha256':sha(body.encode())})
        phase='body';context_active=None;proofs.append({'role':'coded_learning_cell','page':f['page'],'bbox':f['bbox'],'text_sha256':sha(text.encode()),'prefix':prefix,'units':units})
    draft={'source_id':source['id'],'artifact_sha256':source['sha256'],'primary_census_sha256':sha(census_path.read_bytes()),'all_classified_fields':proofs,'unattached_fragments':unattached,'literal_unresolved_markers':markers,'definitions':sum(r['kind']=='habilidade'for r in records),'contexts':sum(r['kind']=='secao_normativa'for r in records),'source_code_count':394,'ready':False,'reconciled':False,'engine':{'python':sys.version,'pymupdf':fitz.VersionBind}}
    dump(BASE/'ef-lp-materialization-readiness.json',draft)
    assert not unattached,[(f['page'],f['text'][:100],f['candidate_keys'])for f in unattached]
    assert sum(r['kind']=='habilidade'for r in records)==394
    for r in records:r.pop('_last',None)
    base=json.loads((ROOT/'data/manifests/uncoded/ro-ef-with-fisica-v10.json').read_text());assert len(base['items'])==2179
    destination=ROOT/'data/manifests/uncoded/ro-ef-with-portugues-v11.json';generated=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if destination.exists():generated=json.loads(destination.read_text())['generated_at']
    adapter={**base,'generated_at':generated,'method':'Preserves2179prior records; all394literal LP definitions in physical cells with separate parallel-column continuations, explicit source year blocks/annual headers only. Documentary field contexts preserved separately. Pending independent body readback.','items':copy.deepcopy(base['items'])+records}
    dump(destination,adapter);draft.update({'adapter_path':str(destination.relative_to(ROOT)),'adapter_sha256':sha(destination.read_bytes()),'records':len(adapter['items']),'base2179_preserved_exactly':adapter['items'][:2179]==base['items'],'binding_ready':False,'manifest_cache_proposal_or_database_mutated':False,'command':'var/venv-pipeline/bin/python docs/evidence/source-audit-ro/build_ef_portugues.py'})
    dump(BASE/'ef-lp-materialization-readiness.json',draft);print(json.dumps({k:draft[k]for k in['definitions','contexts','records','adapter_sha256','literal_unresolved_markers']},ensure_ascii=False))

if __name__=='__main__':main()
