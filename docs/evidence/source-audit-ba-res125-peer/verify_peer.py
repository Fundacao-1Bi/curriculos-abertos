#!/usr/bin/env python3
import hashlib,json,re,sys,unicodedata
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;sys.path.insert(0,str(ROOT/'pipeline'))
from native_glyphs import NativeGlyphText
P=ROOT/'data/manifests/uncoded/ba-resolucao-125-items.json';PIN='f6f1a1579883c97bdce5ab0592357e59af86681b004d6747f8789db6828ffa9d';assert hashlib.sha256(P.read_bytes()).hexdigest()==PIN
expected=json.loads((OUT/'source-visual-denominator.json').read_text());actual=json.loads(P.read_text());SID=actual[0]['source_id'];sources=json.loads((ROOT/'data/manifests/northeast.json').read_text());source=next(s for s in sources if s['id']==SID);assert hashlib.sha256((ROOT/source['local_path']).read_bytes()).hexdigest()==actual[0]['artifact_sha256']==source['sha256']
# Initial independent visual transcription is retained. Two ambiguous tiny-page readings
# were resolved by 3x original-PDF crops before this comparison; no source/output changed.
resolved={8:('história da Bahia, com os seguintes propósitos:','História da Bahia, com os seguintes propósitos:'),9:('potencializando o seu entendimento','potencializando seu entendimento')}
checks=[];failures=[];byrole={};D=fitz.open(ROOT/source['local_path']);readers={n:NativeGlyphText(D[n-1])for n in [1,2]}
def canon(t):return re.sub(r'\s','',unicodedata.normalize('NFC',t))
for row,item in zip(expected['units'],actual):
 text=row['text']
 if row['order']in resolved:text=text.replace(*resolved[row['order']])
 a=item['text'];symbolic=0
 if row['role']=='footer_context':symbolic=a.count('\uf0dc');a=a.replace('\uf0dc','')
 text_ok=canon(text)==canon(a);evidence_ok=all(canon(e['excerpt'])in canon(readers[e['page']].text(e['bbox']))for e in item['evidence']);composition=canon(item['text'])==canon(' '.join(e['excerpt']for e in item['evidence']));checks.append({'visual_order':row['order'],'role':row['role'],'page':row['page'],'key':item['key'],'text_matches_source_visual_reading':text_ok,'all_native_evidence_fragments_match_original_glyph_stream':evidence_ok,'evidence_composition':composition,'original_symbolic_footer_glyphs_preserved':symbolic if row['role']=='footer_context'else None});byrole[row['role']]=item
 if not text_ok or not evidence_ok or not composition:failures.append(checks[-1])
assert len(actual)==expected['public_visual_units']==23
keys={i['key']for i in actual};orphans=[i['key']for i in actual if i.get('parent_key')and i['parent_key']not in keys];root=actual[0]['key'];graph=[]
for child,parent in [('quoted_art19','outer_art1'),('quoted_par1','quoted_art19'),('quoted_par2','quoted_art19'),('quoted_par3','quoted_art19'),('quoted_incisoI','quoted_par2'),('quoted_incisoII','quoted_par2'),('quoted_incisoIII','quoted_par2'),('outer_art2_paragraph','outer_art2')]:graph.append({'child_role':child,'parent_role':parent,'passed':byrole[child]['parent_key']==byrole[parent]['key']})
for role,stage in [('quoted_incisoI','EI'),('quoted_incisoII','EF'),('quoted_incisoIII','EM')]:graph.append({'role':role,'source_explicit_stage':stage,'passed':any(p.get('stage')==stage for p in byrole[role].get('positions',[]))})
graph.append({'role':'quoted_incisoI','negative':'EI is not assigned the EF/EM discipline created by outer Art2','passed':all(p.get('component')is None for p in byrole['quoted_incisoI'].get('positions',[]))})
# Count only printed meaningful source text inside the body/footer bands. Logos and decorative
# shape marks are not new curricular definitions. Each line is covered by one node's real bbox.
partition=[]
for pn in [1,2]:
 for li,clusters in enumerate(readers[pn].lines):
  t=''.join(c['text']for c in clusters)
  if not t.strip():continue
  cx=sum((c['box'][0]+c['box'][2])/2 for c in clusters)/len(clusters);cy=sum((c['box'][1]+c['box'][3])/2 for c in clusters)/len(clusters)
  if cy<75:continue
  owners=[i['key']for i in actual for e in i['evidence']if e['page']==pn and e['bbox'][0]-.2<=cx<=e['bbox'][2]+.2 and e['bbox'][1]-.2<=cy<=e['bbox'][3]+.2]
  partition.append({'page':pn,'original_line':li,'owners':owners})
partition_failures=[p for p in partition if len(p['owners'])!=1];imagepaths=expected['private_renders']+['var/private-evidence/source-audit-northeast/ba-res125-quoted-history-case-crop.png','var/private-evidence/source-audit-northeast/ba-res125-inciso-I-pronoun-crop.png'];images=[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}for p in imagepaths]
report={'source_id':SID,'source_sha256':source['sha256'],'sidecar_sha256':PIN,'independent_visual_units':23,'sidecar_nodes':len(actual),'all_units':checks,'visual_ambiguity_resolutions':[{'order':8,'initial_peer_reading':'história da Bahia','original_crop_reading':'História da Bahia','sidecar_changed':False},{'order':9,'initial_peer_reading':'potencializando o seu entendimento','original_crop_reading':'potencializando seu entendimento','sidecar_changed':False}],'private_original_renders':images,'hierarchy_checks':graph,'orphans':orphans,'original_horizontal_meaningful_lines':len(partition),'line_partition_failures':partition_failures,'literal_failures':failures,'code_null_on_all_nodes':all(i.get('code')is None for i in actual),'rights':'No full original page images published. Existing private renders only; two small ambiguity crops from original source by author.','limitations':['Automated documentary peer, not human pedagogical review.','No legal vigency or cryptographic signature validity asserted.','Title/session21June, homologation25June and publication26June remain distinct.'],'passed':not failures and not orphans and not partition_failures and all(c['passed']for c in graph)};(OUT/'peer-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(report['passed'],len(partition),len(failures),len(partition_failures));assert report['passed']
