#!/usr/bin/env python3
"""Independent physical table/cell denominator, still before sidecar construction."""
import collections,datetime,gzip,hashlib,json,re
from pathlib import Path
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
def sha(value):return hashlib.sha256(value).hexdigest()
def main():
 census=json.loads((OUT/'physical-census.json').read_text());output=[]
 for source in census['sources']:
  assert sha((ROOT/source['artifact']).read_bytes())==source['artifact_sha256'];native=json.loads(gzip.decompress((ROOT/source['private_census']).read_bytes()));record={'source_id':source['source_id'],'artifact_sha256':source['artifact_sha256'],'tables':[],'page_contexts':[]}
  with fitz.open(ROOT/source['artifact'])as doc:
   for p,raw in zip(doc,native['pages']):
    page=raw['page'];plain='\n'.join(r['text']for r in raw['lines']);headers=[{'line_id':r['id'],'text':r['text'],'bbox':r['bbox']}for r in raw['lines']if re.search(r'(?i)(?:\b(?:[1-3][ªaºo]?\s*S[ée]rie|S[ée]rie\s*[1-3][ªaºo]?)|ensino\s+m[ée]dio|compet[êe]ncias?\s+(?:espec[íi]ficas?|gerais)|descri[çc][ãa]o\s+da\s+compet[êe]ncia|tabela\s+\d|ensino\s+fundamental)',r['text'])];record['page_contexts'].append({'page':page,'headers':headers})
    if not re.search(r'(?i)(?:compet[êe]ncia|habilidades?|objeto[\s\n]+de[\s\n]+conhecimento|\bEM\d{2}|unidade[\s\n]+tem[áa]tica)',plain):continue
    for ti,t in enumerate(p.find_tables(strategy='lines_strict').tables):
     seen=set();cells=[]
     for ri,row in enumerate(t.rows):
      for ci,bounds in enumerate(row.cells):
       if bounds is None or tuple(bounds)in seen:continue
       seen.add(tuple(bounds));box=fitz.Rect(bounds);words=[(wi,w)for wi,w in enumerate(raw['words'])if box.contains(fitz.Point((w[0]+w[2])/2,(w[1]+w[3])/2))];text=' '.join(w[4]for wi,w in words)
       if not text.strip():continue
       codes=re.findall(r'(?<![A-Z0-9])EM\d{2}[A-Z]{2,3}\d{2,3}(?:[-/][A-Za-z0-9]+)*(?![A-Z0-9])',text);cells.append({'row':ri,'column':ci,'bbox':list(bounds),'native_word_indices':[wi for wi,w in words],'text':text,'text_sha256':sha(text.encode()),'printed_skill_codes':codes,'literal_competency_number_candidates':re.findall(r'(?:\[?CE\s*0?\d\]?|\bC\s*0?\d\b)',text)})
     record['tables'].append({'page':page,'table':ti,'bbox':list(t.bbox),'rows':len(t.rows),'columns':t.col_count,'cells':cells})
  target=ROOT/'var/private-evidence/es-em-core'/(source['source_id']+'-tables.json.gz');payload=json.dumps(record,ensure_ascii=False,separators=(',',':')).encode();target.write_bytes(gzip.compress(payload,mtime=0));roles=[]
  for table in record['tables']:
   header=[{'row':c['row'],'column':c['column'],'text':c['text'],'bbox':c['bbox']}for c in table['cells']if re.search(r'(?i)compet[êe]ncia|descri[çc][ãa]o',c['text'])and len(c['text'])<140];roles.append({'page':table['page'],'table':table['table'],'bbox':table['bbox'],'rows':table['rows'],'columns':table['columns'],'competency_heading_cells':header,'physical_cells':len(table['cells']),'non_code_cells':sum(not c['printed_skill_codes']for c in table['cells'])})
  output.append({'source_id':source['source_id'],'artifact_sha256':source['artifact_sha256'],'physical_table_count':len(record['tables']),'nonempty_physical_cells':sum(len(t['cells'])for t in record['tables']),'private_table_inventory':str(target.relative_to(ROOT)),'private_table_inventory_sha256':sha(target.read_bytes()),'private_decoded_sha256':sha(payload),'tables':roles});print(source['source_id'],len(record['tables']),sum(len(t['cells'])for t in record['tables']),flush=True)
 report={'actor_type':'automated','actor_id':'codex-independent-es-em-core-auditor','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'physical_census_sha256':sha((OUT/'physical-census.json').read_bytes()),'method':'Table grid from primary drawn lines_strict, unique physical cell boxes, all native word centers and complete cell text. No body is accepted from substring/code presence; all words must later be owned or explicitly attributed to preserved coded fields.','sidecar_generated':False,'sources':output};(OUT/'table-census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
