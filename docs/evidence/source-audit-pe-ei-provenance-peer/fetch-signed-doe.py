from pathlib import Path
import sys,json,base64,hashlib
sys.path.insert(0,str(Path(__file__).parent));from fetch import fetch,OUT
if __name__=='__main__':
 result=fetch(('cepe-official-download','https://diariooficial.cepe.com.br/diariooficial/public/home/baixarJornal?codigoDiario=1&dataPublicacao=29%2F12%2F2018&edicaoExtra=false'))
 if result.get('http_status')==200:
  raw=Path(result['private_snapshot']).read_bytes();data=json.loads(raw)
  if isinstance(data,dict)and data.get('dados'):
   pdf=base64.b64decode(data['dados'],validate=True);assert pdf.startswith(b'%PDF');path=OUT/'official-doe-signed-route-20181229.pdf';path.write_bytes(pdf);result['decoded_pdf']={'path':str(path.relative_to(Path.cwd())),'bytes':len(pdf),'sha256':hashlib.sha256(pdf).hexdigest(),'file_name':data.get('nome'),'media_type':data.get('mediaType'),'cryptographic_signature_validity_tested':False}
 (OUT/'fetch-signed-doe-log.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
