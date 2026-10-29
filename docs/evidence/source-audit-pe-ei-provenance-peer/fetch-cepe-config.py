from pathlib import Path
import sys,json,concurrent.futures
sys.path.insert(0,str(Path(__file__).parent));from fetch import fetch,OUT
URLS=[('cepe-app-config','https://diariooficial.cepe.com.br/diariooficialweb/app/app.config.js'),('cepe-app-min','https://diariooficial.cepe.com.br/diariooficialweb/content/scripts-min/app-cdb1880b4f.min.js')]
if __name__=='__main__':
 results=list(concurrent.futures.ThreadPoolExecutor(max_workers=2).map(fetch,URLS));(OUT/'fetch-cepe-config-log.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(results,ensure_ascii=False,indent=2))
