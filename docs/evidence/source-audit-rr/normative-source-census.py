"""Source-only native census; image logos/table detections are not curriculum coverage."""
from pathlib import Path
import fitz,json,re,hashlib
ROOT=Path(__file__).resolve().parents[3];sources=json.loads((ROOT/'data/manifests/north.json').read_text());rows=[]
for sid in ['rr-matrizes-32-2025','rr-integral-38-2025']:
 s=next(s for s in sources if s['id']==sid);p=ROOT/s['local_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'];D=fitz.open(p);pages=[];arts=[];annexes=[];cells=0
 for pn,page in enumerate(D,1):
  text=page.get_text('text');articles=re.findall(r'(?m)^Art\.\s*(\d+)',text);arts.extend(int(a)for a in articles);heads=[]
  for b in page.get_text('dict')['blocks']:
   for line in b.get('lines',[]):
    t=''.join(z['text']for z in line['spans']).strip()
    if t.startswith(('ANEXO','MATRIZ CURRICULAR','DESCRIÇÕES E ORIENTAÇÕES')):heads.append({'source_id':sid,'page':pn,'excerpt':t,'bbox':list(line['bbox'])})
  annexes.extend(z for z in heads if z['excerpt'].startswith('ANEXO'))
  tables=[]
  # Res38is a prose act; frame detections are not curricular matrices.
  if sid=='rr-matrizes-32-2025'and pn>1:
   for ti,t in enumerate(page.find_tables().tables):
    seen=set();nonempty=[]
    for ri,(row,raw)in enumerate(zip(t.rows,t.extract())):
     for ci,(bbox,tx)in enumerate(zip(row.cells,raw)):
      if not bbox or not tx or not tx.strip():continue
      key=tuple(round(x,3)for x in bbox)
      if key in seen:continue
      seen.add(key);nonempty.append({'row':ri,'column':ci,'bbox':list(bbox),'native_character_count':len(tx),'native_text_sha256':hashlib.sha256(tx.encode()).hexdigest()})
    tables.append({'physical_table_index':ti,'bbox':list(t.bbox),'rows':t.row_count,'columns':t.col_count,'nonempty_unique_cells':len(nonempty),'cell_inventory':nonempty});cells+=len(nonempty)
  pages.append({'page':pn,'native_characters':len(text),'articles':articles,'headers':heads,'tables':tables,'embedded_images':[{'xref':i[0],'width':i[2],'height':i[3],'rectangles':[list(r)for r in page.get_image_rects(i[0])]}for i in page.get_images(full=True)]})
 row={'source_id':sid,'artifact_sha256':s['sha256'],'pages':len(D),'parser_repaired':D.is_repaired,'article_numbers_literal':arts,'native_matrix_table_fragments':sum(len(p['tables'])for p in pages),'nonempty_native_matrix_cells':cells,'literal_annex_titles':annexes,'page_census':pages,'structured_adapter_completed':False,'independent_primary_readback':'pending','coverage_claimed':False}
 proof_path=ROOT/'docs/evidence/source-audit-rr/rr-integral-38-2025-visual-readback-20261101.json'
 if sid=='rr-integral-38-2025'and proof_path.is_file():
  proof=json.loads(proof_path.read_text());assert proof['source_artifact_sha256']==s['sha256'];assert proof['physical_page_count']==len(D);assert proof['page_census_comparison']['census_native_character_counts_match_all_pages'];assert proof['page_census_comparison']['article_start_boundaries_match_all_pages'];assert proof['page_census_comparison']['printed_page_numbers_match_physical_pages'];assert proof['page_census_comparison']['candidate_page_text_matches_sorted_source_after_nfkc_whitespace_normalization']
  row['independent_primary_readback']='verified_source_text_pagination_and_article_boundaries'
  row['independent_primary_readback_proof_path']=str(proof_path.relative_to(ROOT))
  row['independent_primary_readback_proof_sha256']=hashlib.sha256(proof_path.read_bytes()).hexdigest()
 rows.append(row)
report={'actor_type':'automated','method':'Source-only native text and physical cell census derived directly from the official PDFs. The independent primary-readback proof is a separate follow-up that compares the current candidate page text with native PDF text only after the source census is computed. Matrix frame fragments are not standalone complete matrices; images require role inspection, not automatic OCR assumptions.','sources':rows};(ROOT/'docs/evidence/source-audit-rr/normative-source-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:r[k]for k in ['source_id','pages','article_numbers_literal','native_matrix_table_fragments','nonempty_native_matrix_cells']}for r in rows]))
