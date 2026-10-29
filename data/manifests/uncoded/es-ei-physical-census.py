import fitz,json,hashlib,re
from pathlib import Path
root=Path.cwd(); sources=[s for s in json.loads((root/'data/manifests/bncc-southeast.json').read_text()) if s['id'] in ['es-curriculo-es-2020-vol-01-educacao-infantil-rev2026','es-tema-integrador-final-24-10']]
out=[]
for s in sources:
 path=root/s['local_path'];doc=fitz.open(path);pages=[]
 for i,p in enumerate(doc):
  if p.rotation:p.remove_rotation()
  text=p.get_text();tables=[]
  for t in p.find_tables().tables:
   tables.append({'bbox':list(t.bbox),'rows':len(t.rows),'cols':t.col_count,'cells':t.extract()})
  lines=[{'text':''.join(x['text'] for x in l['spans']),'bbox':list(l['bbox']),'size':max(x['size'] for x in l['spans'])} for b in p.get_text('dict')['blocks'] if 'lines'in b for l in b['lines']]
  pages.append({'page':i+1,'text':text,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'tables':tables,'lines':lines})
 obj={'source_id':s['id'],'artifact_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':pages};(root/'var/private-evidence/es-ei-temas'/f"{s['id']}-native.json").write_text(json.dumps(obj,ensure_ascii=False))
 out.append({'source_id':s['id'],'artifact_sha256':obj['artifact_sha256'],'page_count':len(doc),'page_inventory':[{'page':p['page'],'text_sha256':p['text_sha256'],'native_chars':len(p['text']),'table_count':len(p['tables']),'table_shapes':[[t['rows'],t['cols']]for t in p['tables']],'headings':[l['text'] for l in p['lines'] if l['size']>=14 or re.match(r'(TI\s|Direitos de Aprendizagem|Para Refletir|Campo de Experi|Aprender a |Dicas para|Vale Observar)',l['text'])]} for p in pages]})
(root/'docs/evidence/source-audit-southeast-uncoded/ei-temas/physical-census.json').write_text(json.dumps({'actor_type':'automated','method':'all physical pages scanned before sidecar construction; native lines and table cells enumerated independently','sources':out},ensure_ascii=False,indent=2))
for src in out:
 print(src['source_id'],src['page_count']);
 for p in src['page_inventory']:
  if src['page_count']==140 and p['page']>=59 and p['page']<=133:print(p['page'],p['table_shapes'],p['headings'])
