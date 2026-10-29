"""Independent original-PDF census, before candidate/author output inspection."""
import collections,datetime,hashlib,json,pathlib,re,sys
import fitz
R=pathlib.Path.cwd();O=pathlib.Path(__file__).resolve().parent
SID='pi-computacao-em-2025';PDF=R/'data/raw/PI/pi-computacao-em.pdf';SHA='e6eda1fbcf82e4fb5554ce121ec3b6c1bdf13c9345ef716658c0946a1a71e61f'
PAGES=[51,52,55,59,61,63,67,69,71,75,79,81,84,86,91,93,96,97,99,100,102,104,107,108,109,111,116,123]
assert hashlib.sha256(PDF.read_bytes()).hexdigest()==SHA
sys.path.insert(0,str(R/'pipeline'));from geometry import normalize_native_page
records=[];original=[]
with fitz.open(PDF) as doc:
 for n in PAGES:
  p=doc[n-1];normalize_native_page(p)
  lines=[]
  for b in p.get_text('dict',sort=True)['blocks']:
   for l in b.get('lines',[]):
    bbox=l['bbox'];x=(bbox[0]+bbox[2])/2;y=(bbox[1]+bbox[3])/2
    text=''.join(s['text'] for s in l['spans']).strip()
    if text and 40<=x<=805 and 40<=y<=555:lines.append({'bbox':list(bbox),'text':text})
  # Source is single-column narrative on this scope. Keep physical order and repeated citations.
  lines.sort(key=lambda l:(round(l['bbox'][1],1),l['bbox'][0]))
  full='\n'.join(l['text'] for l in lines)
  codes=[]
  for li,l in enumerate(lines):
   for m in re.finditer(r'EM13(?:CO|LGG|CHS|MAT|CNT|LP)\d{2,3}',l['text']):codes.append({'code':m.group(),'line':li,'bbox':l['bbox'],'role':'citation_in_commentary_not_new_skill_definition'})
  origin=None
  for prior in range(n-1,0,-1):
   txt=doc[prior-1].get_text(sort=True)
   if 'RELAÇÃO ENTRE AS HABILIDADES' in txt:origin={'pdf_page':prior,'heading':'RELAÇÃO ENTRE AS HABILIDADES','continued_on_this_page':True};break
  records.append({'page':n,'printed_page':n-1,'scope_bbox':[40,40,805,555],'role':'narrative_explanation_or_activity_commentary','body_lines':lines,'body_text_sha256':hashlib.sha256(full.encode()).hexdigest(),'citations':codes,'previous_relation_heading':origin,'standalone_learning_definition_claim':False})
  original.append(f'\n=== PAGE {n} ===\n'+full)
 for n in [51,77,116,128,136]:doc[n-1].get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(O/f'primary-page-{n}.png')
 exclusions=[{'page':77,'observed':'Commentary-only page headed RELAÇÃO ENTRE AS HABILIDADES; excluded by requested scope. This is NOT a mixed definition/commentary table on the original PDF.','preservation_required':True},{'page':128,'observed':'Mixed two-column skill-definition matrix followed by RELAÇÃO ENTRE AS HABILIDADES commentary; excluded.','preservation_required':True},{'page':136,'observed':'Competency paragraph plus mixed two-column skill-definition matrix followed by RELAÇÃO ENTRE AS HABILIDADES commentary; excluded.','preservation_required':True}]
 out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','source_id':SID,'artifact_path':str(PDF.relative_to(R)),'artifact_sha256':SHA,'artifact_bytes':PDF.stat().st_size,'source_pages':len(doc),'candidate_not_opened':True,'scope_pages':PAGES,'denominators':{'selected_narrative_pages':len(PAGES),'body_native_lines':sum(len(r['body_lines']) for r in records),'code_citation_occurrences':sum(len(r['citations']) for r in records),'unique_cited_codes':len(set(c['code'] for r in records for c in r['citations'])),'new_learning_definitions_in_this_scope':0},'pages':records,'excluded_pages':exclusions,'scope_limits':['These are narrative references/explanations and examples of proposed activities; references to skills are not republished as new canonical skill definitions.','Page116 has a contribution-to-relation comparison table, not a HABILIDADES matrix.','Single-page records must retain full body prose and repeated citations; code tokens alone are not the narrative text.','137-page SourceWhole and other mixed/definition pages are not reconciled by this census.']}
 (O/'primary-census.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(O/'primary-body.txt').write_text(''.join(original))
 print(json.dumps(out['denominators']));print('primary_census_sha256',hashlib.sha256((O/'primary-census.json').read_bytes()).hexdigest())
