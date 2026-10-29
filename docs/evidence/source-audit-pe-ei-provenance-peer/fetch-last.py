from pathlib import Path
import sys,json,concurrent.futures
sys.path.insert(0,str(Path(__file__).parent));from fetch import fetch,OUT
URLS=[('see-home','https://portal.educacao.pe.gov.br/'),('cepe-diario-app','https://diariooficial.cepe.com.br/diariooficialweb/'),('drive-exact-current','https://drive.google.com/uc?id=1hnNk221nOEBv7fgxPtCDjRhMyDZ9sEBk&export=download'),('undime-documents','https://undimepe.org.br/portal/documentos'),('cee2021-corrob','https://www.cee.pe.gov.br/wp-content/uploads/2025/10/PARECER-007-2021.pdf')]
if __name__=='__main__':
 results=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(fetch,URLS));(OUT/'fetch-last-log.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False,indent=2))
