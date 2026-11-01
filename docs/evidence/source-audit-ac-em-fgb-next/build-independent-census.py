from __future__ import annotations
import csv, hashlib, json, re
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PDF = ROOT / 'data/raw/AC/ac-cru-em.pdf'
EXPECTED_SHA = '9ff75d1d5d9397aa145dccedd8023a01ed3b862692f58bb7d2cb2c84fc7602ad'
CODE_RE = re.compile(r'\b(EM13[A-Z]{2,5}\d{2,3})\b')
ORG_RE = re.compile(r'QUADRO ORGANIZADOR DE (.+?)\s*[–-]\s*([123])ª SÉRIE', re.I)

def page_lines(page):
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            yield line, ''.join(span['text'] for span in line['spans']).strip()

sha = hashlib.sha256(PDF.read_bytes()).hexdigest()
if sha != EXPECTED_SHA:
    raise SystemExit(f'PDF identity changed: {sha}')
doc = fitz.open(PDF)
if len(doc) != 459:
    raise SystemExit(f'PDF page count changed: {len(doc)}')

orgs=[]
for pno in range(121, 385):
    for line, text in page_lines(doc[pno-1]):
        m=ORG_RE.search(text)
        if m:
            orgs.append({'page':pno,'y':round(line['bbox'][1],3),'title':text,
                         'area':m.group(1).strip(),'year':int(m.group(2))})
if len(orgs) != 10:
    raise SystemExit(f'Expected 10 explicit organizer headings in FGB region, found {len(orgs)}')
orgs.sort(key=lambda x:(x['page'],x['y']))

# Independently assign each code occurrence to the most recent explicit organizer
# heading by physical page and vertical position; codes outside pp.122-384 excluded.
occ=[]
for pno in range(122,385):
    for line, text in page_lines(doc[pno-1]):
        for match in CODE_RE.finditer(text):
            y=round(line['bbox'][1],3)
            candidates=[o for o in orgs if (o['page'],o['y']) <= (pno,y)]
            if not candidates:
                continue
            org=candidates[-1]
            occ.append({'physical_page':pno,'y':y,'code':match.group(1),
                        'organizer_title':org['title'],'organizer_page':org['page'],
                        'area':org['area'],'year':org['year'],
                        'role_status':'skill_code_anchor_only; full skill/object relation unresolved'})

# Cross-check scope marks from native text, retaining headings and recurring table columns.
page_heading_counts={}
for pno in range(122,385):
    txt=doc[pno-1].get_text('text',sort=True)
    page_heading_counts[str(pno)]={
        'has_habilidade_heading':'HABILIDADE' in txt,
        'has_objetos_heading':'OBJETOS DE CONHECIMENTO' in txt,
        'has_propostas_heading':'PROPOSTAS DE ATIVIDADES' in txt,
        'has_common_area_activity_heading':'PROPOSTAS DE ATIVIDADES (COMUM À ÁREA)' in txt,
    }
summary=[]
for ix,o in enumerate(orgs):
    start=(o['page'],o['y'])
    end=(orgs[ix+1]['page'],orgs[ix+1]['y']) if ix+1<len(orgs) else (385,0)
    assigned=[x for x in occ if (o['page'],o['y']) <= (x['physical_page'],x['y']) < end]
    summary.append({'organizer_title':o['title'],'anchor_page':o['page'],'anchor_y':o['y'],
      'next_organizer_anchor':{'page':end[0],'y':end[1]},'explicit_area':o['area'],'explicit_year':o['year'],
      'assigned_code_occurrences':len(assigned),'distinct_codes':len({x['code'] for x in assigned}),
      'pages_with_skill_anchors':sorted({x['physical_page'] for x in assigned})})

result={'source_id':'ac-cru-em','pdf':'data/raw/AC/ac-cru-em.pdf','pdf_sha256':sha,
 'physical_page_count':len(doc),'audited_item_span_inclusive':[122,384],
 'scope_start_context':'explicit FGB organizer begins on physical p.121; first coded item appears p.122',
 'scope_end_context':'next normative part heading ITINERÁRIOS FORMATIVOS occurs on p.385; span ends at p.384',
 'organizer_denominator_method':'direct native-PDF title-line census; each code token assigned to latest preceding explicit QUADRO ORGANIZADOR ... Nª SÉRIE anchor by page and y coordinate',
 'organizer_count':len(orgs),'code_occurrence_count':len(occ),'distinct_code_count':len({x['code'] for x in occ}),
 'organizers':summary,'independent_roles_closed':False,
 'role_blocker':'Code anchors establish occurrence denominator, but the PDF does not yield a closed, auditable row-to-column/object/competence mapping from headings alone; cross-page continuations, full-width panels, objects/proposals/activity blocks and specific-competence prose require role decisions and visual verification.',
 'native_page_heading_inventory':page_heading_counts}
(OUT/'independent-census.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
with (OUT/'pending-role-inventory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['physical_page','y','code','organizer_title','organizer_page','area','year','role_status','full_skill_text_role','component_column_role','object_column_role','activity_or_method_role','competence_definition_role'])
    w.writeheader()
    for row in occ:
        row.update({'full_skill_text_role':'pending row-to-column binding','component_column_role':'pending cell/continuation census','object_column_role':'pending object-vs-proposal/continuation classification','activity_or_method_role':'pending contextual-only boundary review','competence_definition_role':'pending full prose inventory; do not count heading number as definition'})
        w.writerow(row)
print(json.dumps({'output':str(OUT),'pdf_sha256':sha,'pages':len(doc),'organizer_count':len(orgs),
 'code_occurrences':len(occ),'distinct_codes':len({x['code'] for x in occ}),
 'organizers':[{k:x[k] for k in ['organizer_title','assigned_code_occurrences','distinct_codes']} for x in summary]},ensure_ascii=False))
