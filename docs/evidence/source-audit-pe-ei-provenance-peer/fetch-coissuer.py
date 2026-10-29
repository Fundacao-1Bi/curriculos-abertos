from pathlib import Path
import sys,json,concurrent.futures
sys.path.insert(0,str(Path(__file__).parent));from fetch import fetch,OUT
URLS=[('undime-institutional-catalog','https://undimepe.org.br/portal/documentos?category=2'),('afogados-municipal-mirror','https://www.afogadosdaingazeira.pe.gov.br/selecao-simplificada/CURRICULO-DE-PERNAMBUCO-EDUCACAO-INFANTIL-3.pdf')]
if __name__=='__main__':
 results=list(concurrent.futures.ThreadPoolExecutor(max_workers=2).map(fetch,URLS));(OUT/'fetch-coissuer-log.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False,indent=2))
