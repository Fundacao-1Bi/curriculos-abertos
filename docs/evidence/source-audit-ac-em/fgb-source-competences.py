#!/usr/bin/env python3
"""Inventory full specific competencies and numeric references from original native words."""
from pathlib import Path
import collections,json,re
import fitz
R=Path(__file__).resolve().parents[3];O=R/'docs/evidence/source-audit-ac-em';I=json.loads((O/'fgb-native-checkpoint.json').read_text());D=fitz.open(R/'data/raw/AC/ac-cru-em.pdf');norm=lambda s:re.sub(r'\s+',' ',s).strip()
def rows(ws):
 groups=[]
 for w in sorted(ws,key=lambda w:(w[1],w[0])):
  z=next((r for r in groups[-2:]if abs(r[0][1]-w[1])<1.8),None)
  if z is None:groups.append([w])
  else:z.append(w)
 return[sorted(r,key=lambda w:w[0])for r in groups]
W={n+1:[list(w[:5])for row in rows(p.get_text('words'))for w in row if 65<=w[1]<784]for n,p in enumerate(D)}
lines=[]
for pn in range(112,386):
 for row in rows(W[pn]):lines.append({'page':pn,'bbox':[min(w[0]for w in row),min(w[1]for w in row),max(w[2]for w in row),max(w[3]for w in row)],'text':norm(' '.join(w[4]for w in row)),'words':row})
def fragments(words):
 out=[]
 for pn,ws in words:
  if not ws:continue
  out.append({'page':pn,'bbox':[min(w[0]for w in ws),min(w[1]for w in ws),max(w[2]for w in ws),max(w[3]for w in ws)],'words':ws,'text':norm(' '.join(w[4]for w in ws))})
 return out
stop=lambda t:bool(re.fullmatch(r'COMPETÊNCIA(?: ESPECÍFICA)? [1-9]',t)or t.startswith('QUADRO ORGANIZADOR')or t in ['HABILIDADE COMPONENTES OBJETOS DE CONHECIMENTO','HABILIDADE OBJETOS DE CONHECIMENTO','HABILIDADE OBJETOS DE PROPOSTAS DE ATIVIDADES','LINGUAGENS E SUAS TECNOLOGIAS','LÍNGUA PORTUGUESA','HABILIDADE','NÚMEROS E ÁLGEBRA','GEOMETRIA E MEDIDAS','PROBABILIDADE E ESTATÍSTICA']or t.startswith('HABILIDADE '))
numbered=[]
for ix,l in enumerate(lines):
 if not re.fullmatch(r'COMPETÊNCIA(?: ESPECÍFICA)? [1-9]',l['text']):continue
 body=[]
 for nxt in lines[ix+1:]:
  if stop(nxt['text']):break
  body.append(nxt)
 groups=[]
 for z in [l]+body:
  if groups and groups[-1][0]==z['page']:groups[-1][1].extend(z['words'])
  else:groups.append([z['page'],list(z['words'])])
 numbered.append({'source_number':l['text'].split()[-1],'heading':{k:l[k]for k in ['page','bbox','text']},'role':'specific_competence_definition'if body else'competence_number_reference_only','fragments':fragments(groups),'text':norm(' '.join(x['text']for x in [l]+body))})
# Explicit intro lists, bounded by their own primary lead-out sentences, never TOC.
intros=[]
for area,pages,startpat,endpat,pat in [
 ('LGG',[113,114],r'\b1\. Compreender o funcionamento',r'Sobre as habilidades provenientes',r'(?<!\S)[1-7]\. (?=[A-ZÁÉÍÓÚ])'),
 ('CNT',[282],r'- Competência Específica 1:',r'O Currículo de Referência Único do Acre',r'- Competência Específica [1-3]:'),
 ('CHS',[323,324],r'– Competência específica 1:',r'O estudo das Ciências Humanas',r'[–-] Competência específica [1-6]:')]:
 tokens=[(pn,w)for pn in pages for w in W[pn]];joined=' '.join(w[4]for pn,w in tokens);start=re.search(startpat,joined).start();end=re.search(endpat,joined).start();segment=joined[start:end];matches=list(re.finditer(pat,segment));offsets=[];at=0
 for pn,w in tokens:offsets.append((at,at+len(w[4]),pn,w));at+=len(w[4])+1
 for i,m in enumerate(matches):
  a=start+m.start();b=start+(matches[i+1].start()if i+1<len(matches)else len(segment));sel=[(pn,w)for x,y,pn,w in offsets if a<=x<b];groups=[]
  for pn,w in sel:
   if groups and groups[-1][0]==pn:groups[-1][1].append(w)
   else:groups.append([pn,[w]])
  fs=fragments(groups);intros.append({'area':area,'source_number':re.search(r'[1-7]',m.group()).group(),'role':'specific_competence_definition','source_context':'introductory_explicit_specific_competence_list','fragments':fs,'text':norm(' '.join(f['text']for f in fs))})
full=[x for x in numbered if x['role']=='specific_competence_definition'];refs=[x for x in numbered if x['role']=='competence_number_reference_only'];issues=[]
if len(numbered)!=89:issues.append({'unexpected_markers':len(numbered)})
if len(full)!=44:issues.append({'unexpected_full_numbered':len(full)})
if len(refs)!=45:issues.append({'unexpected_reference_labels':len(refs)})
if collections.Counter(x['area']for x in intros)!={'LGG':7,'CNT':3,'CHS':6}:issues.append({'intro_marker_inventory_mismatch':dict(collections.Counter(x['area']for x in intros))})
out={'source_id':I['source_id'],'artifact_sha256':I['artifact_sha256'],'method':'Original native word/line stream; numbered heading starts and physical column/area terminators. Intro lists split only at printed numbered markers and explicit following prose. Preserve repeated definitions and reference-only numeric labels separately.','cache_or_FGB_adapter_consulted':False,'numbered_markers':len(numbered),'full_numbered_definitions':len(full),'numeric_reference_only_labels':len(refs),'intro_definition_occurrences':len(intros),'full_specific_competence_occurrences':len(full)+len(intros),'numbered_parts':numbered,'intro_parts':intros,'issues':issues,'result':'pass'if not issues else'fail'}
(O/'fgb-source-specific-competences.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['numbered_markers','full_numbered_definitions','numeric_reference_only_labels','intro_definition_occurrences','full_specific_competence_occurrences','issues','result']},ensure_ascii=False,indent=2))
