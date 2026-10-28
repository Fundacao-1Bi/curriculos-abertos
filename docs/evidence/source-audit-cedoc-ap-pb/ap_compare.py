from pathlib import Path
import pymupdf as f,json,hashlib,re,difflib,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
IMAGES=ROOT/'var/private-evidence/source-audit-cedoc-ap-pb';IMAGES.mkdir(parents=True,exist_ok=True)
paths=['data/raw/AP/ap-native-ei-ef.pdf','data/raw/AP/ap-rca-ei-ef-cedoc.pdf'];data=[(ROOT/p).read_bytes() for p in paths];docs=[f.open(ROOT/p) for p in paths];assert len(docs[0])==len(docs[1])==614
start=next(i for i,(a,b) in enumerate(zip(*data)) if a!=b);changes=[]
for tag,a,b,c,d in difflib.SequenceMatcher(None,data[0][start-100:],data[1][start-100:],autojunk=False).get_opcodes():
 if tag!='equal':changes.append({'op':tag,'mec_offset':[start-100+a,start-100+b],'cedoc_offset':[start-100+c,start-100+d],'mec_literal':data[0][start-100+a:start-100+b].decode(),'cedoc_literal':data[1][start-100+c:start-100+d].decode(),'mec_context':data[0][start-100+a-35:start-100+b+45].decode()})
page_checks=[]
for pn in range(1,615):
 pages=[doc[pn-1] for doc in docs];texts=[p.get_text() for p in pages];words=[p.get_text('words') for p in pages]
 # Equal page streams and literal positioned words establish content identity,
 # separately from the outer binary whose XMP namespace spelling differs.
 contents=[[hashlib.sha256(doc.xref_stream(x)).hexdigest() for x in p.get_contents()] for doc,p in zip(docs,pages)]
 check={'page':pn,'native_text_equal':texts[0]==texts[1],'word_geometry_equal':words[0]==words[1],'page_contents_streams_equal':contents[0]==contents[1],'page_dimensions_equal':pages[0].rect==pages[1].rect,'text_sha256':hashlib.sha256(texts[1].encode()).hexdigest(),'native_characters':len(texts[1])};page_checks.append(check)
 assert all(check[k] for k in ['native_text_equal','word_geometry_equal','page_contents_streams_equal','page_dimensions_equal']),check
samples=[]
for pn in [1,2,6,33,80,154,240,330,500,614]:
 pix=[doc[pn-1].get_pixmap(matrix=f.Matrix(.8,.8),alpha=False) for doc in docs];hs=[hashlib.sha256(p.samples).hexdigest() for p in pix];assert hs[0]==hs[1]
 path=IMAGES/f'ap-cedoc-page-{pn:03d}.png';pix[1].save(path);samples.append({'page':pn,'pixel_sha256_mec':hs[0],'pixel_sha256_cedoc':hs[1],'pixel_equal':True,'image_path':str(path.relative_to(ROOT)),'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'visually_reviewed':False})
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_files':[{'path':p,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'parser_is_repaired':doc.is_repaired} for p,b,doc in zip(paths,data,docs)],'pages':614,'binary_differences':changes,'binary_interpretation':'Five s characters present in https XML namespace URLs in MEC XMP and absent in CEDOC http namespace URLs. No other byte differences. Both original binaries preserved unchanged.','page_checks':page_checks,'all_page_text_geometry_content_streams_match':True,'visual_render_samples':samples,'relationship':'same_614_page_document_content_with_different_XMP_namespace_bytes_not_a_new_curriculum_edition','edition_vigency':'Catalog2020 claim is not documentary enactment; internal PDF metadata2018 is technical provenance only; relation to339pageapproved2019document still unreconciled.','status':'passed_content_identity_not_completeness'}
(OUT/'ap-614-mec-cedoc-comparison.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ['page_checks','visual_render_samples','binary_differences']})
