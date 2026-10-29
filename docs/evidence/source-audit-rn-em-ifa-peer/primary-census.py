"""Pinned primary-only census; never opens adapter/author output."""
import collections,datetime,hashlib,json,pathlib,re
import pymupdf
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent
SID='rn-referencial-em';SOURCE=next(s for s in json.loads((R/'data/manifests/northeast.json').read_text()) if s['id']==SID)
p=R/SOURCE['local_path'];assert p.name=='rn-referencial-oficial.pdf';assert hashlib.sha256(p.read_bytes()).hexdigest()=='5f894abaa0309169597c7c9b7841aebaa9faaeb45e4cb759e5058b359e2ed845'
with pymupdf.open(p) as doc:
 assert len(doc)==570
 codes=[];all_lines=[];footers=[];excluded=[];groups=[];axes=[];page_hashes={};cg06=[]
 for pn in range(545,559):
  page=doc[pn-1];page_hashes[pn]=hashlib.sha256(page.get_text('text',sort=True).encode()).hexdigest();lines=[]
  for b in page.get_text('dict')['blocks']:
   if b['type']!=0:continue
   for l in b['lines']:
    text=''.join(s['text'] for s in l['spans']).strip()
    if text:lines.append({'page':pn,'text':text,'bbox':list(l['bbox'])})
  start=next(x['bbox'][1] for x in lines if x['text'].startswith('7.2 MATRIZ')) if pn==545 else 0
  end=next(x['bbox'][1] for x in lines if x['text'].startswith('7.3 OS ITINERÁRIOS')) if pn==558 else page.rect.height
  footer=[x for x in lines if x['text']==str(pn) and x['bbox'][1]>page.rect.height*.9];assert len(footer)==1;footers+=footer
  for line in lines:
   if line in footer:continue
   if line['bbox'][1]<start or line['bbox'][1]>=end:excluded.append(line);continue
   all_lines.append(line);t=line['text']
   if t.startswith('ÁREA DE ') or t=='FORMAÇÃO TÉCNICA E PROFISSIONAL':groups.append(line)
   if t.startswith('EIXO ESTRUTURANTE:'):axes.append(line)
   for match in re.finditer(r'EMIF(?:CG|LGG|CHSA|MAT|CNT|FTP)\d{2}',t):codes.append({**line,'code':match.group(),'column':'general' if line['bbox'][0]<300 else 'specific'})
  if pn in [546,549,551,554,557]:
   code=next(x for x in lines if '(EMIFCG06)' in x['text']);box=pymupdf.Rect(45,code['bbox'][1]-8,300,min(code['bbox'][1]+92,page.rect.height-45));page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=box).save(O/f'primary-cg06-{pn}.png');cg06.append({'page':pn,'bbox':list(box),'literal_end':'soluções por meio de difere','crop':f'primary-cg06-{pn}.png'})
  if pn in [545,550,551,552,553,558]:page.get_pixmap(matrix=pymupdf.Matrix(.75,.75)).save(O/f'primary-page-{pn}.png')
 counts=collections.Counter(x['code'] for x in codes);prefix=collections.Counter(re.match(r'EMIF([A-Z]+)',x['code']).group(1) for x in codes)
 assert len(codes)==120 and len(counts)==72,(len(codes),len(counts));assert prefix=={'CG':60,'LGG':12,'CHSA':12,'MAT':12,'CNT':12,'FTP':12},prefix
 assert len(axes)==20,(len(axes),axes)
 assert all(counts[f'EMIFCG{i:02}']==5 for i in range(1,13))
 rows={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:rn-primary-peer','artifact_path':str(p.relative_to(R)),'artifact_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_id':SID,'pdf_pages':570,'audited_range':[545,558],'method':'Read every original native page545–558 and independently count physical code occurrences and columns before opening sidecar/author ledger. Task-provided expected counts were known; review is not blind.','scope_boundaries':{'start':'7.2 MATRIZ DAS HABILIDADES DOS ITINERÁRIOS FORMATIVOS','end_exclusive':'7.3 OS ITINERÁRIOS FORMATIVOS E A PRÁTICA PEDAGÓGICA','outside_lines':excluded},'physical_code_occurrences':len(codes),'unique_printed_codes':len(counts),'code_prefix_occurrences':dict(prefix),'occurrence_count_is_not_unique_national_learning_count':True,'source_group_count':5,'group_types':['Linguagens','Ciências Humanas e Sociais Aplicadas','Matemática','Ciências da Natureza','Formação Técnica e Profissional'],'axis_groups':20,'two_skill_columns':True,'body_lines_in_scope':len(all_lines),'footer_markers':footers,'source_group_heading_occurrences':groups,'axis_heading_occurrences':axes,'code_occurrences':codes,'all_scope_lines':all_lines,'page_sortTrue_sha256':page_hashes,'expected_documentary_nodes_from_primary_structure':{'section':1,'groups':5,'axes':20,'skills':120,'total':146},'continuation_cases':['MAT CG01 code-only550→text551','MAT01 code-only550→text551','MAT CG10 552→553','MAT10 552→553','LGG02 545→546','LGG06 546→547','LGG CG11 547→548','LGG11 547→548','CHSA08 549→550','CNT03 553→554','CNT08 554→555'],'cg06_source_truncation_requires_visual_check':cg06,'scope_limit':'This14page7.2census does not reconcile entire570page source/FGB nor RN UF; no hidden national completion of source text is allowed.'}
 (O/'primary-census.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'body_lines':len(all_lines),'codes':len(codes),'unique':len(counts),'axes':len(axes),'footers':len(footers),'outside_lines':len(excluded)}))
