#!/usr/bin/env python3
"""Extract uncoded HABILIDADE cells in all PR Volume 2 physical occurrences.
Table cell geometry is the denominator, not produced records. No explanations or
examples become objectives. Repeated cells are deduplicated by physical locator.
"""
from pathlib import Path
import fitz,json,re,hashlib,collections
ROOT=Path(__file__).resolve().parents[3];SID='pr-referencial-eief-2025';REV='pr-digital-skill-cells-v1.0.0';OUT=ROOT/'docs/evidence/source-audit-pr'
def norm(s):return re.sub(r'\s+',' ',s).strip()
def ident(pn,loc):return 'ca:'+SID+':'+hashlib.sha256(f'{SID}|{pn}|{loc}|uncoded|occurrence:0'.encode()).hexdigest()[:20]
def save(n,x):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def extract():
 s=next(s for s in json.loads((ROOT/'data/manifests/central-south.json').read_text()) if s['id']==SID);d=fitz.open(ROOT/s['local_path']);items=[];inventory=[]
 for pn,p in enumerate(d,1):
  if pn<904 or 'EXPLICAÇÃO DA HABILIDADE' not in p.get_text():continue
  if p.rotation:p.remove_rotation()
  tabs=p.find_tables();words=p.get_text('words')
  for tab in tabs.tables:
   grid=tab.extract();hi=next((i for i,row in enumerate(grid) if any(c and norm(c) in ['HABILIDADE','HABILIDADES'] for c in row)),None)
   if hi is None:continue
   ci=next(i for i,c in enumerate(grid[hi]) if c and norm(c) in ['HABILIDADE','HABILIDADES'])
   title=next(norm(c) for row in grid[:hi] for c in row if c and 'ENSINO FUNDAMENTAL' in c)
   ypart=title.split('–')[0].split('-')[-1];nums=list(map(int,re.findall(r'\d+',ypart)));years=list(range(nums[0],nums[-1]+1)) if 'AO' in ypart else nums
   pos={'stage':'EF','component':'Educação Digital','area':'Educação Digital e Computação','years':years,'year_label':ypart.strip(),'age_group':None,'period':None,'position_origin':'explicit_source_column_header'}
   cells={tuple(row.cells[ci]) for row in tab.rows[hi+1:] if row.cells[ci]}
   uncode=0
   for cell in sorted(cells,key=lambda c:(c[1],c[0])):
    ws=[w for w in words if cell[0]<(w[0]+w[2])/2<cell[2] and cell[1]<(w[1]+w[3])/2<cell[3]];text=norm(' '.join(w[4] for w in ws))
    if not text or re.search(r'(?:EI|EF)\d{2}[A-Z]{2}\d{2}',text):continue
    if text in ['HABILIDADE','HABILIDADES']:continue
    loc='pr-digital-skill-cell:'+','.join(str(round(v*10)) for v in cell);itemid=ident(pn,loc)
    bb=[min(w[0] for w in ws),min(w[1] for w in ws),max(w[2] for w in ws),max(w[3] for w in ws)]
    other=[w for w in words if cell[2]<(w[0]+w[2])/2<(tab.rows[hi].cells[ci][2] or cell[2]) and cell[1]<(w[1]+w[3])/2<cell[3]]
    refs=list(dict.fromkeys(re.findall(r'EF\d{2}CO\d{2}',' '.join(w[4] for w in other))))
    ev={'source_id':SID,'page':pn,'printed_page':str(pn-(904 if pn<966 else 966)),'section':title,'excerpt':text,'locator':loc,'bbox':bb,'coordinate_space':'page display coordinates after remove_rotation','method':REV}
    items.append({'id':itemid,'source_id':SID,'artifact_sha256':s['sha256'],'code':None,'kind':'habilidade_local_sem_codigo','text':text,'page':pn,'locator':loc,'positions':[pos],'evidence':[ev],'source_context':{'document_part':'Volume 2','hierarchy':['EF','Educação Digital',pos['year_label']],'cell_bbox':list(cell),'official_code_absent':True,'reference_codes':refs,'reference_relationship':'agrupamento_documental_sem_equivalencia','classification_basis':'Célula sem código da subcoluna esquerda HABILIDADE; excluídas EXPLICAÇÃO DA HABILIDADE e EXEMPLOS.'},'extraction_method':REV,'extraction_revision':REV,'actor_type':'automated','actor_id':'agent:pr_adapter','technical_validation_status':'source_skill_cell_and_words_checked','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate'});uncode+=1
   inventory.append({'page':pn,'title':title,'table_bbox':list(tab.bbox),'columns':tab.col_count,'raw_skill_cells':len(cells),'uncoded_skill_cell_denominator':uncode,'expected_item_ids':[ident(pn,'pr-digital-skill-cell:'+','.join(str(round(v*10)) for v in c)) for c in sorted(cells,key=lambda c:(c[1],c[0])) if (tt:=norm(' '.join(w[4] for w in words if c[0]<(w[0]+w[2])/2<c[2] and c[1]<(w[1]+w[3])/2<c[3]))) and not re.search(r'(?:EI|EF)\d{2}[A-Z]{2}\d{2}',tt) and tt not in ['HABILIDADE','HABILIDADES']]})
 (ROOT/'data/manifests/uncoded/pr-digital-items.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n');save('pr-digital-cell-denominator.json',{'source_id':SID,'artifact_sha256':s['sha256'],'actor_type':'automated','method':'Full table-grid skill-cell inventory, code presence evaluated before records','tables':inventory,'expected_item_ids':[eid for r in inventory for eid in r['expected_item_ids']],'verified_item_ids':[i['id'] for i in items]});print('digital items',len(items),'tables',len(inventory));return items
if __name__=='__main__':extract()
