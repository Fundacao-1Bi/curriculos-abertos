#!/usr/bin/env python3
"""Independent physical glyph/line denominator and review atlas; OCR labels are candidates."""
import collections,hashlib,json,math,struct,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;PRIVATE=ROOT/'var/private-evidence/source-audit-southeast-completeness/mg-matrizes2026-ocr13';WORK=PRIVATE/'glyph-review-v1';WORK.mkdir(exist_ok=True)
S=next(s for s in json.load((ROOT/'data/manifests/bncc-southeast.json').open())if s['id']=='mg-matrizes-2026');P=ROOT/S['local_path'];assert hashlib.sha256(P.read_bytes()).hexdigest()==S['sha256'];D=fitz.open(P)
def font_empty_glyphs(buf):
 if len(buf)<12:return set()
 n=struct.unpack_from('>H',buf,4)[0];tabs={}
 for i in range(n):
  tag,chk,off,ln=struct.unpack_from('>4sIII',buf,12+i*16);tabs[tag.decode('latin1')]=(off,ln)
 if not all(k in tabs for k in ['head','maxp','loca']):return set()
 count=struct.unpack_from('>H',buf,tabs['maxp'][0]+4)[0];fmt=struct.unpack_from('>h',buf,tabs['head'][0]+50)[0];ls=[struct.unpack_from('>I'if fmt else'>H',buf,tabs['loca'][0]+i*(4 if fmt else 2))[0]*(1 if fmt else 2)for i in range(count+1)];return{i for i in range(count)if ls[i]==ls[i+1]}
fonts={};glyphs={};pages=[];candidate_counts=collections.defaultdict(collections.Counter);mismatches=[]
for pn in range(1,14):
 p=D[pn-1];pf={}
 for xref,ext,typ,base,*_ in p.get_fonts(full=True):
  _,_,_,buf=D.extract_font(xref);name=base.split('+')[-1];h=hashlib.sha256(buf).hexdigest();fid=name+':'+h[:16];entry={'font_id':fid,'font_name':name,'program_sha256':h,'xref':xref,'empty_glyph_ids':sorted(font_empty_glyphs(buf))};fonts[fid]=entry;pf[name]=entry
 traces=[]
 for si,sp in enumerate(p.get_texttrace()):
  if sp.get('type')==3:continue
  assert abs(sp.get('dir',(1,0))[0]-1)<.01,('unexpected body direction',pn,sp.get('dir'))
  f=pf[sp['font']]
  for ci,c in enumerate(sp['chars']):
   key=f['font_id']+':gid:'+str(c[1]);g={'page':pn,'font_id':f['font_id'],'gid':c[1],'key':key,'source_unicode':c[0],'origin':list(c[2]),'bbox':list(c[3]),'empty_shape':c[1]in f['empty_glyph_ids'],'trace_span':si,'trace_character':ci};traces.append(g)
   if key not in glyphs:glyphs[key]={'key':key,'font_id':f['font_id'],'gid':c[1],'empty_shape':g['empty_shape'],'source_unicode_values':set(),'occurrences':0,'exemplar':g}
   glyphs[key]['source_unicode_values'].add(c[0]);glyphs[key]['occurrences']+=1
 groups=[]
 for g in sorted(traces,key=lambda g:(g['origin'][1],g['origin'][0])):
  if groups and abs(g['origin'][1]-groups[-1][0])<=.35:groups[-1][1].append(g)
  else:groups.append([g['origin'][1],[g]])
 lines=[]
 for li,(baseline,gs)in enumerate(groups):
  gs.sort(key=lambda g:g['origin'][0]);lines.append({'page':pn,'source_line':li,'baseline':baseline,'bbox':[min(g['bbox'][0]for g in gs),min(g['bbox'][1]for g in gs),max(g['bbox'][2]for g in gs),max(g['bbox'][3]for g in gs)],'glyphs':gs})
 o=json.load((PRIVATE/f'page-{pn:02}-ocr-candidate.json').open())
 for w in o['words']:
  if w['confidence']<80:continue
  yc=(w['top']+w['bottom'])/2;line=min(lines,key=lambda r:abs((r['bbox'][1]+r['bbox'][3])/2-yc));selected=[g for g in line['glyphs']if not g['empty_shape']and w['x0']-.3<=(g['bbox'][0]+g['bbox'][2])/2<=w['x1']+.3];text=w['text']
  if len(selected)==len(text):
   for g,ch in zip(selected,text):candidate_counts[g['key']][ch]+=1
  else:mismatches.append({'page':pn,'ocr_word':text,'confidence':w['confidence'],'source_glyphs':len(selected),'ocr_characters':len(text)})
 pages.append({'page':pn,'independent_source_lines':lines,'trace_visible_glyph_occurrences':len(traces),'ocr_words':o['word_count']})
ordered=[]
for k,g in sorted(glyphs.items(),key=lambda kv:(kv[1]['font_id'],kv[1]['gid'])):
 known=[x for x in g['source_unicode_values']if x>=32 and x!=65533];g['source_unicode_values']=sorted(g['source_unicode_values']);g['ocr_character_candidates']=[{'character':ch,'unicode':'U+'+format(ord(ch),'04X'),'votes':n}for ch,n in candidate_counts[k].most_common()];g['unicode_already_known']=known[0]if len(set(known))==1 else None
 if not g['empty_shape']and g['unicode_already_known']is None:ordered.append(g)
for sheet in range(math.ceil(len(ordered)/36)):
 doc=fitz.open();page=doc.new_page(width=720,height=900)
 for j,g in enumerate(ordered[sheet*36:(sheet+1)*36]):
  row,col=divmod(j,6);x,y=col*120,row*145;ex=g['exemplar'];b=fitz.Rect(ex['bbox'])+(-.4,-.4,.4,.4);pix=D[ex['page']-1].get_pixmap(matrix=fitz.Matrix(6,6),clip=b,alpha=False);cand=g['ocr_character_candidates'][0]['unicode']if g['ocr_character_candidates']else'NO_CANDIDATE';label=f'{sheet*36+j:03} gid{g["gid"]} {cand}';page.insert_text((x+4,y+14),label,fontsize=7);page.insert_text((x+4,y+24),g['font_id'].split(':')[0][:22],fontsize=6);page.insert_image(fitz.Rect(x+25,y+30,x+95,y+115),stream=pix.tobytes('png'),keep_proportion=True);page.insert_text((x+4,y+130),f'p{ex["page"]} n={g["occurrences"]}',fontsize=7)
 target=WORK/f'glyph-atlas-{sheet+1:02}.png';page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(target);doc.close()
report={'source_id':S['id'],'source_sha256':S['sha256'],'method':'Independent physical original glyph/line inventory from PDF trace. OCR supplies suggestions only; every unknown nonempty glyph requires primary visual review. Empty shape is whitespace/format, not guessed letters.','fonts':list(fonts.values()),'glyph_inventory':list(glyphs.values()),'atlas_order':[g['key']for g in ordered],'unknown_nonempty_glyphs_for_primary_review':len(ordered),'source_pages':pages,'ocr_alignment_mismatches':mismatches,'primary_visual_review_completed':False};(WORK/'physical-glyph-line-inventory.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n');print(json.dumps({'unknown_nonempty_glyphs':len(ordered),'glyph_occurrences':sum(p['trace_visible_glyph_occurrences']for p in pages),'source_lines':sum(len(p['independent_source_lines'])for p in pages),'atlas_sheets':math.ceil(len(ordered)/36),'candidate_votes_available':sum(bool(g['ocr_character_candidates'])for g in ordered),'OCR_alignment_mismatches':len(mismatches)},ensure_ascii=False,indent=2))
