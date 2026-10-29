"""Reviewed primary locators for immutable licensed national skill records.

Evidence is corrected without changing identity, source codes or search aliases.
Exactly eight reviewed records restore primary PDF EN DASH punctuation in a new
extraction; their exact licensed upstream wording is retained separately. All
other canonical wording remains invariant and no checker normalization is added.
"""
import hashlib
import copy
import json
from pathlib import Path

PATH='docs/evidence/source-audit-br-fidelity/locator-overrides.json'
SHA256='917adac1463d26d77122165c7c438a5f72bca97cdab943c3012170ec9008d81f'
_CACHE=None
PRIMARY_TEXT_CORRECTIONS={'EM13CHS302','EM13CHS606','EM13CNT107','EM13LP26','EM13LP34','EM13LP37','EM13LP40','EM13LP54'}


def apply_primary_evidence(root,source,item):
    global _CACHE
    if source['id'] not in ('br-bncc-2018','br-bncc-computacao-2022'):return item
    if _CACHE is None:
        data=(root/PATH).read_bytes()
        if hashlib.sha256(data).hexdigest()!=SHA256:raise ValueError('National primary locator proof checksum mismatch')
        _CACHE=json.loads(data)
    group=_CACHE['sources'].get(source['id'])
    if not group or group['artifact_sha256']!=source.get('sha256'):raise ValueError('National primary locator source SHA mismatch')
    record=group['records'].get(item['id'])
    if not record:return item
    if record['expected_code']!=item['code'] or record['canonical_text_sha256']!=hashlib.sha256(item['text'].encode()).hexdigest():raise ValueError('National locator item code/text identity mismatch')
    before=(item['id'],item['code'],item.get('code_aliases'));old_text=item['text']
    if 'text' in record:
        correction=record.get('primary_transcription_correction') or {};new_text=record['text'];upstream=record.get('upstream_text');raw=record.get('primary_source_text')
        sha=lambda value:hashlib.sha256(value.encode()).hexdigest()
        if source['id']!='br-bncc-2018' or item['code'] not in PRIMARY_TEXT_CORRECTIONS or correction.get('method')!='primary_pdf_dash_transcription_correction_v1':raise ValueError('Unapproved national canonical text modification')
        if correction.get('source_id')!=source['id'] or correction.get('artifact_sha256')!=source['sha256'] or correction.get('item_id')!=item['id'] or correction.get('code')!=item['code']:raise ValueError('Primary transcription identity mismatch')
        if upstream!=old_text or sha(upstream)!=correction.get('upstream_text_sha256') or not isinstance(raw,str) or sha(raw)!=correction.get('primary_source_text_sha256') or sha(new_text)!=correction.get('corrected_text_sha256'):raise ValueError('Primary transcription text checksum mismatch')
        if ' '.join(raw.split())!=new_text or new_text.replace('–','-')!=old_text:raise ValueError('Primary transcription changed more than the documented EN DASH glyphs')
        for key in ('proof','decision'):
            proof=(root/correction[f'{key}_path']).resolve()
            if not proof.is_relative_to(root.resolve()) or hashlib.sha256(proof.read_bytes()).hexdigest()!=correction[f'{key}_sha256']:raise ValueError('Primary transcription evidence/decision checksum mismatch')
        for field in ('text','upstream_text','primary_transcription_correction','text_origin'):item[field]=copy.deepcopy(record[field])
        item['review_events'].append({'actor_type':'automated','actor_id':'curriculos-abertos:primary-transcription-correction','method':'primary_pdf_dash_transcription_correction_v1','at':_CACHE['generated_at'],'result':'extraction_correction_primary_punctuation_restored_not_official_curricular_change'})
    for field in ('evidence','primary_source_text','primary_typographic_equivalence','canonical_text_policy','technical_validation_status','editorial_note'):
        if field in record:item[field]=copy.deepcopy(record[field])
    item.setdefault('source_context',{})['primary_locator_review']={'proof_path':PATH,'proof_sha256':SHA256,'verification':copy.deepcopy(record['verification'])}
    item['review_events'].append({'actor_type':'automated','actor_id':'codex-independent-br-fidelity-auditor','method':'primary-source-cell-and-code-locator-review','at':_CACHE['generated_at'],'result':'primary_locators_checked_with_record_bound_typography_if_explicit'})
    if before!=(item['id'],item['code'],item.get('code_aliases')) or (item['text']!=old_text and item['code'] not in PRIMARY_TEXT_CORRECTIONS):raise AssertionError('National immutable identity/code fields or unapproved canonical text changed')
    return item
