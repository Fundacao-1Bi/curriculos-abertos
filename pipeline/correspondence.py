"""Additional documentary associations and deliberately non-official lexical candidates."""
from __future__ import annotations
import collections
import hashlib
import math
import re

LEARNING_KINDS={'habilidade','objetivo_aprendizagem','capacidade','direito_aprendizagem','habilidade_local_sem_codigo'}
STOP=set('a as o os e em de da das do dos para por com como que se na nas no nos um uma umas uns ao aos ou sua suas seu seus esse essa esses essas este esta estes estas dos das pela pelo pelas pelos ser sobre entre mais menos muito nos sem sob suas mesmo cada'.split())


def _id(*parts):return 'ca:relation:'+hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:24]

def _event(item,method):
    return {'actor_type':'automated','actor_id':'curriculos-abertos:documentary-and-lexical-associations','method':method,'at':next((event.get('at') for event in item.get('review_events',[]) if event.get('at')),None),'result':'documented_association' if method.startswith('document') else 'lexical_candidate_not_pedagogically_validated'}


def _partial_evidence(item):
    if not item.get('evidence'):return []
    evidence=dict(item['evidence'][0])
    excerpt=evidence.get('excerpt','')
    if len(excerpt)>400:
        evidence['excerpt']=excerpt[:400]+' […]';evidence['excerpt_is_partial']=True
    return [evidence]


def documentary_links(items,sources):
    national_by_code={}
    by_id={item['id']:item for item in items}
    for item in items:
        if item.get('uf')!='BR':continue
        for code in ([item['code']] if item.get('code') else [])+item.get('code_aliases',[]):national_by_code[code]=item
    output=[]
    for item in items:
        if item.get('uf')=='BR' or item.get('kind') not in LEARNING_KINDS or item.get('code'):continue
        context=item.get('source_context') or {}
        codes=list(context.get('reference_codes') or [])
        if context.get('parent_code_original'):codes.append(context['parent_code_original'])
        refs=context.get('reference_evidence') or {}
        anchors=refs.get('anchors',[]) if isinstance(refs,dict) else refs if isinstance(refs,list) else []
        if not anchors and item.get('parent_id') in by_id:
            parent=by_id[item['parent_id']]
            if parent.get('code'):anchors=parent.get('evidence',[])
        targets={national_by_code[code]['id']:national_by_code[code] for code in codes if code in national_by_code}
        if not targets or not (anchors or context.get('parent_objective_heading')):continue
        evidence=_partial_evidence(item)
        for anchor in anchors:
            if not isinstance(anchor,dict):continue
            excerpt=anchor.get('excerpt') or anchor.get('code')
            page=anchor.get('page') or item['evidence'][0]['page']
            if excerpt and page:evidence.append({'source_id':item['source_id'],'page':page,'printed_page':None,'section':'Referência nacional no mesmo quadro documental','excerpt':excerpt,'bbox':anchor.get('bbox')})
        output.append({'id':_id(item['id'],'documented-row-reference',*sorted(targets)),'members':[{'item_id':item['id'],'role':'source','scope':'Local objective placed in the source row/heading explicitly associated with these references.'}]+[{'item_id':target,'role':'target','scope':'Reference expressly printed in the same documentary grouping; no full coverage/equivalence asserted.'} for target in sorted(targets)],'relation_type':'referencia_nacional','origin':'declaracao_fonte','technical_validation_status':'documentary_row_reference_checked','pedagogical_review_status':'not_reviewed','publication_status':'documented_reference','method':'documented-uncoded-row-reference-v1','evidence':evidence,'scope':'Agrupamento documental explícito. Objetivos sem código próprio permanecem sem código; o conjunto não comprova equivalência ou cobertura integral.','review_events':[_event(item,'documented-uncoded-row-reference-v1')]})
    for source in sources:
        for relation in source.get('explicit_relations',[]):
            source_ids=relation.get('source_item_ids') or [relation.get('source_item_id')]
            target_ids=relation.get('target_item_ids') or [relation.get('target_item_id')]
            if any(item_id not in by_id for item_id in source_ids+target_ids):continue
            if not relation.get('evidence'):continue
            first=by_id[source_ids[0]]
            output.append({'id':relation.get('id') or _id(source['id'],'explicit-source-association',*source_ids,*target_ids),'members':[{'item_id':item_id,'role':'source','scope':relation.get('scope','Explicit source association')} for item_id in source_ids]+[{'item_id':item_id,'role':'target','scope':relation.get('scope','Explicit source association')} for item_id in target_ids],'relation_type':relation.get('relation_type','relacao_generica'),'origin':'declaracao_fonte','technical_validation_status':'primary_source_explicit_relation_checked','pedagogical_review_status':'not_reviewed','publication_status':'documented_reference','method':'documented-explicit-source-association-v1','evidence':relation['evidence'],'scope':relation.get('scope'),'review_events':[_event(first,'documented-explicit-source-association-v1')]})
    return output


def lexical_candidates(items,relations,normalize):
    """IDF-weighted token Jaccard. A candidate never becomes an official declaration."""
    targets=[item for item in items if item.get('uf')=='BR' and item.get('kind') in LEARNING_KINDS]
    target_by_id={item['id']:item for item in targets}
    def tokens(item):return {token for token in re.findall(r'[a-z]{3,}',normalize(item['text'])) if token not in STOP}
    target_tokens={item['id']:tokens(item) for item in targets}
    index=collections.defaultdict(set)
    for item_id,words in target_tokens.items():
        for word in words:index[word].add(item_id)
    idf={word:math.log((1+len(targets))/(1+len(ids)))+1 for word,ids in index.items()}
    linked={member['item_id'] for relation in relations for member in relation.get('members',[]) if member['role']=='source'}
    output=[]
    for item in items:
        if item.get('uf')=='BR' or item['id'] in linked or item.get('kind') not in LEARNING_KINDS:continue
        words=tokens(item)
        if len(words)<5 or len(words)>250:continue
        candidates=set()
        for word in words:
            if len(index.get(word,()))<=80:candidates.update(index.get(word,()))
        source_stages={p['stage'] for p in item.get('positions',[])}
        best=None
        for target_id in candidates:
            target=target_by_id[target_id]
            target_stages={p['stage'] for p in target.get('positions',[])}
            if source_stages and target_stages and not source_stages.intersection(target_stages):continue
            other=target_tokens[target_id]
            shared=words&other
            if len(shared)<5:continue
            numerator=sum(idf.get(word,1) for word in shared)
            denominator=sum(idf.get(word,1) for word in words|other)
            score=numerator/denominator if denominator else 0
            if score>=0.72 and (best is None or score>best[0] or score==best[0] and target_id<best[1]):best=(score,target_id,shared)
        if best is None:continue
        score,target_id,shared=best;target=target_by_id[target_id]
        output.append({'id':_id(item['id'],target_id,'lexical-candidate-v1'),'members':[{'item_id':item['id'],'role':'source','scope':'Automatically suggested lexical overlap; pedagogical coverage unknown.'},{'item_id':target_id,'role':'target','scope':'Candidate only; not an official equivalence.'}],'relation_type':'sobreposicao_parcial','origin':'sugestao_automatica','technical_validation_status':'algorithm_output_only','pedagogical_review_status':'not_reviewed','publication_status':'candidate_pending','method':'portuguese-idf-weighted-token-jaccard-v1','score':round(score,6),'score_definition':'IDF-weighted Jaccard of distinct normalized Portuguese tokens; minimum score 0.72 and five shared non-stopwords. Not semantic search or pedagogical validation.','shared_tokens':sorted(shared),'evidence':_partial_evidence(item)+_partial_evidence(target),'scope':'Candidata lexical. Não constitui declaração oficial, equivalência, pré-requisito ou cobertura integral. Não revisada pedagogicamente.','review_events':[_event(item,'lexical-candidate-v1')]})
    return output
