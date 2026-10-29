import json,hashlib
from pathlib import Path
import pymupdf as f
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;PRIVATE=ROOT/'var/private-evidence/native-body-rj-peer'
def main():
 d=f.open(ROOT/'data/raw/RJ/rj-em-curriculo-referencial.pdf');shots=[]
 for pn,box in [(76,[135,165,800,300]),(156,[135,430,800,545]),(184,[135,165,800,510]),(220,[135,165,800,490])]:
  p=d[pn-1];p.remove_rotation();pix=p.get_pixmap(matrix=f.Matrix(1.4,1.4),clip=f.Rect(box));raw=pix.tobytes('png');path=PRIVATE/f'em-p{pn}.png';path.write_bytes(raw);shots.append({'source_id':'rj-em-curriculo-referencial','page':pn,'bbox':box,'private_path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 p=f.open(ROOT/'data/raw/RJ/rj-doc-eief-2019.pdf')[382];box=[383,301,583,487];raw=p.get_pixmap(matrix=f.Matrix(2,2),clip=f.Rect(box)).tobytes('png');path=PRIVATE/'ef-p383.png';path.write_bytes(raw);shots.append({'source_id':'rj-doc-eief-2019','page':383,'bbox':box,'private_path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)});(OUT/'private-primary-crops.json').write_text(json.dumps({'actor_type':'automated','purpose':'Independent technical supersession review; bounded primary visual samples, every14occurrence also checked native','crops':shots,'images_redistributed':False},indent=2)+'\n');print([(s['page'],s['bytes'])for s in shots])
if __name__=='__main__':main()
