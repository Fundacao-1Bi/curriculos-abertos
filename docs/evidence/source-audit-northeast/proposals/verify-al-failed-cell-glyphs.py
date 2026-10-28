import pathlib,json,sys,re,unicodedata,datetime,collections,hashlib
import pymupdf as f
R=pathlib.Path(__file__).resolve().parents[4];O=pathlib.Path(__file__).parent
sys.path.insert(0,str(R/'pipeline'));from native_glyphs import NativeGlyphText
from geometry import normalize_native_page
from al_actualtext_witness import actualtext_identity_witnesses
sources={s['id']:s for s in json.loads((R/'data/manifests/northeast.json').read_text())};r=json.loads((O.parent/'expanded-preflight-classification.json').read_text());out={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','scope':'Every preflight-failing physical ruled-cell in two AL artifacts, not whole-source semantic acceptance. Compare fullpage rawdict physical clusters against independent texttrace; source characters retained.','comparison_only_equivalences':'NFKC ligatures, remove layout Cf and whitespace, source soft-hyphen→nominal hyphen. For undefined nominal trace Unicode only, exact source ActualText operators tied to active source font and IdentityCID→GID witness the same physical glyph; raw source cluster text is unchanged. No dictionary/spelling replacement.','sources':{}}
def n(t):return ''.join(c for c in unicodedata.normalize('NFKC',t.replace('\u00ad','-')) if not c.isspace() and unicodedata.category(c)!='Cf').replace('\u00ad','-')
subset=json.loads((O/'al-recovery-subset-probe.json').read_text())
for sid in ['al-recal-ef','al-recal-em']:
 s=sources[sid];d=f.open(R/s['local_path']);cache={};checks=[]
 extra_pages={705} if sid=='al-recal-ef' else {124,129,133,148}
 extra=[i for i in subset['cases']['current_core:'+sid]['records'] if i['page'] in extra_pages and i.get('bbox')]
 known={(i['page'],i['code'],tuple(i['bbox'])) for i in r['sources'][sid]['items']}
 combined=r['sources'][sid]['items']+[i for i in extra if (i['page'],i['code'],tuple(i['bbox'])) not in known]
 for item in combined:
  if item['method']!='pymupdf-ruled-cell':continue
  pn=item['page'];box=item['bbox']
  if pn not in cache:
   page=d[pn-1];normalize_native_page(page);reader=NativeGlyphText(page);clusters=[];witnesses=actualtext_identity_witnesses(page)
   for span in page.get_texttrace():
    last=None
    for ch in span['chars']:
     if ch[1]<0 and last is not None:last['text']+=chr(ch[0]);continue
     last={'text':chr(ch[0]),'box':list(ch[3]),'font':span['font'],'glyph_id':ch[1]};
     if ch[0]==65533 and (span['font'],ch[1]) in witnesses:
      last['actualtext_witness']=witnesses[(span['font'],ch[1])][0];last['text']=last['actualtext_witness']['actual_text']
     clusters.append(last)
   cache[pn]=(reader,clusters)
  reader,clusters=cache[pn];selected=[g for g in clusters if box[0]<=(g['box'][0]+g['box'][2])/2<box[2] and box[1]<=(g['box'][1]+g['box'][3])/2<box[3]];raw=reader.text(box);trace=''.join(g['text'] for g in selected)
  checks.append({'page':pn,'bbox':box,'code':item['code'],'reader_text':raw,'trace_text':trace,'passed':n(raw)==n(trace),'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'trace_sha256':hashlib.sha256(trace.encode()).hexdigest(),'actualtext_identity_witnesses':[g['actualtext_witness'] for g in selected if g.get('actualtext_witness')]})
 out['sources'][sid]={'source_sha256':s['sha256'],'pages':sorted(cache),'cells':len(checks),'count_unit':'coded fragments; multiple codes may share one physical cell','physical_cells':len({(c['page'],tuple(c['bbox'])) for c in checks}),'passed':sum(c['passed'] for c in checks),'checks':checks};print(sid,len(checks),sum(c['passed'] for c in checks),flush=True)
(O/'al-failed-cells-glyph-trace.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
