"""Source-column identifier reader proposal. No production pipeline mutation.

Only an explicit Código da Habilidade column authorizes whole-cell identifier
reading. This is not a global regex extension and never reinterprets prose or
turns national/local identifiers into equivalent learning relations.
"""
import re
# Characters actually observed in ES identifier cells are retained literally.
# Case and punctuation are never translated. Only internal layout whitespace is
# removed after validating a single national-looking identifier in a code column.
_BASE=r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2,3}|EM\d{2}(?:[A-Z]{3}\d{3}|LP\d{1,4}|CO\d{2}))'
_ONE=re.compile(r'^'+_BASE+r'[A-Za-z0-9*/\\.\-\u2010\u2011]*$')

def identifier_from_explicit_code_column(raw, header):
 normalized=' '.join(header.casefold().split())
 if not (normalized.startswith('código da habilidade') or normalized.startswith('codigo da habilidade') or normalized.startswith('código habilidade') or normalized.startswith('codigo habilidade') or normalized in ('código','codigo')):return None
 compact=re.sub(r'\s+','',raw)
 if not _ONE.fullmatch(compact):return None
 # A second complete national base means a joint/list cell: separate handling.
 starts=list(re.finditer(_BASE,compact))
 if len(starts)!=1:return None
 return {'code':compact,'original_code_cell_text':raw,'identifier_origin':'explicit_source_code_column','code_whitespace_policy':'Source column typography only; case and punctuation preserved','national_equivalence_claimed':False}
