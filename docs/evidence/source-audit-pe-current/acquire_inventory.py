#!/usr/bin/env python3
"""Official PE portal inventory; private content-addressed PDF acquisition only.

Proposal output deliberately uses proposed_sources rather than sources, keeping
it outside the pipeline until the Northeast owner incorporates reviewed entries.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin,quote
import concurrent.futures,datetime,hashlib,json,re,time,unicodedata,urllib.request,urllib.error
import fitz
ROOT=Path(__file__).resolve().parents[3]
PORTAL='https://portal.educacao.pe.gov.br/ensino-medio/'
AUDIT=ROOT/'docs/evidence/source-audit-pe-current'
RAW=ROOT/'data/raw/PE'
PRIVATE=ROOT/'var/private-evidence/source-audit-pe-current'
ALLOWED={'portal.educacao.pe.gov.br','educacao.pe.gov.br','www.educacao.pe.gov.br','drive.google.com','drive.usercontent.google.com'}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def norm(t):return re.sub(r'\s+',' ',t).strip()
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def slug(t):return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',t).encode('ascii','ignore').decode().lower()).strip('-')
class Node:
    def __init__(self,tag,attrs,parent=None):self.tag=tag;self.attrs=dict(attrs);self.parent=parent;self.children=[]
    def text(self):return norm(' '.join(x.text() if isinstance(x,Node) else x for x in self.children))
    def descendants(self):
        for child in self.children:
            if isinstance(child,Node):yield child;yield from child.descendants()
class Parser(HTMLParser):
    def __init__(self):super().__init__();self.root=Node('root',[]);self.cur=self.root;self.nodes=[]
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs,self.cur);self.cur.children.append(node);self.nodes.append(node)
        if tag not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.cur=node
    def handle_endtag(self,tag):
        node=self.cur
        while node.parent and node.tag!=tag:node=node.parent
        if node.parent:self.cur=node.parent
    def handle_data(self,text):self.cur.children.append(text)
class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def validate(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in ALLOWED or p.username or p.password:raise ValueError('Unregistered source URL or redirect host')
def obtain(url,limit=80*1024*1024):
    validate(url);url=quote(url,safe=':/%?=&+#')
    req=urllib.request.Request(url,headers={'User-Agent':'CurriculosAbertos/1.0 official-source research'})
    opener=urllib.request.build_opener(Redirects())
    with opener.open(req,timeout=60) as r:
        validate(r.geturl());data=r.read(limit+1)
        if len(data)>limit:raise ValueError('Source exceeds inventory size bound')
        return data,{'http_status':r.status,'final_url':r.geturl(),'content_type':r.headers.get('content-type'),'etag':r.headers.get('etag'),'last_modified':r.headers.get('last-modified'),'bytes':len(data)}

def portal_inventory():
    html,http=obtain(PORTAL,8*1024*1024);digest=hashlib.sha256(html).hexdigest();(RAW/f'{digest}.html').write_bytes(html)
    p=Parser();p.feed(html.decode('utf-8'))
    tabs=[n.text() for n in p.nodes if n.attrs.get('role')=='tab'];panels=[n for n in p.nodes if n.attrs.get('role')=='tabpanel'];assert tabs==['2026','2025','2022-2024'] and len(panels)==3,(tabs,len(panels))
    groups=[]
    for label,panel in zip(tabs,panels):
        links=[]
        for n in panel.descendants():
            if n.tag=='a' and n.attrs.get('href') and n.text():links.append({'label':n.text(),'url':urljoin(PORTAL,n.attrs['href'])})
        groups.append({'portal_group':label,'panel_block_id':panel.attrs.get('data-block-id'),'panel_role':'tabpanel','headings':[n.text() for n in panel.descendants() if n.tag in ('h2','h3','h4','h5')],'links':links})
    evidence={'official_url':PORTAL,'collected_at':now(),'sha256':digest,'private_snapshot_path':str((RAW/f'{digest}.html').relative_to(ROOT)),'http':http,'actor_type':'automated','actor_id':'agent:rs_adapter:pe-current-inventory','method':'Stackable role=tab buttons in DOM order paired with sibling role=tabpanel containers. Portal group is not asserted as PDF edition or legal application period.','groups':groups}
    dump(AUDIT/'portal-inventory.json',evidence)
    return evidence

def download(entry):
    attempts=[]
    for index in range(2):
        try:
            data,http=obtain(entry['url']);assert b'%PDF-' in data[:1024],http
            digest=hashlib.sha256(data).hexdigest();file=RAW/f'{digest}.pdf'
            if file.exists():assert hashlib.sha256(file.read_bytes()).hexdigest()==digest
            else:
                temp=file.with_suffix('.pdf.download');temp.write_bytes(data);temp.replace(file)
            with fitz.open(file) as doc:
                assert not doc.needs_pass and len(doc)<=2000
                texts=[page.get_text() for page in doc]
                metadata=doc.metadata
                pages=len(doc)
            preview=RAW/f'{digest}.inventory.txt';preview.write_text('\n\n'.join(f'PDF PAGE {i+1}\n{t}' for i,t in enumerate(texts)))
            code_mentions=sum(len(re.findall(r'\b(?:EM\d{2}[A-Z]{2,4}\d{2,3}[A-Z0-9]*|EMIF[A-Z]+\d{2})\b',t)) for t in texts)
            dated_pages=[{'page':i+1,'years':sorted(set(re.findall(r'\b(?:19|20)\d{2}\b',t))),'preview':norm(t)[:200]} for i,t in enumerate(texts[:12]) if re.search(r'\b(?:19|20)\d{2}\b',t)]
            attempts.append({'at':now(),'result':'acquired_and_pdf_parsed',**http})
            return {**entry,'sha256':digest,'local_path':str(file.relative_to(ROOT)),'inventory_preview':str(preview.relative_to(ROOT)),'pages':pages,'bytes':len(data),'status':'acquired','collected_at':now(),'http':http,'attempts':attempts,'pdf_metadata':metadata,'first_pages': [{'page':i+1,'text':norm(t)[:1200]} for i,t in enumerate(texts[:3])],'early_year_mentions':dated_pages,'code_mentions_diagnostic_not_denominator':code_mentions}
        except Exception as e:
            attempts.append({'at':now(),'result':'failed','error':str(e)[:400]})
            if index==0:time.sleep(1)
    return {**entry,'status':'acquisition_failed','attempts':attempts}

def main():
    AUDIT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    portal=portal_inventory();group=portal['groups'][0]
    entries=[];seen=set()
    for link in group['links']:
        if not ('Organizador Curricular Trimestral da FGB' in link['label'] or re.search(r'Caderno.*(?:IFA|Atividades Complementares)',link['label'])):continue
        if link['url'] in seen:continue
        seen.add(link['url']);entries.append({**link,'portal_group':group['portal_group'],'portal_panel_block_id':group['panel_block_id']})
    assert sum('Organizador Curricular Trimestral da FGB' in e['label'] for e in entries)==12
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future={executor.submit(download,e):e for e in entries}
        for f in concurrent.futures.as_completed(future):
            r=f.result();results.append(r);print(json.dumps({'label':r['label'],'status':r['status'],'pages':r.get('pages'),'sha256':r.get('sha256')},ensure_ascii=False),flush=True)
    results.sort(key=lambda r:entries.index(next(e for e in entries if e['url']==r['url'])))
    dump(PRIVATE/'acquisition-results-full.json',results)
    public_results=[]
    for result in results:
        safe={k:v for k,v in result.items() if k!='first_pages'}
        safe['early_year_mentions']=[{k:v for k,v in mention.items() if k!='preview'} for mention in result.get('early_year_mentions',[])]
        public_results.append(safe)
    dump(AUDIT/'acquisition-results.json',public_results)
    print(json.dumps({'selected':len(entries),'acquired':sum(r['status']=='acquired' for r in results),'failed':sum(r['status']!='acquired' for r in results)},ensure_ascii=False))

if __name__=='__main__':main()
