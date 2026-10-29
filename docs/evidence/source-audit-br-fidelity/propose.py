#!/usr/bin/env python3
"""394 record-by-record proposals, checked by the unchanged pipeline literal checker."""
import collections,copy,datetime,hashlib,json,re,sys
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline'));sys.path.insert(0,str(OUT))
from ingest import evidence_check
from analyze import norm,primary_proof,trace_text,digest,rounded
from ms_glyphs import rendered_glyph_text
CODE=re.compile(r'\((?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2,3}|EM\d{2}[A-Z]{2,3}\d{2,3})\)')
def compact(text):
 import unicodedata
 return re.sub(r'[\s\-\u00ad\u2010\u2011]','',unicodedata.normalize('NFKD',text).casefold())
def without_code(text,code):return re.sub(r'^\s*\('+re.escape(code)+r'\)\s*','',text).strip()
def tokens(text):
 import unicodedata
 return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',re.sub(r'\s+',' ',text)).casefold().encode('ascii','ignore').decode())
def main():
 baseline=json.loads((OUT/'baseline-records.json').read_text());inventory=json.loads((OUT/'native-inventory.json').read_text());analysis={r['id']:r for r in json.loads((OUT/'search-analysis.json').read_text())['records']};primary={s['source_id']:s for s in inventory['sources']};results=[];rendered=[]
 for group in baseline['sources']:
  sid=group['source_id'];source=group['source'];extracted=json.loads((ROOT/group['cache']).read_text());assert digest((ROOT/source['local_path']).read_bytes())==source['sha256']
  with fitz.open(ROOT/source['local_path']) as document:
   for item in group['records']:
    row=analysis[item['id']];number=item['evidence'][0]['page'];page=document[number-1];anchors=[a for a in row['native_code_anchors'] if a['page']==number];proposed=copy.deepcopy(item);proof=None;policy=None;status='unresolved';record_class='unresolved';box=None
    # The upstream page is authoritative here; exact duplicate examples on another page are explicitly recorded.
    exact=[p for p in row['proposals'] if p['page']==number and p['exact']]
    if len(exact)==1 and len(exact[0]['code_anchors'])==1:
     p=exact[0];box=fitz.Rect(p['bbox']);proof=p['proof'];anchor=p['code_anchors'][0];status='exact_native_cell_locator';record_class='layout_only'
    elif len(anchors)==1:
     anchor=anchors[0];block=next(block for block in page.get_text('blocks') if block[5]==anchor['block']);box=fitz.Rect(block[:4])+(-.7,-.7,.7,.7);proof=primary_proof(page,box,item['text']);status='exact_native_block_locator' if proof['native_exact'] else 'unresolved';record_class='layout_only'
    else:anchor=None
    evidence=[];raw_body=None;word_equal=None
    if box is not None and anchor is not None:
     raw_body=without_code(proof['rawdict_text'],item['code']);word_equal=tokens(raw_body)==tokens(item['text'])
     if status=='unresolved':
      traced=rendered_glyph_text(page,rounded(box))
      if norm(item['text']) in norm(traced):status='exact_rendered_glyph_locator';record_class='native_encoding_separator'
      elif compact(item['text']) in compact(proof['native_text']):
       status='documented_existing_typographic_policy';record_class='compound_hyphen_or_layout_whitespace';policy={'method':'primary_pdf_word_wrap_compound_hyphen_and_whitespace; existing literal-checker policy only','evidence':[{'source_id':sid,'artifact_sha256':source['sha256'],'page':number,'bbox':rounded(box),'source_excerpt':proof['rawdict_text'],'canonical_text_sha256':hashlib.sha256(item['text'].encode()).hexdigest(),'compact_source_sha256':hashlib.sha256(compact(proof['native_text']).encode()).hexdigest(),'scope':'Formatting only; no lexical substitution, code correction, or generic fuzzy matching.'}]}
      else:record_class='primary_licensed_typography_difference' if tokens(proof['rawdict_text'].replace('('+item['code']+')',''))==tokens(item['text']) else 'requires_lexical_review'
     code_box=fitz.Rect(anchor['bbox'])+(-.5,-.5,.5,.5)
     evidence=[{'source_id':sid,'page':number,'printed_page':None,'section':'Primary code glyph, isolated native word','excerpt':item['code'],'bbox':rounded(code_box),'locator':'primary-code-bbox:'+item['code'],'method':'pymupdf-native-code-bbox','evidence_role':'code_locator'}, {'source_id':sid,'page':number,'printed_page':None,'section':'Primary curriculum cell; licensed canonical text preserved','excerpt':item['text'],'bbox':rounded(box),'locator':'primary-text-cell-bbox:'+item['code'],'method':'pymupdf-rendered-glyph-trace-v1' if status=='exact_rendered_glyph_locator' else 'pymupdf-native-cell-bbox','evidence_role':'canonical_text'}]
     proposed['evidence']=evidence
     if policy:proposed['primary_typographic_equivalence']=policy
     passed=evidence_check(proposed,extracted,document)
     region=box|code_box;region=region+(-2,-2,2,2);pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=region,alpha=False);render_path=OUT/'renders'/('record-'+hashlib.sha256(item['id'].encode()).hexdigest()[:16]+'.png');pix.save(render_path);rendered.append({'id':item['id'],'source_id':sid,'page':number,'bbox':rounded(region),'path':str(render_path.relative_to(ROOT)),'png_sha256':hashlib.sha256(render_path.read_bytes()).hexdigest(),'width':pix.width,'height':pix.height})
    else:passed=False
    assert all(proposed.get(field)==item.get(field) for field in ['id','code','text','source_id','source_dataset','code_aliases','positions','parent_id'])
    # Canonical hashes are never rewritten; the proposal changes evidence and a documented formatting proof only.
    results.append({'id':item['id'],'source_id':sid,'source_sha256':source['sha256'],'code':item['code'],'canonical_text_sha256':hashlib.sha256(item['text'].encode()).hexdigest(),'upstream_locator_preserved':True,'old_evidence':item['evidence'],'proposed_evidence':evidence,'primary_typographic_equivalence':policy,'status':status,'classification':record_class,'strict_current_checker_passed':passed,'raw_primary_excerpt':raw_body,'native_proof':proof,'full_crop_word_tokens_equal':word_equal,'same_page_code_occurrences':len(anchors),'other_exact_example_pages':[p['page'] for p in row['proposals'] if p['exact'] and p['page']!=number],'immutable_fields_preserved':True})
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();report={'actor_type':'automated','actor_id':'codex-independent-br-fidelity-auditor','generated_at':stamp,'checker_sha256':hashlib.sha256((ROOT/'pipeline/ingest.py').read_bytes()).hexdigest(),'denominator':394,'checked':len(results),'strict_passed':sum(r['strict_current_checker_passed'] for r in results),'counts':dict(collections.Counter(r['status'] for r in results)),'classification_counts':dict(collections.Counter(r['classification'] for r in results)),'records':results,'publication_modified':False,'canonical_dataset_modified':False,'checker_modified':False,'source_attribution':'CC-BY-4.0 bncc-dev/bncc-dados, commit9c268978efa2aa250834c6a9edb6074432752838; primary official PDFs pinned by SHA256'}
 (OUT/'proposals.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(OUT/'render-inventory.json').write_text(json.dumps({'actor_type':'automated','generated_at':stamp,'count':len(rendered),'records':rendered},ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},ensure_ascii=False));print('NOT_PASSING',[(r['code'],r['status'],r['classification']) for r in results if not r['strict_current_checker_passed']])
if __name__=='__main__':main()
