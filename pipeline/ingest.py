#!/usr/bin/env python3
"""Currículos Abertos: bounded acquisition, page/cell extraction and immutable candidates.

Downloaded documents are untrusted data. This program never executes document content.
The web process must run this program in a separate worker process.
"""
from __future__ import annotations
import argparse
import collections
import contextlib
import datetime as dt
import hashlib
import gzip
import http.client
import ipaddress
import json
import os
import re
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from urllib.parse import urljoin, urlsplit, quote

ROOT = Path(__file__).resolve().parents[1]
EXTRACTION_REVISION = 'page-cell-v1.4.0'
MAPPING_REVISION = 'documented-code-rules-v1.1.0'
SCHEMA_VERSION = '1.0.0'
UFS = 'AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split()
STAGES = ('EI', 'EF', 'EM')
MAX_BYTES = int(os.getenv('SOURCE_MAX_BYTES', '209715200'))
MAX_PAGES = int(os.getenv('SOURCE_MAX_PAGES', '2500'))
TIMEOUT = int(os.getenv('SOURCE_TIMEOUT_SECONDS', '90'))
MAX_ATTEMPTS = 3
STOP = False
# National and local forms. A national-code occurrence is not automatically a learning.
# Local suffixes remain part of the canonical code (MG, /ES, ART, QUI, FIL, *, ...).
NATIONAL_PATTERN = r'(?:EI\d{2}[A-Z]{2}\d{2}|EF\d{2}[A-Z]{2}\d{2,3}|EM\d{2}(?:[A-Z]{3}\d{3}|LP\d{1,4}|CO\d{2}))'
NATIONAL_BASE = re.compile(NATIONAL_PATTERN)
NATIONAL = re.compile(r'(?<![A-Z0-9])'+NATIONAL_PATTERN+r'(?![A-Z0-9])')
CODE_ANY = re.compile(r'(?<![A-Z0-9])(?:(?:'+'|'.join(UFS+['BR'])+r')(?:[-.]\s*|[ \t]+))?(?:'+NATIONAL_PATTERN+r'|EMIF[A-Z]{2,6}\d{1,3}|EM(?:LGG|MAT|CNT|CHS)\d{3}[A-Z]?|EM(?:LP|CH)\d{2,3}(?:[-.]?[A-Z])?|EM[123]PV\d{2}|PV\d{2}|(?:LP|LGG|CHSA|MAT|CN|EPT)\d{2,3}(?:FG|IF))(?:(?:\.\s*[scadn]\s*\.\s*\d{2})|(?:[A-Z][A-Za-z0-9]{0,12}|[a-z]|\*)|[/.-][A-Za-z0-9-]+)*(?![A-Z0-9])')
CODE = CODE_ANY
COMPONENTS = {'LP':'Língua Portuguesa','MA':'Matemática','CI':'Ciências','GE':'Geografia','HI':'História','AR':'Arte','EF':'Educação Física','LI':'Língua Inglesa','ER':'Ensino Religioso','LGG':'Linguagens e suas Tecnologias','MAT':'Matemática e suas Tecnologias','CNT':'Ciências da Natureza e suas Tecnologias','CHS':'Ciências Humanas e Sociais Aplicadas','EO':'O eu, o outro e o nós','CG':'Corpo, gestos e movimentos','TS':'Traços, sons, cores e formas','EF-EI':'Escuta, fala, pensamento e imaginação','ET':'Espaços, tempos, quantidades, relações e transformações','CO':'Computação'}


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
def sha_bytes(value): return hashlib.sha256(value).hexdigest()
def sha_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()
def log(event, **fields): print(json.dumps({'time': now(), 'event': event, **fields}, ensure_ascii=False), flush=True)
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(canonical(value))
    tmp.replace(path)
def normalize(text): return ' '.join(unicodedata.normalize('NFKD', re.sub(r'\u00ad\s*', '', re.sub(r'(?<=[a-zà-ÿ])-\s+(?=[a-zà-ÿ])', '', text))).encode('ascii', 'ignore').decode().casefold().split())
def safe_path(relative, root=ROOT):
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()): raise ValueError('Path escapes storage root')
    return candidate

def load_sources():
    found = {}
    for path in sorted((ROOT / 'data/manifests').glob('*.json')):
        value = json.loads(path.read_text())
        sources = value if isinstance(value, list) else value.get('sources', [])
        if not isinstance(sources, list): continue
        for source in sources:
            if not isinstance(source, dict) or not source.get('id'): continue
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,239}',source['id']) or source.get('uf') not in UFS+['BR']:raise ValueError('Invalid registered source ID or jurisdiction')
            if source['id'] in found and found[source['id']] != source: raise ValueError(f'Duplicate source ID: {source["id"]}')
            found[source['id']] = dict(source, manifest_path=str(path.relative_to(ROOT)))
    return list(found.values())


def handle_stop(signum, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)


class SafeDownloader:
    """Only registered HTTPS hosts; every redirect validated; connect to validated IP.

    Hostname is preserved for TLS verification and SNI while the TCP destination is
    pinned to the public DNS address already checked, preventing DNS rebinding.
    """
    def __init__(self, sources):
        self.allowed_hosts = set(filter(None, os.getenv('SOURCE_ALLOWED_HOSTS', '').split(',')))
        for source in sources:
            for field in ('official_url', 'artifact_url'):
                hostname = urlsplit(source.get(field) or '').hostname
                if hostname: self.allowed_hosts.add(hostname.lower())
            for hostname in source.get('allowed_redirect_hosts', []): self.allowed_hosts.add(hostname.lower())
        self.last_host = {}

    def validate(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.fragment:
            raise ValueError('Only credential-free HTTPS source URLs are permitted')
        if parsed.port not in (None, 443): raise ValueError('Non-standard source port rejected')
        host = (parsed.hostname or '').lower()
        if host not in self.allowed_hosts: raise ValueError(f'Redirect/source host not allowlisted: {host}')
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        ips = sorted({entry[4][0] for entry in addresses})
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips): raise ValueError('Private/reserved source address rejected')
        return parsed, ips[0]

    def request(self, url, headers=None, method='GET', max_bytes=MAX_BYTES):
        if STOP: raise InterruptedError('Job pause requested')
        current = url
        for redirect in range(6):
            if STOP: raise InterruptedError('Job pause requested')
            parsed, ip = self.validate(current)
            host = parsed.hostname.lower()
            delay = 1 - (time.monotonic() - self.last_host.get(host, 0))
            if delay > 0: time.sleep(delay)
            self.last_host[host] = time.monotonic()
            conn = http.client.HTTPSConnection(host, 443, timeout=TIMEOUT, context=ssl.create_default_context())
            sock = socket.create_connection((ip, 443), timeout=TIMEOUT)
            conn.sock = conn._context.wrap_socket(sock, server_hostname=host)
            try:
                conn.request(method, quote(parsed.path,safe='/%:@!$&()*+,;=-._~') + ('?' + quote(parsed.query,safe='=&%/:?+;,@-._~') if parsed.query else ''), headers={'Host': host, 'User-Agent': 'CurriculosAbertos/0.1 (+documentary-research)', 'Accept-Encoding': 'identity', **(headers or {})})
                response = conn.getresponse()
                info = {key.lower(): val for key, val in response.getheaders()}
                if response.status in (301, 302, 303, 307, 308):
                    location = info.get('location')
                    if not location: raise ValueError('Redirect without Location')
                    current = urljoin(current, location)
                    continue
                if response.status == 304: return {'status': 304, 'url': current, 'headers': info, 'body': b''}
                if response.status != 200: raise ValueError(f'HTTP {response.status} at {host}')
                size = int(info.get('content-length', '0'))
                if size > max_bytes: raise ValueError('Source exceeds configured size bound')
                start = time.monotonic()
                body = bytearray()
                while True:
                    if STOP: raise InterruptedError('Job pause requested')
                    if time.monotonic() - start > TIMEOUT: raise TimeoutError('Source total duration exceeded')
                    block = response.read(min(1024 * 1024, max_bytes - len(body) + 1))
                    if not block: break
                    body.extend(block)
                    if len(body) > max_bytes: raise ValueError('Source exceeds configured size bound')
                return {'status': response.status, 'url': current, 'headers': info, 'body': bytes(body)}
            finally: conn.close()
        raise ValueError('Source redirect limit exceeded')

    def acquire(self, source):
        last = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                result = self.request(source['artifact_url'])
                body = result['body']
                if not body.startswith(b'%PDF-'): raise ValueError('Acquired artifact is not a PDF; explicit HTML/structured adapter required')
                target = ROOT / 'data/raw' / source['uf'] / f'{source["id"]}.pdf'
                target=safe_path(str(target.relative_to(ROOT)))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                return target, dict(source, sha256=sha_bytes(body), collected_at=now(), local_path=str(target.relative_to(ROOT)), acquisition={'attempts': attempt, 'final_url': result['url'], 'headers': {k: v for k, v in result['headers'].items() if k in ('etag', 'last-modified', 'content-type', 'content-length')}})
            except InterruptedError: raise
            except Exception as error:
                last = error
                log('download_failed', source_id=source['id'], attempt=attempt, error=str(error))
                if attempt < MAX_ATTEMPTS: time.sleep(min(2 ** attempt, 8))
        raise last


def national_position(code):
    if re.fullmatch(r'(?:EM[123])?PV\d{2}',code):return {'stage':'EM','component':'Projeto de Vida','area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'source_local_code_context','position_note':'Objetivo próprio PV, sem ano/semestre inferido.'}
    if re.search(r'EMIF[A-Z]{2,6}\d{1,3}',code):
        return {'stage':'EM','component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'document_code_context','position_note':'Código de itinerário; área/série não inferidas sem declaração documental.'}
    local_df=re.fullmatch(r'(LP|LGG|CHSA|MAT|CN|EPT)\d{2,3}(FG|IF)',code)
    if local_df:
        return {'stage':'EM','component':'Língua Portuguesa' if local_df[1]=='LP' else None,'area':{'LP':'Linguagens e suas Tecnologias','LGG':'Linguagens e suas Tecnologias','CHSA':'Ciências Humanas e Sociais Aplicadas','MAT':'Matemática e suas Tecnologias','CN':'Ciências da Natureza e suas Tecnologias','EPT':'Educação Profissional e Técnica'}.get(local_df[1]),'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'document_local_code','position_note':'Código próprio do Currículo em Movimento; FG/IF preservados, sem relação BNCC inferida.'}
    go_local=re.fullmatch(r'(?:GO[-.]?)?EM(LGG|MAT|CNT|CHS|LP|CH)\d{2,3}[-.]?[A-Z]?',re.sub(r'\s+','',code))
    if go_local:return {'stage':'EM','component':None,'area':COMPONENTS.get(go_local[1]),'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'source_local_code_context','position_note':'Objetivo próprio de Goiás sem código nacional atribuído por transformação.'}
    match = NATIONAL_BASE.search(code)
    if not match:
        stage_match=re.search(r'(?:^|[-. \t\n])(EI|EF|EM)',code)
        if stage_match:return {'stage':stage_match[1],'component':None,'area':None,'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'source_local_code_stage_candidate','position_note':'Código local não interpretado pela gramática nacional; nenhum ano, bloco ou componente inventado.'}
        return None
    base = match.group()
    stage = base[:2]
    if stage == 'EI':
        symbol = base[4:6]
        component = COMPONENTS.get('EF-EI' if symbol == 'EF' else symbol)
        age = {'01':'Bebês (zero a 1 ano e 6 meses)', '02':'Crianças bem pequenas (1 ano e 7 meses a 3 anos e 11 meses)', '03':'Crianças pequenas (4 anos a 5 anos e 11 meses)'}.get(base[2:4])
        return {'stage': stage, 'component': component, 'area': 'Campos de experiências', 'years': None, 'year_label': None, 'age_group': age, 'period': None, 'position_origin':'national_code_convention', 'position_note':'Grupo etário explicitado pela convenção nacional do código; posicionamento local adicional não inferido.'}
    if stage == 'EF':
        block = base[2:4]
        years = [int(block)] if block[0] == '0' else list(range(int(block[0]), int(block[1]) + 1)) if int(block[0]) <= int(block[1]) else None
        return {'stage':stage,'component':COMPONENTS.get(base[4:6]),'area':None,'years':years,'year_label':f'{years[0]}º ano' if years and len(years)==1 else f'{years[0]}º ao {years[-1]}º ano' if years else None,'age_group':None,'period':None,'position_origin':'national_code_convention','position_note':'Bloco preservado conforme convenção do código nacional; não implica período letivo local.'}
    return {'stage':stage,'component':'Língua Portuguesa' if base[4:6]=='LP' else 'Computação' if base[4:6]=='CO' else None,'area':COMPONENTS.get(base[4:7]) or ('Linguagens e suas Tecnologias' if base[4:6]=='LP' else 'Computação' if base[4:6]=='CO' else None),'years':None,'year_label':None,'age_group':None,'period':None,'position_origin':'national_code_convention','position_note':'O código EM não determina série; a fonte deve explicitar o posicionamento.'}


def decode_source_text(source,text):
    value=text
    for mapping in source.get('glyph_replacements',[]):
        evidence=mapping.get('evidence') or {}
        if not evidence or not isinstance(mapping.get('from'),str) or len(mapping['from'])!=1 or not isinstance(mapping.get('to'),str) or not 1<=len(mapping['to'])<=8:raise ValueError('Invalid source-specific glyph decoding map')
        if evidence.get('artifact_sha256')!=source.get('sha256') or evidence.get('source_id')!=source['id']:raise ValueError('Glyph decoding map is not bound to this exact source artifact')
        value=value.replace(mapping['from'],mapping['to'])
    return value


def clean_text(text):
    # Canonical text keeps spelling, case and punctuation. Only PDF line wrapping is normalized.
    return re.sub(r'[ \t]+', ' ', re.sub(r'\s*\n\s*', ' ', re.sub(r'\u00ad\s*', '', text))).strip()


def candidates_from_cell(cell, next_cell=None, source=None):
    matches=[]
    for match in CODE_ANY.finditer(cell):
        # A citation in the middle of a sentence is not a new coded objective.
        prefix=cell[:match.start()]
        line_prefix=prefix.rsplit('\n',1)[-1].strip()
        local_go_goal=(source or {}).get('id')=='go-dcgoem-portal-atual' and re.match(r'GO(?:[-.]\s*|\s+)EM',match.group()) and prefix.rstrip().endswith('(') and cell[match.end():].lstrip().startswith(')')
        if not local_go_goal and line_prefix not in ('','(','[','•','-') and not re.match(r'^Habilidades?\b.*:\s*\(*$',line_prefix,re.IGNORECASE):continue
        matches.append(match)
    found=[]
    for index,match in enumerate(matches):
        tail=cell[match.end():matches[index+1].start() if index+1<len(matches) else len(cell)]
        tail=re.sub(r'^[\s():;\-–—]+','',tail).strip()
        # Remove an opening delimiter belonging to the next code, not source prose.
        if index+1<len(matches) and tail.endswith('(') and tail.count('(')>tail.count(')'): tail=tail[:-1].rstrip()
        if not tail and next_cell: tail=next_cell.strip()
        if not tail or CODE_ANY.match(tail.lstrip('([')): continue
        source_id=(source or {}).get('id','')
        boundaries=[]
        if source_id=='rj-em-curriculo-referencial': boundaries=['Objetos de conhecimento:','Campos de Atuação Social:','Competência específica',r'Habilidades? de[^\n]*:']
        if source_id.startswith('es-ifa-'): boundaries=[r'Competência \d+']
        for marker in boundaries:
            boundary=re.search(marker,tail,flags=re.IGNORECASE)
            if boundary: tail=tail[:boundary.start()].rstrip()
        if tail: found.append((match.group(),clean_text(tail),cell))
    return found


def make_item(source, code, text, page, method, locator, context=None, quality='pending_documentary_review'):
    token = f'{source["id"]}|{page}|{locator}|{code or "uncoded"}'
    position = national_position(code or '')
    if position and position['stage'] not in source.get('stages',[]): position = None
    item = {'id':f'ca:{source["id"]}:{sha_bytes(token.encode())[:20]}','curriculum_id':source.get('curriculum_id') or f'{source["uf"].lower()}:{source["id"]}','source_id':source['id'],'uf':source['uf'],'code':code,'text':text,'normalized_text':normalize(text),'editorial_note':None,'kind':'objetivo_aprendizagem' if position and position['stage']=='EI' else 'habilidade' if code and position else 'referencia_no_documento' if code else 'secao_normativa','parent_id':None,'positions':[position] if position else [],'evidence':[{'source_id':source['id'],'page':page,'printed_page':None,'section':context,'excerpt':text,'locator':locator,'method':method}],'extraction_revision':EXTRACTION_REVISION,'extraction_status':quality,'technical_validation_status':'pending_literal_and_documentary_verification','pedagogical_review_status':'not_reviewed','publication_status':'extracted_candidate','canonical_text_policy':'PDF line wraps normalized; spelling/punctuation unaltered','review_events':[{'actor_type':'automated','actor_id':'curriculos-abertos:page-cell-extractor','method':EXTRACTION_REVISION,'result':quality,'at':now()}]}
    if source.get('document_type') in ('ato_normativo','resolucao','parecer'):
        item['kind']='referencia_no_documento' if code else 'artigo_normativo'
        item['positions']=[]
    if not item['positions']: item['position_unknown_reason']='Fonte não explicita posicionamento estruturado deste trecho ou contexto ainda não processado; nenhum ano/etapa inventado.'
    return item


def extract_bncc_dataset(source, path):
    """Reuse CC-BY bncc-dados; verify primary code/page and keep per-record provenance."""
    import pymupdf as fitz
    upstream=ROOT/'data/raw/BR/bncc-dados'
    mapping={'br-bncc-2018':[('dados/bncc-2018/educacao-infantil.json','objetivos'),('dados/bncc-2018/ensino-fundamental.json','habilidades'),('dados/bncc-2018/ensino-medio.json','habilidades')], 'br-bncc-computacao-2022':[('dados/computacao-2022/computacao.json','objetivos_ei'),('dados/computacao-2022/computacao.json','habilidades_ef'),('dados/computacao-2022/computacao.json','habilidades_em')]}
    inputs_path=ROOT/'data/manifests/uncoded/br-structure-input.json'
    fixed_inputs=json.loads(inputs_path.read_text()).get('inputs',{}) if inputs_path.exists() else {}
    if source['id'] not in mapping or (not upstream.exists() and not fixed_inputs):return None
    document=fitz.open(path)
    pages=[{'page':i+1,'text':page.get_text('text',sort=True),'text_sha256':sha_bytes(page.get_text('text',sort=True).encode()),'code_mentions':len(CODE_ANY.findall(page.get_text('text'))),'method':'pymupdf-native'} for i,page in enumerate(document)]
    items=[];warnings=[]
    for relative,key in mapping[source['id']]:
        data=fixed_inputs.get(relative) or json.loads((upstream/relative).read_text())
        for record in data[key]:
            locator=record['fonte'].get('localizador_pdf') or record['fonte'].get('localizador','')
            found=re.search(r'página PDF (\d+)',locator)
            if not found: raise ValueError('BNCC dataset record lacks PDF page locator')
            page_number=int(found.group(1));code=record['codigo'];text=record['texto']
            printed_code='EF05CO011' if source['id']=='br-bncc-computacao-2022' and code=='EF05CO11' else code
            if not 1<=page_number<=len(pages): raise ValueError('BNCC dataset page outside primary source')
            literal_code=printed_code in pages[page_number-1]['text']
            literal_text=normalize(text) in normalize(pages[page_number-1]['text'])
            item=make_item(source,code,text,page_number,'bncc-dados-licensed-structured-import',f'upstream-code:{code}',quality='upstream_structured_with_primary_locator')
            item['id']=f'ca:{source["id"]}:{code}'
            if printed_code!=code:
                item['code']=printed_code
                item['code_aliases']=[code]
                item['editorial_note']='O PDF oficial, página 36, imprime EF05CO011. O dataset reutilizado normalizava para EF05CO11; o texto original foi preservado e a forma normalizada é somente alias de busca. O ID técnico anterior permanece estável.'
                item['source_context']={'printed_code':printed_code,'upstream_normalized_code':code,'verification':'Primary PDF page 36 visually inspected; original is not silently corrected.'}
            item['publication_status']='source_attributed'
            item['technical_validation_status']='primary_code_and_text_checked' if literal_code and literal_text else 'primary_code_checked_text_layout_pending' if literal_code else 'primary_locator_pending'
            item['source_dataset']={'name':'bncc-dev/bncc-dados','commit':'9c268978efa2aa250834c6a9edb6074432752838','path':relative,'license':'CC-BY-4.0','url':'https://github.com/bncc-dev/bncc-dados','source_record_locator':record['fonte']}
            if record.get('anos') and item['positions']: item['positions'][0].update(years=record['anos'],position_origin='source_dataset_explicit_years')
            item['source_context']={**(item.get('source_context') or {}),**{k:v for k,v in record.items() if k not in ('texto','codigo','fonte','vigencia')}}
            if not literal_code: warnings.append({'page':page_number,'code':code,'issue':'primary_code_locator_not_verified'})
            if not literal_text: item['extraction_flags']=['primary_text_order_requires_cell_review']
            items.append(item)
    return {'source_id':source['id'],'sha256':sha_file(path),'extraction_revision':EXTRACTION_REVISION,'pages':pages,'items':items,'warnings':warnings,'table_count':None,'page_count':len(pages),'document_page_count':len(document),'code_mentions':sum(p['code_mentions'] for p in pages),'coded_items':len(items),'extracted_at':now(),'reconciliation_status':'licensed_dataset_cross_checked_primary_locator','dataset_attribution':'bncc-dev/bncc-dados, CC-BY-4.0, commit 9c268978efa2aa250834c6a9edb6074432752838','ocr_pending':False}


def extraction_config_hash(source):
    fields=('id','uf','stages','components','stage_component_inventory','normative_parts','non_curricular_code_pages','code_rules','position_contexts','structure_sections','uncoded_items_path','layout_rules','extraction_pages','scope_pages','page_text_end_markers','requires_ocr','glyph_replacements','page_regions','extraction_page_ranges')
    import pymupdf
    config={field:source.get(field) for field in fields}
    config['native_engine']={'name':'PyMuPDF','version':pymupdf.__version__}
    config['extraction_revision']=EXTRACTION_REVISION
    if source.get('uncoded_items_path'):
        path=safe_path(source['uncoded_items_path'])
        if path.exists():config['uncoded_items_sha256']=sha_file(path)
    return sha_bytes(canonical(config))


def extract_pdf(source, path, force=False):
    import pymupdf as fitz
    if tuple(map(int,fitz.__version__.split('.')[:3]))<(1,26,7):raise RuntimeError('PyMuPDF>=1.26.7 required. Use var/venv-pipeline/bin/python or patched worker runtime.')
    digest = sha_file(path)
    config_hash=extraction_config_hash(source)
    expected = source.get('sha256')
    if expected and expected != digest: raise ValueError('Artifact SHA-256 mismatch')
    cache_path = ROOT / 'data/extracted' / f'{digest}-{EXTRACTION_REVISION}.json'
    if cache_path.exists() and not force:
        cached = json.loads(cache_path.read_text())
        if cached.get('source_id') == source['id'] and cached.get('extraction_config_sha256')==config_hash and not (cached.get('ocr_pending') and not os.getenv('SOURCE_SKIP_OCR')):
            log('extraction_cache_hit', source_id=source['id'], sha256=digest)
            return cached
    reused=extract_bncc_dataset(source,path)
    if reused is not None:
        reused['extraction_config_sha256']=config_hash
        write_json(cache_path,reused)
        log('structured_reuse_complete',source_id=source['id'],items=len(reused['items']),pages=reused['page_count'])
        return reused
    document = fitz.open(path)
    if document.needs_pass and not document.authenticate(''): raise ValueError('Encrypted document requires legitimate access')
    if len(document) > MAX_PAGES: raise ValueError('Page count exceeds configured parser bound')
    items, pages, warnings = [], [], []
    table_count = 0
    open_cells={}
    for index, page in enumerate(document):
        if STOP: raise InterruptedError('Extraction checkpoint requested')
        page_number = index + 1
        from geometry import normalize_native_page,words_from_page
        scoped_pages=source.get('extraction_pages') or source.get('scope_pages')
        ranges=source.get('extraction_page_ranges',[])
        if scoped_pages and page_number not in scoped_pages:continue
        if ranges and not any(r['page_start']<=page_number<=r['page_end'] for r in ranges):continue
        page_normalization=normalize_native_page(page)
        plain=page.get_text('text',sort=not bool(source.get('glyph_replacements'))) or ''
        method='pymupdf-native'
        page_words=words_from_page(page)
        ocr_result=None
        image_area=sum((fitz.Rect(info['bbox']).get_area() for info in page.get_image_info()),0)
        needs_ocr=bool(source.get('requires_ocr') or (len(plain.strip())<30 and image_area>0.15*page.rect.get_area()))
        if needs_ocr and not os.getenv('SOURCE_SKIP_OCR'):
            try:
                from ocr import ocr_page
                ocr_result=ocr_page(page,source,page_number)
                plain=ocr_result['text'];page_words=ocr_result.get('layout_words') or ocr_result['words']
                method=ocr_result['method']
                warnings.extend({'page':page_number,**warning} for warning in ocr_result.get('warnings',[]))
                warnings.append({'page':page_number,'issue':'ocr_used','status':'requires_documentary_review','method':method,'ocr_cache_key':ocr_result.get('cache_key')})
            except Exception as error:
                warnings.append({'page':page_number,'issue':'no_extractable_text_or_ocr_failed','error':str(error)[:300]})
        # Decode only a reviewed, source-specific font mapping; never a global guessing substitution.
        for mapping in source.get('glyph_replacements',[]):
            if mapping.get('evidence') and mapping.get('from') is not None and mapping.get('to') is not None:
                plain=decode_source_text(source,plain)
                for word in page_words:word['text']=word['text'].replace(mapping['from'],mapping['to'])
        for stop in source.get('page_text_end_markers',[]):
            if isinstance(stop,dict) and stop.get('page')==page_number:
                marker=stop.get('marker','')
                if marker and marker in plain:
                    plain=plain.split(marker,1)[0]
                    marker_words=[word for word in page_words if word['text']==marker.split()[0]]
                    if marker_words:page_words=[word for word in page_words if word['top']<min(word['top'] for word in marker_words)]
        region_rule=next((rule for rule in source.get('page_regions',[]) if rule.get('page')==page_number),None)
        if region_rule:
            from geometry import clipped_words,words_text
            region_words=[];region_text=[]
            for region in region_rule['regions']:
                selected=clipped_words(page_words,*region)
                region_words.extend(selected);region_text.append(words_text(selected))
            page_words=region_words;plain='\n\n'.join(region_text)
        layout_height=ocr_result['layout_rect'][3] if ocr_result else page.rect.height
        layout_width=ocr_result['layout_rect'][2] if ocr_result else page.rect.width
        pages.append({'page':page_number,'text':plain,'text_sha256':sha_bytes(plain.encode()),'code_mentions':len(list(CODE_ANY.finditer(plain))),'method':method,'ocr_required':needs_ocr,'ocr_completed':bool(ocr_result),'page_regions':region_rule.get('regions') if region_rule else None,'page_normalization':page_normalization,'ocr':{key:ocr_result.get(key) for key in ('method','cache_key','configuration','result_sha256','layout_to_original','ocr_rotation_applied')} if ocr_result else None})
        page_items = []
        tables=[]
        # Restrict costly table detection to pages with curriculum codes.
        if not ocr_result and CODE_ANY.search(plain) and page_number not in source.get('non_curricular_code_pages',[]):
            try:
                tables = page.find_tables(strategy='lines').tables
                for table_index, table in enumerate(tables):
                    rows=table.extract()
                    if source.get('glyph_replacements'):
                        rows=[[decode_source_text(source,page.get_text('text',clip=fitz.Rect(box)+(-0.2,-0.2,0.2,0.2),sort=False)) if box else None for box in row.cells] for row in table.rows]
                    if not rows:continue
                    from geometry import learning_column_indices
                    learning_columns=learning_column_indices(table,rows)
                    column_headers={ci:' '.join(str(row[ci] or '') for row in rows[:3] if ci<len(row)) for ci in range(max(len(row) for row in rows))}
                    blocked_columns={ci for ci,header in column_headers.items() if normalize(header).startswith('relacao ')}
                    table_count += 1
                    for row_index, row in enumerate(rows):
                        for cell_index, value in enumerate(row):
                            if not value or cell_index in blocked_columns:continue
                            if source['id']=='pb-proposta-ei-ef' and (not learning_columns or cell_index not in learning_columns):continue
                            next_header=normalize(column_headers.get(cell_index+1,''))
                            following=row[cell_index+1] if cell_index+1<len(row) and re.match(r'^(?:habilidades?|objetivos de aprendizagem|descricao da habilidade)(?:$|\s)',next_header) else None
                            bounds=table.rows[row_index].cells[cell_index]
                            column_key=(round(bounds[0]/10),round(bounds[2]/10)) if bounds else None
                            first_code=CODE_ANY.search(value)
                            prefix=value[:first_code.start()] if first_code else value
                            prefix=prefix.rstrip().rstrip('(').strip()
                            prior=open_cells.get(column_key)
                            if row_index<3 and prior and prior['page']==page_number-1 and len(prefix)>10 and (prefix[0].islower() or not prior['item']['text']) and not normalize(prefix).startswith(('objetivos','habilidades','campo','criancas','bebes')):
                                fragment=clean_text(prefix)
                                previous=prior['item']
                                previous['text']=(previous['text']+' '+fragment).strip()
                                previous['normalized_text']=normalize(previous['text'])
                                previous['evidence'].append({'source_id':source['id'],'page':page_number,'printed_page':None,'section':'Continuação de célula na página seguinte','excerpt':fragment,'locator':f'table:{table_index}/row:{row_index}/cell:{cell_index}','bbox':list(bounds) if bounds else None,'method':'cross-page-cell-continuation'})
                                previous['cross_page_continuation']=True
                                if re.search(r'[.!?;:][)\"”]*$',fragment):previous['extraction_flags']=[flag for flag in previous.get('extraction_flags',[]) if flag not in ('possible_page_continuation','code_only_waiting_page_continuation')]
                                open_cells.pop(column_key,None)
                            cell_candidates=candidates_from_cell(value, following, source)
                            code_matches=list(CODE_ANY.finditer(value))
                            if cell_index in learning_columns and code_matches and not value[code_matches[-1].end():].strip(' ()[]\n\t.;:'):
                                trailing=[];previous_end=0
                                for trailing_match in code_matches:
                                    before=value[previous_end:trailing_match.start()].strip().lstrip(') ').rstrip('(').strip()
                                    if len(before)>10:trailing.append((trailing_match.group(),clean_text(before),value))
                                    previous_end=trailing_match.end()
                                if trailing:cell_candidates=trailing
                            for candidate_index,(code, text, raw) in enumerate(cell_candidates):
                                item = make_item(source,code,text,page_number,'pymupdf-ruled-cell',f'table:{table_index}/row:{row_index}/cell:{cell_index}', context=f'Tabela {table_index+1}, linha {row_index+1}')
                                item['evidence'][0]['bbox'] = list(table.bbox)
                                if len(list(CODE_ANY.finditer(raw))) > 1: item['extraction_flags']=['multiple_codes_in_cell']
                                if len(text)>3500: item['extraction_flags']=item.get('extraction_flags',[])+['long_cell_requires_review']
                                if bounds:item['evidence'][0]['bbox']=list(bounds)
                                item['source_context']={'table_row':{str(ci):value for ci,value in enumerate(row) if value},'column_headers':column_headers,'source_column_index':cell_index,'source_table_index':table_index}
                                if row_index==len(rows)-1 and candidate_index==len(cell_candidates)-1 and not re.search(r'[.!?;:][)\"”]*$',text):
                                    open_cells[column_key]={'page':page_number,'item':item}
                                    item['extraction_flags']=item.get('extraction_flags',[])+['possible_page_continuation']
                                page_items.append(item)
            except Exception as error:
                warnings.append({'page':page_number,'issue':'table_extraction_error','error':str(error)[:300]})
        if not page_items and not tables and CODE_ANY.search(plain) and page_number not in source.get('non_curricular_code_pages',[]):
            # Unruled tables remain explicitly flagged candidates.
            words=page_words
            code_words=[w for w in words if CODE_ANY.search(w['text'])]
            for word_index,word in enumerate(code_words):
                same_line=[w for w in words if (w.get('block'),w.get('paragraph'),w.get('line'))==(word.get('block'),word.get('paragraph'),word.get('line'))] if ocr_result else [w for w in words if abs(w['top']-word['top'])<3]
                if any(word['x0']-50<w['x0']<word['x0']-8 for w in same_line if w['text'].strip('()') not in ('•','-')):continue
                next_y=min([other['top'] for other in code_words if other['top']>word['top']+5 and abs(other['x0']-word['x0'])<35] or [layout_height-24])
                right=min([other['x0']-4 for other in code_words if other['x0']>word['x0']+50 and abs(other['top']-word['top'])<80] or [layout_width-20])
                if ocr_result:
                    block_words=[w for w in words if w.get('block')==word.get('block')]
                    anchor_top=min(w['top'] for w in same_line) if same_line else word['top']
                    selected=[w for w in block_words if w['top']>=anchor_top-1 and w['top']<next_y-1 and w['x1']<=right]
                else:selected=[w for w in words if w['top']>=word['top']-2 and w['bottom']<=next_y+1 and w['x0']>=word['x0']-8 and w['x1']<=right]
                from geometry import words_text
                segment=words_text(selected)
                if source.get('glyph_replacements'):
                    segment=decode_source_text(source,page.get_text('text',clip=fitz.Rect(word['x0']-8,word['top']-2,right,next_y),sort=False))
                for code,text,raw in candidates_from_cell(segment, source=source):
                    if len(text)>3500: continue
                    item=make_item(source,code,text,page_number,'pymupdf-coordinate-candidate',f'anchor:{word_index}/y:{round(word["top"],2)}',quality='pending_layout_review')
                    item['extraction_flags']=['ocr_layout_requires_documentary_review' if ocr_result else 'unruled_layout_requires_review']
                    item['evidence'][0]['bbox']=[word['x0']-8,word['top']-2,right,next_y]
                    page_items.append(item)
        from geometry import declared_columns,recover_missing_columns,words_from_page
        declared,matched_rules=declared_columns(source,page_number,page,page_words,CODE_ANY,make_item,clean_text)
        if matched_rules:
            page_items=[item for item in page_items if not item.get('code')] + declared
        else:
            recovered_items=recover_missing_columns(source,page_number,page,page_words,tables,page_items,CODE_ANY,make_item,clean_text)
            page_items.extend(recovered_items)
        for recovered in page_items:
            if 'code_only_waiting_page_continuation' in recovered.get('extraction_flags',[]):
                box=recovered['evidence'][0].get('bbox')
                if box:open_cells[(round(box[0]/10),round(box[2]/10))]={'page':page_number,'item':recovered}
        if source['id']=='rj-em-curriculo-referencial' and re.search(r'Habilidades? de[^\n]*:',plain,re.IGNORECASE):
            page_items=[]
            for candidate_index,(code,text,raw) in enumerate(candidates_from_cell(plain,source=source)):
                item=make_item(source,code,text,page_number,'labelled-objective-paragraph',f'labelled-code:{candidate_index}',quality='labelled_source_paragraph_checked')
                page_items.append(item)
        if region_rule:
            page_items=[item for item in page_items if all(not evidence.get('bbox') or any(evidence['bbox'][0]>=region[0]-1 and evidence['bbox'][1]>=region[1]-1 and evidence['bbox'][2]<=region[2]+1 and evidence['bbox'][3]<=region[3]+1 for region in region_rule['regions']) for evidence in item['evidence'])]
        for item in page_items:
            for evidence in item['evidence']:
                evidence['page_normalization']=page_normalization
                if ocr_result and evidence.get('bbox'):
                    evidence['ocr_upright_bbox']=evidence['bbox']
                    evidence['bbox']=list(fitz.Rect(evidence['bbox'])*fitz.Matrix(ocr_result['layout_to_original']))
                    evidence['coordinate_space']='original_pdf_display_after_ocr_inverse_transform'
        distinct={}
        for item in page_items:
            evidence=item['evidence'][0];box=evidence.get('bbox')
            locator=tuple(round(number,1) for number in box) if box else evidence.get('locator')
            key=(item['code'],item['text'],locator)
            if key in distinct:
                previous=distinct[key]
                previous.setdefault('occurrence_locators',[previous['evidence'][0].get('locator')]).append(evidence.get('locator'))
                for position in item['positions']:
                    if position not in previous['positions']:previous['positions'].append(position)
            else:distinct[key]=item
        items.extend(distinct.values())
        if page_number % 50 == 0: log('extract_progress',source_id=source['id'],page=page_number,pages=len(document),items=len(items))
    # Preserve uncoded documentary sections separately; do not fabricate official codes/learning types.
    for page in pages:
        if len(page['text'].strip())>=100:
            text=page['text'].strip()
            item=make_item(source,None,text,page['page'],'pymupdf-page-section','page-section',quality='pending_structure_review')
            item['extraction_flags']=['uncoded_documentary_section_not_classified_learning']
            items.append(item)
    result={'source_id':source['id'],'sha256':digest,'extraction_revision':EXTRACTION_REVISION,'pages':pages,'items':items,'warnings':warnings,'table_count':table_count,'page_count':len(pages),'document_page_count':len(document),'code_mentions':sum(p['code_mentions'] for p in pages),'coded_items':sum(i['code'] is not None for i in items),'extracted_at':now(),'reconciliation_status':'pending_documentary_reconciliation','source_text_decoding':source.get('glyph_replacements',[]),'ocr_pending':any(p.get('ocr_required') and not p.get('ocr_completed') for p in pages)}
    result['extraction_config_sha256']=config_hash
    write_json(cache_path,result)
    log('extract_complete',source_id=source['id'],pages=len(pages),items=len(items),warnings=len(warnings))
    return result


def evidence_check(item, extracted, pdf=None):
    pages={p['page']:p for p in extracted['pages']}
    fragments=[]
    for evidence in item.get('evidence',[]):
        page=pages.get(evidence.get('page'))
        if not page:return False
        excerpt=evidence.get('excerpt','')
        if evidence.get('ocr_reference_path'):
            proof_path=safe_path(evidence['ocr_reference_path'])
            if not proof_path.exists() or proof_path.stat().st_size>32*1024*1024 or sha_file(proof_path)!=evidence.get('ocr_reference_sha256'):return False
            proof=json.loads(proof_path.read_text())
            if proof.get('artifact_sha256') and proof['artifact_sha256']!=extracted['sha256']:return False
            if proof.get('page') and proof['page']!=evidence['page']:return False
            proof_text=proof.get('text')
            if proof_text is None:
                from geometry import words_text
                proof_words=[]
                for word in proof.get('words',[]):
                    if word.get('bbox'):
                        box=word['bbox'];proof_words.append({'x0':box[0],'top':box[1],'x1':box[2],'bottom':box[3],'text':word['text'],'line':str(word.get('line',0)),'block':0})
                    else:proof_words.append(word)
                proof_text=words_text(proof_words)
            if normalize(excerpt) not in normalize(proof_text):return False
            fragments.append(excerpt)
            continue
        if evidence.get('method')=='pymupdf-rendered-glyph-trace-v1':
            if pdf is None or not evidence.get('bbox'):return False
            from geometry import normalize_native_page
            from ms_glyphs import rendered_glyph_text
            actual_page=pdf[evidence['page']-1]
            normalize_native_page(actual_page)
            visible=rendered_glyph_text(actual_page,evidence['bbox'],color_policy=evidence.get('glyph_color_policy'))
            if normalize(excerpt) not in normalize(visible):return False
            fragments.append(excerpt)
            continue
        if normalize(excerpt) not in normalize(page['text']):
            if pdf is None or not evidence.get('bbox'):return False
            import pymupdf as fitz
            actual_page=pdf[evidence['page']-1]
            from geometry import normalize_native_page,words_from_page,clipped_words,words_text
            normalize_native_page(actual_page)
            box=fitz.Rect(evidence['bbox'])+(-1,-1,1,1)
            clipped=actual_page.get_text('text',clip=box,sort=not bool(extracted.get('source_text_decoding')))
            for mapping in extracted.get('source_text_decoding',[]):clipped=clipped.replace(mapping['from'],mapping['to'])
            if evidence.get('method')=='pymupdf-rendered-glyph-trace-v1':
                from ms_glyphs import rendered_glyph_text
                clipped=rendered_glyph_text(actual_page,list(box),color_policy=evidence.get('glyph_color_policy'))
            if normalize(excerpt) not in normalize(clipped):
                actual_words=clipped_words(words_from_page(actual_page),box.x0,box.y0,box.x1,box.y1)
                clipped=words_text(actual_words)
                if normalize(excerpt) not in normalize(clipped):
                    typography=item.get('primary_typographic_equivalence')
                    def typographic(value):return re.sub(r'[\s\-\u00ad\u2010\u2011]','',unicodedata.normalize('NFKD',value).casefold())
                    if not isinstance(typography,dict) or not typography.get('method') or not typography.get('evidence') or typographic(excerpt) not in typographic(clipped):return False
        if evidence.get('evidence_role')!='code_locator':fragments.append(excerpt)
    if not fragments:return False
    primary=pages[item['evidence'][0]['page']]['text']
    code=item.get('code')
    if code and code not in primary and code not in re.sub(r'\s+','',primary):return False
    return normalize(' '.join(fragments))==normalize(item['text'])


def finalize_items(items,sources):
    source_by_id={s['id']:s for s in sources}
    ordinals=collections.Counter()
    finalized=[]
    for original in items:
        item=dict(original)
        source=source_by_id.get(item['source_id'])
        if not source or source.get('include_in_corpus') is False or source.get('publication_eligible') is False:continue
        if not item.get('text','').strip():continue
        if item.get('code') and item['evidence'][0].get('page') in source.get('non_curricular_code_pages',[]):continue
        authority=source.get('adapter_authority',{})
        section_range=authority.get('uncoded_page_sections_pages')
        if section_range and len(section_range)==2 and not item.get('document_specific_adapter') and item['evidence'][0].get('method')=='pymupdf-page-section' and section_range[0]<=item['evidence'][0].get('page',0)<=section_range[1]:continue
        reference_range=authority.get('generic_coded_reference_pages')
        if reference_range and len(reference_range)==2 and item.get('code') and not item.get('document_specific_adapter') and reference_range[0]<=item['evidence'][0].get('page',0)<=reference_range[1]:
            item['kind']='referencia_no_documento'
            item['positions']=[]
            item['position_unknown_reason']='Código citado em orientações/atividades, não definição de aprendizagem; capacidades locais estão no adaptador documental.'
        authority_range=authority.get('coded_learning_pages')
        if authority_range and len(authority_range)==2 and item.get('code') and not item.get('document_specific_adapter') and authority_range[0]<=item['evidence'][0].get('page',0)<=authority_range[1]:continue
        evidence=item.get('evidence',[])
        if not evidence: continue
        page=evidence[0].get('page')
        locator=evidence[0].get('locator') or evidence[0].get('section') or 'document'
        key=(item['source_id'],page,locator,item.get('code'))
        ordinal=ordinals[key];ordinals[key]+=1
        if not item.get('source_dataset') and not item.get('structural_key'):
            token=f'{item["source_id"]}|{page}|{locator}|{item.get("code") or "uncoded"}|occurrence:{ordinal}'
            item['id']=f'ca:{item["source_id"]}:{sha_bytes(token.encode())[:20]}'
        item['normalized_text']=normalize(item['text'])
        if not item.get('document_specific_adapter') and not item.get('source_dataset'):
            item['technical_validation_status']='source_locator_available_documentary_validation_pending'
        if item.get('code'):item['code_search_form']=re.sub(r'\s+','',item['code'])
        positions=[dict(p) for p in item.get('positions',[]) if p.get('stage') in source.get('stages',[])]
        for position in positions:
            if not item.get('document_specific_adapter') and position.get('stage')=='EM' and not position.get('component') and item.get('code') and re.search(r'EM\d{2}LP\d{2}',item['code']):position['component']='Língua Portuguesa'
        for context in source.get('position_contexts',[]):
            start=context.get('page_start',context.get('page',0));end=context.get('page_end',start)
            if start<=page<=end and (not context.get('code') or context['code']==item.get('code')):
                explicit={k:context.get(k) for k in ('stage','component','area','years','year_label','age_group','period')}
                if explicit.get('stage'):
                    explicit.update(position_origin='source_document_context',position_evidence=context.get('evidence'))
                    positions=[explicit]
        if item.get('code'):
            for rule in source.get('code_rules',[]):
                pattern=rule.get('pattern','')
                if not pattern or len(pattern)>500:continue
                match=re.fullmatch(pattern,item['code'])
                if not match:continue
                if rule.get('position_from_national_code') and positions:
                    for position in positions:position.update(position_origin='documented_source_code_rule',position_evidence=rule.get('evidence'),position_rule_id=rule.get('id'))
                if rule.get('position_year_group') and positions:
                    group=str(match.group(int(rule['position_year_group'])))
                    if group.isdigit() and 1<=int(group)<=12:
                        for position in positions:position.update(years=[int(group)],year_label=f'{int(group)}º ano',position_origin='documented_source_code_rule',position_evidence=rule.get('evidence'),position_rule_id=rule.get('id'))
        item['positions']=positions
        if item.get('kind')=='secao_normativa':
            for section in source.get('structure_sections',[]):
                start=section.get('page_start',section.get('page',0));end=section.get('page_end',start)
                if start<=page<=end and section.get('stage'):
                    positions=[{k:section.get(k) for k in ('stage','component','area','years','year_label','age_group','period')}]
                    positions[0]['position_origin']='explicit_document_section_heading'
                    item['positions']=positions
                    item['source_section']=section.get('title') or section.get('section')
                    break
        if not positions:
            item['position_unknown_reason']='Posicionamento não explicitado/estruturado neste trecho; nenhum ano ou etapa atribuído por suposição.'
            if item.get('code') and item.get('kind') in ('habilidade','objetivo_aprendizagem'):item['kind']='referencia_no_documento'
        for event in item.get('review_events',[]):
            if not event.get('at'):event['at']=source.get('collected_at')
        finalized.append(item)
    return finalized


def source_uncoded_items(sources,extracts):
    import pymupdf as fitz
    items=[]
    for source in sources:
        relative=source.get('uncoded_items_path')
        if not relative or source.get('include_in_corpus') is False:continue
        raw_adapter=json.loads(safe_path(relative).read_text())
        if isinstance(raw_adapter,list):
            adapter={'source_id':source['id'],'artifact_sha256':source.get('sha256'),'actor_type':'automated','actor_id':'document-specific-source-adapter','items':[record for record in raw_adapter if record.get('source_id')==source['id']]}
        else:adapter=raw_adapter
        if adapter.get('source_id')!=source['id'] or adapter.get('artifact_sha256')!=source.get('sha256'):raise ValueError('Uncoded adapter source/hash mismatch')
        extracted=extracts.get(source['id'])
        if not extracted:continue
        if source.get('glyph_replacements'):extracted['source_text_decoding']=source['glyph_replacements']
        with fitz.open(safe_path(source['local_path'])) as document:
            for record in adapter.get('items',[]):
                if record.get('artifact_sha256',source.get('sha256'))!=source.get('sha256'):raise ValueError('Uncoded item artifact hash mismatch')
                item=make_item(source,record.get('code'),record['text'],record['page'],'document-specific-uncoded-adapter',record['locator'],quality='literal_text_and_explicit_context_checked')
                item['kind']=record['kind'];item['positions']=record.get('positions',[])
                item['document_specific_adapter']=True
                for field in ('source_number','title','source_dataset','primary_typographic_equivalence','source_right_label'):
                    if field in record:item[field]=record[field]
                if record.get('key'):
                    item['structural_key']=record['key']
                    item['id']=f'ca:{source["id"]}:section:{record["key"]}'
                    item['parent_id']=f'ca:{source["id"]}:section:{record["parent_key"]}' if record.get('parent_key') else None
                item['evidence']=record.get('evidence') or item['evidence']
                item['evidence'][0]['locator']=record['locator']
                item['source_context']=record.get('source_context')
                if record.get('parent_id'):item['parent_id']=record['parent_id']
                if record.get('parent_key'):item['parent_id']=f'ca:{source["id"]}:section:{record["parent_key"]}'
                if item['positions']:item.pop('position_unknown_reason',None)
                item['technical_validation_status']=record.get('technical_validation_status','literal_text_and_explicit_context_checked')
                item['publication_status']='source_attributed'
                item['review_events']=[{'actor_type':record.get('actor_type',adapter.get('actor_type','automated')),'actor_id':record.get('actor_id',adapter.get('actor_id','document-adapter')),'method':record.get('extraction_method',adapter.get('method')),'at':adapter.get('generated_at') or source.get('collected_at'),'result':'literal_source_context_verified'}]
                if not evidence_check(item,extracted,document):raise ValueError(f'Uncoded adapter text/code/page verification failed: {source["id"]} {record["locator"]}')
                items.append(item)
    return items


def attach_hierarchy(items,sources):
    by_source_code={(item['source_id'],item['code']):item for item in items if item.get('code')}
    nodes={(item['source_id'],item['structural_key']):item for item in items if item.get('structural_key')}
    for item in items:
        for alias in item.get('code_aliases',[]):by_source_code[(item['source_id'],alias)]=item
    for source in sources:
        if not source.get('uncoded_items_path'):continue
        adapter=json.loads(safe_path(source['uncoded_items_path']).read_text())
        if not isinstance(adapter,dict):continue
        for link in adapter.get('item_parent_links',[]):
            item=by_source_code.get((source['id'],link['code']))
            parent=nodes.get((source['id'],link['parent_key']))
            if not item or not parent:raise ValueError(f'Unresolved structural parent: {source["id"]} {link["code"]}')
            item['parent_id']=parent['id']
            item['structural_context_ids']=[nodes[(source['id'],key)]['id'] for key in link.get('context_keys',[]) if (source['id'],key) in nodes]
            item['structural_competency_ids']=[nodes[(source['id'],key)]['id'] for key in link.get('competency_keys',[]) if (source['id'],key) in nodes]
            item['hierarchy_evidence']=link.get('evidence')
            item['hierarchy_origin']='declared_document_structure'
    return items


def relations_for(items,sources):
    nationals=collections.defaultdict(list)
    source_by_id={source['id']:source for source in sources}
    for item in items:
        if item['uf']=='BR' and item['code']:nationals[item['code']].append(item)
    groups={}
    for item in items:
        if item['uf']=='BR' or not item['code'] or item.get('kind')=='referencia_no_documento':continue
        source=source_by_id[item['source_id']]
        declarations=[]
        if item['code'] in nationals:
            declarations.append({'rule_id':'literal-national-code','national_code':item['code'],'relation_type':'referencia_nacional','origin':'declaracao_fonte','evidence':item['evidence'],'scope':'Literal national-code reference only; equivalence, coverage union and prerequisite not asserted.'})
        for rule in source.get('code_rules',[]):
            if rule.get('mapping_allowed') is False or not rule.get('national_code_group') or not rule.get('evidence'):continue
            pattern=rule.get('pattern','')
            if not pattern or len(pattern)>500:continue
            match=re.fullmatch(pattern,item['code'])
            if not match:continue
            target=match.group(int(rule['national_code_group']))
            if target not in nationals:continue
            declarations.append({'rule_id':rule['id'],'national_code':target,'relation_type':rule.get('relation_type','relacao_generica'),'origin':'regra_fonte','evidence':[rule['evidence']],'scope':rule.get('scope','Source-declared code rule; no full equivalence inferred.')})
        for declaration in declarations:
            for national in nationals[declaration['national_code']]:
                key=(source['id'],declaration['rule_id'],national['id'],declaration['relation_type'])
                if key not in groups:
                    rid='ca:relation:'+sha_bytes('|'.join(key).encode())[:24]
                    groups[key]={'id':rid,'members':[{'item_id':national['id'],'role':'target','scope':'national reference item'}],'relation_type':declaration['relation_type'],'origin':declaration['origin'],'technical_validation_status':'literal_code_checked' if declaration['rule_id']=='literal-national-code' else 'documented_source_rule_applied','pedagogical_review_status':'not_reviewed','publication_status':'documented_reference','method':MAPPING_REVISION,'rule_id':declaration['rule_id'],'evidence':declaration['evidence'],'scope':declaration['scope'],'review_events':[{'actor_type':'automated','actor_id':'curriculos-abertos:documented-code-rules','method':MAPPING_REVISION,'at':item['review_events'][0].get('at'),'result':'documented_reference_without_equivalence'}]}
                relation=groups[key]
                relation['members'].append({'item_id':item['id'],'role':'source','scope':declaration['scope']})
    from correspondence import documentary_links,lexical_candidates
    documented=list(groups.values())+documentary_links(items,sources)
    return documented+lexical_candidates(items,documented,normalize)


def expected_source_parts(source):
    parts=[{'source_id':source['id'],'part':part,'edition':source.get('edition')} for part in (source.get('normative_parts') or ['inventário detalhado de partes pendente'])]
    for related in source.get('expected_related_documents',[]):
        if related.get('mandatory',True) and related.get('status') not in ('processed_reconciled','resolved'):
            parts.append({'source_id':source['id'],'part':'Documento curricular obrigatório referenciado: '+related['title'],'edition':related.get('edition'),'required_related_document_pending':True,'evidence':related.get('evidence'),'reason':related.get('reason')})
    return parts


def coverage_for(sources, extracts, items, relations):
    by_source=collections.defaultdict(list)
    for item in items: by_source[item['source_id']].append(item)
    relation_index=collections.defaultdict(set)
    relation_by_id={r['id']:r for r in relations}
    for relation in relations:
        for member in relation['members']: relation_index[member['item_id']].add(relation['id'])
    result=[]
    for uf in UFS:
        for stage in STAGES:
            scoped=[s for s in sources if s.get('uf')==uf and stage in s.get('stages',[]) and s.get('mandatory',True)]
            components=sorted({c for s in scoped for c in s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])})
            if not components or any(not s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else []) for s in scoped):components.append(None)
            for component in components:
                source_ids=[s['id'] for s in scoped if (component is None and not s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])) or component in s.get('stage_component_inventory',{}).get(stage,s.get('components',[]) if len(s.get('stages',[]))==1 else [])]
                stage_items=[i for sid in source_ids for i in by_source[sid] if any(p.get('stage')==stage and (component is None or p.get('component')==component or p.get('area')==component) for p in i.get('positions',[]))]
                expected=[part for s in scoped if s['id'] in source_ids for part in expected_source_parts(s)]
                processed=[x for x in expected if x['source_id'] in extracts and not x.get('required_related_document_pending') and not extracts[x['source_id']].get('ocr_pending')]
                # Reconciliation evidence must exist independently, keyed to exact artifact hash.
                reconciled=[]
                for entry in processed:
                    file=ROOT/'data/manifests/reconciliation'/f'{entry["source_id"]}.json'
                    if not file.exists(): continue
                    record=json.loads(file.read_text())
                    extracted=extracts[entry['source_id']]
                    record_revision=record.get('target_publication_extraction_revision') or record.get('publication_extraction_revision') or record.get('extraction_revision')
                    if record_revision!=EXTRACTION_REVISION or record.get('source_id')!=entry['source_id'] or not record.get('method') or not record.get('actor_id') or record.get('actor_type') not in ('automated','human'):continue
                    actual_item_ids={item['id'] for item in by_source[entry['source_id']]}
                    for part in record.get('parts',[]):
                        if part.get('name')==entry['part'] and record.get('artifact_sha256')==extracted['sha256'] and part.get('expected_item_ids')==part.get('verified_item_ids') and part.get('expected_item_ids') and set(part['verified_item_ids']).issubset(actual_item_ids) and part.get('evidence') and not part.get('findings'):
                            reconciled.append(entry)
                relation_ids={rid for item in stage_items for rid in relation_index[item['id']]}
                applicable_relations=[relation_by_id[rid] for rid in relation_ids]
                errors=[{'source_id':s['id'],'error':s.get('processing_error')} for s in scoped if s.get('processing_error')]
                pending=[]
                if not scoped: pending.append('Inventário oficial deste recorte não concluído')
                if len(processed)<len(expected): pending.append('Documentos/partes obrigatórias não processados')
                if len(reconciled)<len(expected) or not expected: pending.append('Reconciliação documental por parte não concluída')
                if len(reconciled)<len(expected) and any(i.get('extraction_flags') for i in stage_items): pending.append('Candidatos com fronteiras/estrutura pendentes de revisão')
                result.append({'uf':uf,'stage':stage,'component':component,'source_ids':source_ids,'editions':sorted({s.get('edition') or 'edição não confirmada' for s in scoped}),'expected_parts':expected,'processed_parts':processed,'reconciled_parts':reconciled,'expected_parts_count':len(expected),'processed_parts_count':len(processed),'reconciled_parts_count':len(reconciled),'item_count':len(stage_items),'learning_types':dict(collections.Counter(i['kind'] for i in stage_items)),'items_with_evidence':sum(bool(i['evidence']) for i in stage_items),'relations':dict(collections.Counter(r['origin'] for r in applicable_relations)),'relation_types':dict(collections.Counter(r['relation_type'] for r in applicable_relations)),'review_statuses':dict(collections.Counter(r['pedagogical_review_status'] for r in applicable_relations)),'critical_errors':errors,'pending':pending,'editorial_completeness':'reconciled' if expected and len(reconciled)==len(expected) and not pending else 'pending','technical_verification':'partial' if processed else 'not_processed','mapping_coverage':'literal_code_references_only','reconciled':bool(expected and len(reconciled)==len(expected) and not pending),'ready':bool(expected and len(reconciled)==len(expected) and not pending),'denominator_definition':'Mandatory source parts identified in the independent source inventory; source inventory itself remains pending until documented reconciliation.'})
    return result


def stratified_samples(items, extracts):
    strata=collections.defaultdict(list)
    for item in items:
        for position in item.get('positions',[]): strata[(item['uf'],position['stage'],position.get('component') or position.get('area'))].append(item)
    samples=[]
    for key, candidates in sorted(strata.items(),key=lambda pair:str(pair[0])):
        ordered=sorted(candidates,key=lambda item:sha_bytes(item['id'].encode()))
        chosen=ordered[:min(3,len(ordered))]
        # include first/last document occurrence to expose multipage boundary risks
        chosen.extend(sorted(candidates,key=lambda i:(i['source_id'],i['evidence'][0]['page']))[:1])
        chosen.extend(sorted(candidates,key=lambda i:(i['source_id'],i['evidence'][0]['page']))[-1:])
        for item in {i['id']:i for i in chosen}.values():
            samples.append({'uf':key[0],'stage':key[1],'component':key[2],'item_id':item['id'],'source_id':item['source_id'],'page':item['evidence'][0]['page'],'code':item['code'],'literal_text_in_page':evidence_check(item,extracts[item['source_id']]),'actor_type':'automated','actor_id':'curriculos-abertos:deterministic-page-check','method':'stratified-hash-first-last-v1','scope':'Literal text/code location only; no visual table or pedagogical validation claimed','extraction_flags':item.get('extraction_flags',[])})
    return samples


def ingest(args):
    sources=load_sources()
    if not sources: raise ValueError('No registered sources. Source inventory is required before ingestion.')
    selected=[s for s in sources if (not args.source or s['id']==args.source) and (not args.uf or s['uf']==args.uf)]
    if not selected: raise ValueError('Selected source/UF was not registered')
    job_id=args.job_id or 'ingest-'+dt.datetime.now().strftime('%Y%m%dT%H%M%S')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',job_id): raise ValueError('Invalid job ID')
    checkpoint_path=ROOT/'var/jobs'/f'{job_id}.json'
    checkpoint=json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {'id':job_id,'created_at':now(),'completed':[],'errors':{},'state':'running'}
    checkpoint['state']='running'; write_json(checkpoint_path,checkpoint)
    downloader=SafeDownloader(sources)
    extracts={}
    for source in selected:
        if source.get('include_in_corpus') is False: continue
        if STOP:
            checkpoint['state']='paused';write_json(checkpoint_path,checkpoint);return 75
        try:
            log('source_started',job_id=job_id,source_id=source['id'])
            local=source.get('local_path')
            path=safe_path(local) if local else None
            if (not path or not path.exists()) and args.cached_only:
                source['processing_error']='Artifact not acquired; cached-only packaging did not attempt network'
                continue
            if not path or not path.exists():
                path,update=downloader.acquire(source)
                source.update(update)
            else:
                source['sha256']=source.get('sha256') or sha_file(path)
            if args.cached_only:
                cache=ROOT/'data/extracted'/f'{sha_file(path)}-{EXTRACTION_REVISION}.json'
                if not cache.exists():
                    source['processing_error']='Local artifact acquired; extraction pending in batch worker'
                    continue
                extracted=json.loads(cache.read_text())
                if extracted.get('extraction_config_sha256')!=extraction_config_hash(source):
                    source['processing_error']='Extraction config changed; reprocessing required before packaging'
                    continue
            else:
                extracted=extract_pdf(source,path,force=args.force)
            source['sha256']=extracted['sha256'];source['status']='extracted_pending_reconciliation'
            source['extraction']={'revision':EXTRACTION_REVISION,'page_count':extracted['page_count'],'code_mentions':extracted['code_mentions'],'coded_items':extracted['coded_items'],'reconciliation_status':extracted['reconciliation_status']}
            extracts[source['id']]=extracted
            checkpoint['completed']=sorted(set(checkpoint['completed']+[source['id']]))
            checkpoint['errors'].pop(source['id'],None)
            write_json(checkpoint_path,checkpoint)
        except InterruptedError:
            checkpoint['state']='paused';write_json(checkpoint_path,checkpoint);return 75
        except Exception as error:
            source['processing_error']=str(error);source['status']='processing_failed'
            checkpoint['errors'][source['id']]=str(error)
            write_json(checkpoint_path,checkpoint)
            log('source_failed',job_id=job_id,source_id=source['id'],error=str(error))
    # Always use all available cached sources for consistent national candidate, not only selected source.
    for source in sources:
        if source.get('include_in_corpus') is False: continue
        if source['id'] in extracts: continue
        local=source.get('local_path')
        if not local: continue
        path=safe_path(local)
        if not path.exists(): continue
        digest=sha_file(path)
        cached=ROOT/'data/extracted'/f'{digest}-{EXTRACTION_REVISION}.json'
        if cached.exists():
            record=json.loads(cached.read_text())
            if record.get('extraction_config_sha256')==extraction_config_hash(source):extracts[source['id']]=record
    items=[]
    for source_id,extracted in sorted(extracts.items()): items.extend(extracted['items'])
    if not items:raise ValueError('No valid extraction cache available; existing candidate/publication left untouched')
    items.extend(source_uncoded_items(sources,extracts))
    items=finalize_items(items,sources)
    items=attach_hierarchy(items,sources)
    ids=[i['id'] for i in items]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate canonical item IDs detected')
    relations=relations_for(items,sources)
    coverage=coverage_for(sources,extracts,items,relations)
    samples=stratified_samples(items,extracts)
    # Streamed, sharded distribution avoids a national string exceeding runtime limits.
    from distribution import write_publication
    metadata={'schema_version':SCHEMA_VERSION,'created_at':checkpoint['created_at'],'extraction_revision':EXTRACTION_REVISION,'mapping_revision':MAPPING_REVISION,'schema_path':'data/schema/1.0.0.json','schema_sha256':sha_file(ROOT/'data/schema/1.0.0.json'),'sources':sources,'coverage':coverage,'publication_kind':'incomplete_documentary_candidate','national_release_ready':all(row['ready'] for row in coverage),'coverage_statement':'Extração real; completude e reconciliação são estados independentes. Seções documentais sem código não são habilidades inventadas.','changelog':[{'type':'initial_source_collection','description':'Primeira coleta destas edições, sem inventar histórico oficial anterior.'},{'type':'extraction_revision','revision':EXTRACTION_REVISION,'description':'Revisão identificada de extração/identificadores, regras documentadas e geometria. Não representa alteração oficial de currículo.'}],'verification':{'samples':samples,'verifier_type':'automated','human_pedagogical_review':False},'rights':{'code':'MIT','project_metadata':'CC0-1.0 only where rights are held by project','third_party_materials':'Original source rights retained; no blanket relicensing; source PDFs are not redistributed.','licensed_dataset':'bncc-dev/bncc-dados CC-BY-4.0 attribution retained on reused records.'}}
    bundle,bundle_path,digest,pointer=write_publication(ROOT,metadata,items,relations)
    identity=bundle['id']
    write_json(ROOT/'data/coverage-manifest.json',{'publication':identity,'generated_at':now(),'national_release_ready':bundle['national_release_ready'],'ufs_ready':sorted({r['uf'] for r in coverage if all(row['ready'] for row in coverage if row['uf']==r['uf'])}),'coverage':coverage})
    write_json(ROOT/'docs/evidence/data-samples.json',{'publication':identity,'samples':samples,'scope':'Automated literal page verification only; visual/documentary reconciliation remains separate.'})
    write_json(ROOT/'docs/evidence/ingestion-summary.json',{'publication':identity,'bundle_sha256':digest,'distribution_format':bundle.get('format'),'compressed_bytes':pointer.get('total_compressed_bytes'),'decoded_bytes':pointer.get('total_decoded_bytes'),'sources_registered':len(sources),'sources_extracted':len(extracts),'items':len(items),'coded_items':sum(bool(i['code']) for i in items),'relations':len(relations),'errors':checkpoint['errors'],'national_release_ready':bundle['national_release_ready'],'created_at':now(),'job_id':job_id})
    report=['# Cobertura documental real',f'\nPublicação candidata: `{identity}`. Fontes registradas: {len(sources)}; processadas: {len(extracts)}; registros: {len(items)}; relações de referência literal: {len(relations)}.', '\nUma extração não significa reconciliação. Nenhuma parte é marcada pronta só por conter registros. Códigos não determinam equivalência.', '\n| UF | Fontes | Itens codificados | EI/EF/EM | Reconciliação |','|---|---:|---:|---|---|']
    for uf in UFS:
        scoped=[s for s in sources if s['uf']==uf]
        stages=', '.join(stage+': '+str(sum(1 for i in items if i['uf']==uf and i['code'] and any(p['stage']==stage for p in i['positions']))) for stage in STAGES)
        report.append(f'| {uf} | {len(scoped)} | {sum(i["uf"]==uf and bool(i["code"]) for i in items)} | {stages} | pendente |')
    (ROOT/'docs/data-coverage.md').write_text('\n'.join(report)+'\n')
    checkpoint.update(state='completed_with_errors' if checkpoint['errors'] else 'completed',publication=identity,artifact=str(bundle_path.relative_to(ROOT)),artifact_sha256=digest,validation=pointer.get('validation'),finished_at=now());write_json(checkpoint_path,checkpoint)
    log('candidate_written',job_id=job_id,publication=identity,path=str(bundle_path.relative_to(ROOT)),sha256=digest,items=len(items),relations=len(relations),national_release_ready=bundle['national_release_ready'])
    return 1 if checkpoint['errors'] else 0


def sources_check(args):
    sources=load_sources();selected=[s for s in sources if not args.source or s['id']==args.source]
    job_id=args.job_id or 'monitor-'+dt.datetime.now().strftime('%Y%m%dT%H%M%S')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',job_id):raise ValueError('Invalid monitor job ID')
    downloader=SafeDownloader(sources)
    latest_path=ROOT/'var/source-monitor/latest.json'
    report_path=ROOT/'var/source-monitor'/f'{job_id}.json'
    previous=json.loads(latest_path.read_text()) if latest_path.exists() else {'sources':[]}
    previous_by={s['source_id']:s for s in previous.get('sources',[])}
    if report_path.exists():
        existing=json.loads(report_path.read_text())
    else:existing={'sources':[],'started_at':now()}
    checks=list(existing['sources']);completed={c['source_id'] for c in checks if c.get('status')!='unavailable'}
    checks=[c for c in checks if c.get('status')!='unavailable']
    tasks_path=ROOT/'var/source-monitor/tasks.json'
    tasks=json.loads(tasks_path.read_text()) if tasks_path.exists() else []
    task_ids={t['id'] for t in tasks}
    def persist(state):
        report={'job_id':job_id,'started_at':existing['started_at'],'checked_at':now(),'state':state,'sources':checks,'publication_changed':False,'policy':'Changes open evaluation tasks; never replace a published edition automatically.'}
        write_json(report_path,report);write_json(latest_path,report);write_json(tasks_path,tasks)
    persist('running')
    for source in selected:
        if STOP:persist('paused');return 75
        if source['id'] in completed:continue
        prior=previous_by.get(source['id'],{})
        headers={}
        if prior.get('etag'):headers['If-None-Match']=prior['etag']
        if prior.get('last_modified'):headers['If-Modified-Since']=prior['last_modified']
        try:
            response=downloader.request(source['artifact_url'],headers=headers)
            if response['status']==304:
                entry={**prior,'source_id':source['id'],'checked_at':now(),'status':'unchanged','http_status':304}
            else:
                digest=sha_bytes(response['body']);baseline=prior.get('sha256') or source.get('sha256')
                entry={'source_id':source['id'],'checked_at':now(),'sha256':digest,'baseline_sha256':baseline,'etag':response['headers'].get('etag'),'last_modified':response['headers'].get('last-modified'),'status':'content_changed_requires_review' if baseline and digest!=baseline else 'unchanged' if baseline else 'baseline_observed','http_status':200,'task_required':bool(baseline and digest!=baseline),'new_edition_confirmed':False}
        except InterruptedError:persist('paused');return 75
        except Exception as error:entry={'source_id':source['id'],'checked_at':now(),'status':'unavailable','error':str(error),'task_required':True,'new_edition_confirmed':False}
        if entry.get('task_required'):
            tid='source-evaluation-'+sha_bytes(canonical({'source_id':source['id'],'status':entry['status'],'sha256':entry.get('sha256'),'baseline':entry.get('baseline_sha256')}))[:20]
            if tid not in task_ids:
                tasks.append({'id':tid,'job_id':job_id,'source_id':source['id'],'created_at':now(),'status':'pending_evaluation','detected_change':entry,'publication_changed':False});task_ids.add(tid)
            entry['evaluation_task_id']=tid
        checks.append(entry);persist('running');log('source_check',job_id=job_id,**entry)
    persist('completed')
    return 1 if any(c['status']=='unavailable' for c in checks) else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('ingest','sources-check','extract'):
        action=sub.add_parser(name);action.add_argument('--source');action.add_argument('--uf',choices=UFS+['BR']);action.add_argument('--job-id');action.add_argument('--force',action='store_true');action.add_argument('--cached-only',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='extract':
            selected=[source for source in load_sources() if (not args.source or source['id']==args.source) and (not args.uf or source['uf']==args.uf) and source.get('include_in_corpus',True)]
            if not selected: raise ValueError('No registered source selected')
            for source in selected:
                if not source.get('local_path'): raise ValueError('Source artifact has not been acquired')
                extract_pdf(source,safe_path(source['local_path']),force=args.force)
            return 0
        return ingest(args) if args.command=='ingest' else sources_check(args)
    except Exception as error:
        if args.job_id and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',args.job_id):
            checkpoint=ROOT/'var/jobs'/f'{args.job_id}.json'
            if checkpoint.exists():
                state=json.loads(checkpoint.read_text());state.update(state='failed',error=str(error)[:2000],finished_at=now());write_json(checkpoint,state)
        log('fatal',error=str(error)[:2000]);return 1
if __name__=='__main__': raise SystemExit(main())
