#!/usr/bin/env python3
"""Rebuild a chapter-scope proposal from independently checked original images.
No learning extraction, manifest mutation, or automatic year attribution.
"""
from pathlib import Path
import json,hashlib
import fitz
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
IMAGES=ROOT/'var/private-evidence/source-audit-am-sections'
PDF=ROOT/'data/raw/AM/am-rca-ef-ai.pdf'
SOURCE='am-rca-ef-ai'
SHA='38d9b9c5bf7534f48d9f5182fd9b43bc07555f56944eca2eaa11a9e120f82508'
assert hashlib.sha256(PDF.read_bytes()).hexdigest()==SHA
D=fitz.open(PDF); assert len(D)==670
ocr=json.loads((OUT/'ai-boundary-ocr.json').read_text())+json.loads((OUT/'ai-trailing-pages-ocr.json').read_text())
by={o.get('page_number',o.get('page')):o for o in ocr}
# Actual transcriptions from original images, including TOC typography.
chapters=[
 ('lp','Língua Portuguesa','Língua Portuguesa',110,344,16,421,'LÍNGUA PORTUGUESA'),
 ('arte','Arte','Arte',345,397,17,446,'ARTE'),
 ('educacao-fisica','Educação Física','Educação Física',398,460,19,472,'EDUCAÇÃO FÍSICA'),
 ('lingua-inglesa','Língua Inglesa','Língua Inglesa',461,488,20,497,'COMPONENTE CURRICULAR - LÍNGUA INGLESA'),
 ('lingua-espanhola','Língua espanhola','Língua Espanhola',489,515,21,522,'LÍNGUA ESPANHOLA'),
 ('matematica','Matemática','Matemática',516,556,22,547,'MATEMÁTICA'),
 ('ciencias','Ciências da Natureza','Ciências',557,588,23,572,'CIÊNCIAS DA NATUREZA'),
 ('geografia','Geografia','Geografia',590,615,25,622,'GEOGRAFIA'),
 ('historia','História','História',616,641,26,647,'HISTÓRIA'),
 ('ensino-religioso','Ensino Religioso','Ensino Religioso',642,656,27,672,'ENSINO RELIGIOSO'),
]
def rel(p):return str(p.relative_to(ROOT))
def transform_box(box,m):
 pts=[fitz.Point(x,y)*fitz.Matrix(m) for x,y in [(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])]]
 return [round(min(p.x for p in pts),2),round(min(p.y for p in pts),2),round(max(p.x for p in pts),2),round(max(p.y for p in pts),2)]
def ev(page,excerpt,box,role,image=None,layout=False,manual90=False,printed=True):
 box=list(box);extra={}
 if layout:
  m=[0,-1,1,0,0,842] if manual90 else by[page]['layout_to_original']
  extra={'layout_bbox':box,'layout_to_original':m}
  box=transform_box(box,m)
 r=D[page-1].rect
 box=[max(0,box[0]),max(0,box[1]),min(r.width,box[2]),min(r.height,box[3])]
 assert 0<=box[0]<box[2]<=r.width and 0<=box[1]<box[3]<=r.height,(page,box,r)
 image=image or IMAGES/f'ai-page-{page:03}-original.png'
 return {'source_id':SOURCE,'page':page,'printed_page':str(page-2) if printed else None,'excerpt':excerpt,'bbox':[round(v,2) for v in box],'coordinate_space':'original_pdf_page','bbox_precision':'visual_region_envelope','evidence_role':role,'method':'automated_agent_original_image_visual_check','human_pedagogical_review':False,'image_path':rel(image),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),**extra}
def title_box(page):
 im=Image.open(IMAGES/f'ai-page-{page:03}-layout.png').convert('RGB'); w,h=im.size;r=D[page-1].rect;sx=w/r.width;sy=h/r.height
 pts=[]
 for y in range(int(75*sy),int(170*sy)):
  for x in range(int(20*sx),int(560*sx)):
   red,g,b=im.getpixel((x,y))
   if red>170 and g>135 and b<145 and red>b*1.3 and g>b*1.2:pts.append((x/sx,y/sy))
 assert pts,page
 return [min(x for x,y in pts)-2,min(y for x,y in pts)-2,max(x for x,y in pts)+2,max(y for x,y in pts)+2]
def folio(page):
 o=by[page];words=[w for w in o['words'] if w['text']==str(page-2)]
 if words:
  w=words[-1];return ev(page,str(page-2),[w['x0']-2,w['top']-2,w['x1']+2,w['bottom']+2],'printed_folio')
 boxes={460:[75,65,105,81],488:[81,100,105,114],588:[70,43,100,59],668:[480,780,540,825]}
 assert page in boxes,page
 image=IMAGES/f'ai-page-{page:03}-verified-upright.png' if page==488 else None
 return ev(page,str(page-2),boxes[page],'printed_folio',image=image,layout=page!=668,manual90=page==488)
def toc(chapter_num,title,page_printed,y):
 return ev(16,f'{chapter_num}. {title} ... {page_printed}',[95,y-4,555,y+14],'contents_entry',image=IMAGES/'ai-page-016.png',printed=False)
sections=[]
for slug,title,component,start,end,num,y,last_header in chapters:
 te=ev(start,title,title_box(start),'chapter_opening')
 toc_title='Matemátia' if num==22 else ('Língua Espanhola' if num==21 else title)
 proof=[toc(num,toc_title,start-2,y),te,folio(start),ev(end,last_header,[30,35,790,180],'last_component_table_header',image=IMAGES/'ai-page-488-verified-upright.png' if end==488 else None,layout=True,manual90=end==488),folio(end)]
 sections.append({'id':f'am-ai-{slug}-{start}-{end}','title':title,'stage':'EF','component':component,'area':None,'page_start':start,'page_end':end,'evidence':te,'scope_evidence':proof,'scope_method':'Declared chapter opening, matching TOC, last component table and next declared opening; physical pages, 1-based.','years_not_inferred':True})
areas=[(109,'Linguagens','COMPETÊNCIAS ESPECÍFICAS DE LINGUAGENS PARA O ENSINO FUNDAMENTAL',[330,355,1100,445],15,396),(589,'Ciências Humanas','COMPETÊNCIAS ESPECÍFICAS DE CIÊNCIAS HUMANAS PARA O ENSINO FUNDAMENTAL',[160,110,445,150],24,597)]
for page,area,title,box,num,y in areas:
 te=ev(page,title,box,'area_competence_heading')
 sections.append({'id':f'am-ai-area-{page}','title':title,'stage':'EF','component':None,'area':area,'page_start':page,'page_end':page,'evidence':te,'scope_evidence':[toc(num,'Competências específicas de Linguagens para o Ensino Fundamental' if page==109 else 'Competências Específicas de Ciências Humanas para o Ensino Fundamental',page-2,y),te,folio(page)],'years_not_inferred':True})
te=ev(657,'Referências',[375,118,527,149],'references_opening')
sections.append({'id':'am-ai-referencias-657-668','title':'Referências','stage':'EF','component':None,'area':None,'page_start':657,'page_end':668,'evidence':te,'scope_evidence':[toc(28,'Referências',655,697),te,folio(657),folio(668)],'content_role':'bibliographic_references_not_learning_items','years_not_inferred':True})
sections.sort(key=lambda s:s['page_start'])
for a,b in zip(sections,sections[1:]): assert a['page_end']<b['page_start']
assert sum(s['page_end']-s['page_start']+1 for s in sections if s['component'])==546
proposal={'source_id':SOURCE,'artifact_path':rel(PDF),'artifact_sha256':SHA,'document_pages':len(D),'page_convention':'physical PDF pages, 1-based; printed folios independently verified on each component opening and closing','structure_sections':sections,'position_contexts':[],'integration_notes':[
'Apply structure_sections for component context. Do not apply broad chapter position_contexts: the current finalizer writes missing year fields as null and can erase a year detected in a table header.',
'No chapter-wide year or year range was inferred from codes or the final 5º ano table. Per-table year detection remains separate.',
'TOC page16 has no visible printed folio. Protocol stamps are not folios. The source jumps from chapter17 to19; no chapter18 was invented.',
'TOC Matemátia typo is preserved only in its evidence; the actual component opening says Matemática.',
'Ciências da Natureza is the literal chapter heading; canonical Ciências is additionally stated in the narrative on page557.',
'Physical109 has native PDF dimensions1413×2000; do not assume A4 geometry.',
'Physical488 is visually rotated90 degrees although the existing OCR cache says rotation0. A separate correctly rotated proof image is supplied; the shared cache was not changed.',
'Physical669 is blank apart from a protocol stamp and670 is a decorative backcover. They are excluded from references and component scopes.'
],'verification':{'actor_type':'automated_agent','human_pedagogical_review':False,'component_chapters':10,'component_pages':546,'area_competence_pages':2,'references_pages':12,'all_component_openings_and_closings_visually_checked':True,'source_sha_verified':True,'json_scope_nonoverlap_verified':True,'does_not_claim_item_extraction_or_UF_acceptance':True}}
(OUT/'ai-structure-sections-proposal.json').write_text(json.dumps(proposal,ensure_ascii=False,indent=2)+'\n')
reviewed=sorted({15,16,109,110,344,345,397,398,460,461,488,489,515,516,556,557,588,589,590,615,616,641,642,656,657,668,669,670})
review={'source_id':SOURCE,'artifact_sha256':SHA,'actor_type':'automated_agent','human_pedagogical_review':False,'reviewed_physical_pages':reviewed,'original_images_visually_checked':True,'page_geometry':{str(n):list(D[n-1].rect) for n in reviewed},'special_pages':[{'page':488,'issue':'Shared OCR cache orientation0 conflicts with visually established90-degree table orientation','corrected_proof':rel(IMAGES/'ai-page-488-verified-upright.png'),'printed_page':'486','cache_mutated':False},{'page':669,'classification':'blank_except_protocol_stamp','printed_page':None},{'page':670,'classification':'decorative_backcover','printed_page':None}],'scope_tests':{'component_sections':10,'component_pages':546,'nonoverlapping':True,'years_assigned':0,'main_evidence_is_object':all(isinstance(s['evidence'],dict) for s in sections)}}
(OUT/'ai-verified-boundaries.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sections':len(sections),'component_sections':10,'component_pages':546,'reviewed_pages':len(reviewed),'proposal_sha256':hashlib.sha256((OUT/'ai-structure-sections-proposal.json').read_bytes()).hexdigest()},ensure_ascii=False))
