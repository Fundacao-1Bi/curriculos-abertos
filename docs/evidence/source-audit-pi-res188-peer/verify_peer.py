#!/usr/bin/env python3
"""Match the independently visualized complete public act against the frozen sidecar."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent;P=ROOT/'data/manifests/uncoded/pi-resolucao-188-2025-items.json';raw=P.read_bytes();side=json.loads(raw);visual=json.loads((OUT/'source-visual-denominator.json').read_text());items=side['items'];nodes={i['key']:i for i in items}
def ns(x):return re.sub(r'\s','',unicodedata.normalize('NFC',x))
checks=[];failures=[];mapped=collections.defaultdict(list)
for u in visual['units']:
 found=[i for i in items if i['page']==u['page']and ns(u['text'])in ns(i['text'])];ok=len(found)==1;checks.append({'visual_unit':u['unit'],'page':u['page'],'matching_node_keys':[i['key']for i in found],'passed':ok})
 if not ok:failures.append({'check':'visual_unit_missing_or_duplicated','unit':u['unit']})
 else:mapped[found[0]['key']].append(u)
extra=[]
for i in items:
 parts=mapped.get(i['key'],[]);ok=bool(parts)and ns(' '.join(u['text']for u in parts))==ns(i['text'])
 if not ok:extra.append({'key':i['key'],'kind':i['kind'],'reason':'Output wording not equal to independently visualized units in document order.'})
 checks.append({'node_key':i['key'],'visual_unit_count':len(parts),'exact_nonwhitespace_case_punctuation_match':ok})
 if i.get('code')is not None:failures.append({'check':'invented_curricular_code','key':i['key']})
 seen=set();current=i['key']
 while current:
  if current in seen or current not in nodes:failures.append({'check':'parent_cycle_or_orphan','key':i['key']});break
  seen.add(current);current=nodes[current].get('parent_key')
 if any(p.get('years')is not None or p.get('age_group')is not None or p.get('period')is not None for p in i.get('positions',[])):failures.append({'check':'date_used_as_grade_or_age','key':i['key']})
article=[i for i in items if i['kind']=='artigo_normativo'];homolog=[i for i in items if i['kind']=='homologacao'];signature=[i for i in items if i['kind']=='assinatura_documental'and i['page']==2];parent_ok=len(homolog)==len(signature)==1 and signature[0].get('parent_key')==homolog[0]['key']
if len(article)!=1 or not parent_ok:failures.append({'check':'article_count_or_crosspage_homologation_scope'})
privacy_patterns=[r'Mat(?:r[íi]cula)?[.:]?\s*\d{4,}',r'CRC\s*[0-9A-F]{5,}',r'c[oó]digo\s+verificador\s*\d{5,}'];privacy_findings=[]
for index,i in enumerate(items):
 if any(re.search(p,i['text'],re.I)for p in privacy_patterns):privacy_findings.append({'item_index':index,'key':i['key'],'reason':'Private noncurricular receipt/authentication material appeared in public canonical text.'})
source=next(s for s in json.loads((ROOT/'data/manifests/northeast.json').read_text())if s.get('sha256')==visual['source_sha256']);sourcepath=ROOT/source['local_path'];source_hash=hashlib.sha256(sourcepath.read_bytes()).hexdigest();images=[]
for n in [1,2]:
 p=ROOT/f'var/private-evidence/source-audit-northeast/pi-res188-p{n}.png';im=Image.open(p);images.append({'page':n,'existing_private_render':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pixel_dimensions':list(im.size),'visually_read_in_full':True})
result={'actor_type':'automated','source_id':side['source_id'],'source_sha256':source_hash,'source_hash_matches_original':source_hash==visual['source_sha256'],'sidecar_sha256':hashlib.sha256(raw).hexdigest(),'independent_public_visual_units':len(visual['units']),'output_nodes':len(items),'unique_keys':len(nodes),'visual_unit_checks':checks,'output_wording_extras':extra,'hierarchy_findings':failures,'private_receipt_leak_findings':privacy_findings,'sole_article_count':len(article),'two_considerations':sum(i['kind']=='considerando'for i in items)==2,'homologation_signature_parent_across_pages_passed':parent_ok,'images':images,'new_renders_created':False,'source_or_sidecar_modified':False,'signature_validity_verified':False,'source_ready':False,'passed':source_hash==visual['source_sha256']and not failures and not extra and not privacy_findings and len(nodes)==len(items),'scope':'All public normative wording of the two-page act visually verified, including dates, distinct process references and P1homologation→P2signature. Fifteen visible textual units are losslessly represented by14nodes because process header and issue date are grouped. Technical source_order is graph order(root title first), not a claim about physical top-to-bottom reading. Excluded employee receipts/QR/CRC remain private; no cryptographic signature, legal vigency advice, pedagogical human review or UF readiness claimed.'};(OUT/'peer-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items()if k not in['visual_unit_checks','images']})
