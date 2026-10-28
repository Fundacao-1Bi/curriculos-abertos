#!/usr/bin/env python3
"""Acquire two pinned public runtime images over Registry v2, verify, and load locally.

This is a local-network fallback for a stalled daemon pull endpoint, not an access
control bypass. Only official public Docker Library repositories are accepted.
Anonymous pull tokens and CDN signatures remain in memory and never enter logs.
"""
from __future__ import annotations
import argparse
import datetime as dt
import gzip
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import socket
import subprocess
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'var/runtime-images'
REPORT = ROOT / 'docs/evidence/runtime-images.json'
REGISTRY = 'https://registry-1.docker.io'
ACCEPT = ', '.join(['application/vnd.oci.image.index.v1+json', 'application/vnd.docker.distribution.manifest.list.v2+json', 'application/vnd.oci.image.manifest.v1+json', 'application/vnd.docker.distribution.manifest.v2+json'])
SPECS = {
 'node': {'tag': '22.23.4-bookworm-slim', 'index': 'sha256:de170b39439eb0e5a3444ad7d60b015614a381e10fecae2e30ec9e735122f38d', 'version': 'v22.23.4', 'command': ['node','--version']},
 'postgres': {'tag': '17.11-bookworm', 'index': 'sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27', 'version': '17.11', 'command': ['postgres','--version']},
}
HEX = re.compile(r'^sha256:[a-f0-9]{64}$')
MAX_COMPRESSED = 512 * 1024 * 1024
MAX_UNPACKED = 1024 * 1024 * 1024
MAX_TOTAL_UNPACKED = 3 * 1024 * 1024 * 1024

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def emit(event, **fields): print(json.dumps({'at': now(), 'event': event, **fields}), flush=True)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024), b''):h.update(block)
 return 'sha256:'+h.hexdigest()
def safe_failure(error):
 if isinstance(error,urllib.error.HTTPError):return f'HTTP {error.code}'
 if isinstance(error,subprocess.TimeoutExpired):return 'Local Docker command exceeded its explicit timeout.'
 if isinstance(error,urllib.error.URLError):return 'TLS/network connection failed.'
 if isinstance(error,TimeoutError):return 'Network timeout.'
 # Never serialize a URL-bearing exception, token, subprocess environment, or CDN signature.
 return str(error) if isinstance(error,(ValueError,RuntimeError)) and '://' not in str(error) else type(error).__name__

def allowed_url(url):
 parsed=urllib.parse.urlsplit(url)
 if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('Runtime download requires HTTPS without userinfo.')
 host=parsed.hostname or ''
 if host not in ('registry-1.docker.io','auth.docker.io') and not host.endswith(('.docker.com','.docker.io','.cloudflarestorage.com','.cloudfront.net')):raise ValueError('Registry redirect host is outside the runtime allowlist.')
 for entry in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
  if not ipaddress.ip_address(entry[4][0]).is_global:raise ValueError('Runtime registry address is not public.')
 return parsed

class Redirects(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  allowed_url(newurl)
  redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
  if redirected and urllib.parse.urlsplit(newurl).hostname!=urllib.parse.urlsplit(req.full_url).hostname:
   redirected.remove_header('Authorization')
  return redirected

class Registry:
 def __init__(self,repo):
  self.repo=repo;self.token=None;self.deadline=time.monotonic()+600
  self.opener=urllib.request.build_opener(Redirects())
 def auth(self):
  scope=urllib.parse.quote(f'repository:library/{self.repo}:pull')
  url=f'https://auth.docker.io/token?service=registry.docker.io&scope={scope}'
  allowed_url(url)
  with self.opener.open(url,timeout=30) as response:
   data=response.read(1024*1024+1)
  if len(data)>1024*1024:raise ValueError('Anonymous token response exceeds limit.')
  self.token=json.loads(data)['token']
 def request(self,path):
  if time.monotonic()>self.deadline:raise RuntimeError('Runtime acquisition exceeded its 10 minute budget.')
  if self.token is None:self.auth()
  url=f'{REGISTRY}/v2/library/{self.repo}/{path}'
  allowed_url(url)
  req=urllib.request.Request(url,headers={'Authorization':'Bearer '+self.token,'Accept':ACCEPT,'User-Agent':'Curriculos-Abertos-runtime-acquisition/1.0'})
  return self.opener.open(req,timeout=45)
 def json(self,path,expected):
  if not HEX.fullmatch(expected):raise ValueError('Invalid expected manifest digest.')
  for attempt in range(3):
   try:
    with self.request(path) as response:
     data=response.read(4*1024*1024+1)
    if len(data)>4*1024*1024:raise ValueError('Runtime manifest exceeds 4 MiB limit.')
    if 'sha256:'+hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Runtime manifest digest mismatch.')
    return json.loads(data),data
   except (urllib.error.URLError,TimeoutError,OSError):
    if attempt==2:raise
    self.token=None;time.sleep(2**attempt)
 def blob(self,expected,size):
  if not HEX.fullmatch(expected) or not isinstance(size,int) or size<1 or size>MAX_COMPRESSED:raise ValueError('Invalid or oversized runtime blob.')
  path=CACHE/'blobs'/expected.split(':')[1]
  path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists() and path.stat().st_size==size and digest(path)==expected:return path
  for attempt in range(3):
   temporary=path.with_suffix('.tmp')
   try:
    count=0;h=hashlib.sha256()
    with self.request('blobs/'+expected) as response,temporary.open('wb') as target:
     while True:
      block=response.read(1024*1024)
      if not block:break
      count+=len(block)
      if time.monotonic()>self.deadline:raise RuntimeError('Runtime acquisition exceeded its 10 minute budget.')
      if count>size or count>MAX_COMPRESSED:raise ValueError('Runtime blob exceeds the declared limit.')
      h.update(block);target.write(block)
    if count!=size or 'sha256:'+h.hexdigest()!=expected:raise ValueError('Runtime blob size or digest mismatch.')
    temporary.replace(path);return path
   except (urllib.error.URLError,TimeoutError,OSError):
    if attempt==2:raise
    self.token=None;time.sleep(2**attempt)
   finally:temporary.unlink(missing_ok=True)

def docker(args,timeout=120):
 result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout,check=False)
 if result.returncode!=0:raise RuntimeError(f'Docker {args[0]} failed with exit {result.returncode}.')
 return result.stdout.strip()

def acquire(repo):
 spec=SPECS[repo];tag=repo+':'+spec['tag'];registry=Registry(repo)
 emit('runtime_index_fetch',repository=repo,tag=spec['tag'])
 index,index_raw=registry.json('manifests/'+spec['index'],spec['index'])
 candidates=[m for m in index.get('manifests',[]) if m.get('platform',{}).get('os')=='linux' and m.get('platform',{}).get('architecture')=='arm64' and m.get('platform',{}).get('variant') in (None,'v8')]
 if len(candidates)!=1:raise ValueError('Expected exactly one linux/arm64 runtime manifest.')
 selected=candidates[0];manifest_digest=selected['digest']
 manifest,manifest_raw=registry.json('manifests/'+manifest_digest,manifest_digest)
 config_info=manifest['config'];config_path=registry.blob(config_info['digest'],config_info['size'])
 config=json.loads(config_path.read_bytes())
 if config.get('os')!='linux' or config.get('architecture')!='arm64':raise ValueError('Runtime config platform does not match linux/arm64.')
 layers=manifest.get('layers',[]);diffs=config.get('rootfs',{}).get('diff_ids',[])
 if len(layers)!=len(diffs) or not layers or len(layers)>50:raise ValueError('Runtime layer/config count mismatch.')
 if sum(layer.get('size',MAX_COMPRESSED+1) for layer in layers)>MAX_COMPRESSED:raise ValueError('Runtime image exceeds 512 MiB total compressed limit.')
 work=CACHE/repo/spec['tag'];work.mkdir(parents=True,exist_ok=True)
 layer_names=[];total=0;layer_reports=[]
 for position,(layer,diff_id) in enumerate(zip(layers,diffs),1):
  if not HEX.fullmatch(diff_id):raise ValueError('Invalid uncompressed layer digest.')
  emit('runtime_layer_fetch',repository=repo,layer=position,layers=len(layers),compressed_bytes=layer['size'])
  compressed=registry.blob(layer['digest'],layer['size'])
  target=work/(diff_id.split(':')[1]+'.layer.tar')
  if not target.exists() or digest(target)!=diff_id:
   temporary=target.with_suffix('.tmp');h=hashlib.sha256();written=0
   media=layer.get('mediaType','')
   if 'gzip' not in media:raise ValueError('Runtime layer encoding is not the supported gzip format.')
   try:
    with gzip.open(compressed,'rb') as source,temporary.open('wb') as output:
     while True:
      block=source.read(1024*1024)
      if not block:break
      written+=len(block)
      if written>MAX_UNPACKED or total+written>MAX_TOTAL_UNPACKED:raise ValueError('Runtime layer exceeds uncompressed resource limit.')
      h.update(block);output.write(block)
    if 'sha256:'+h.hexdigest()!=diff_id:raise ValueError('Runtime uncompressed layer digest mismatch.')
    temporary.replace(target)
   finally:temporary.unlink(missing_ok=True)
  total+=target.stat().st_size
  if total>MAX_TOTAL_UNPACKED:raise ValueError('Runtime image exceeds total uncompressed size limit.')
  arcname=f'{diff_id.split(":")[1]}/layer.tar';layer_names.append((target,arcname))
  layer_reports.append({'compressed_sha256':layer['digest'],'compressed_bytes':layer['size'],'diff_id':diff_id,'uncompressed_bytes':target.stat().st_size})
 config_name=config_info['digest'].split(':')[1]+'.json'
 docker_manifest=[{'Config':config_name,'RepoTags':[tag],'Layers':[name for _,name in layer_names]}]
 docker_manifest_path=work/'manifest.json';docker_manifest_path.write_text(json.dumps(docker_manifest,separators=(',',':')))
 archive=work/'docker-image.tar'
 with tarfile.open(archive,'w') as output:
  output.add(config_path,arcname=config_name,recursive=False)
  output.add(docker_manifest_path,arcname='manifest.json',recursive=False)
  for path,arcname in layer_names:output.add(path,arcname=arcname,recursive=False)
 # An operator may have a locally modified image under an official-looking tag.
 # Refuse to replace that reference; other images, tags and containers are untouched.
 prior=subprocess.run(['docker','image','inspect',tag],capture_output=True,text=True,check=False,timeout=30)
 if prior.returncode==0:
  existing=json.loads(prior.stdout)[0]
  if existing.get('Architecture')!='arm64' or existing.get('Os')!='linux' or existing.get('RootFS',{}).get('Layers')!=diffs or existing.get('Config')!=config.get('config'):
   raise ValueError('An existing local runtime tag differs from the verified official image; it was preserved.')
 emit('runtime_docker_load',repository=repo,archive_bytes=archive.stat().st_size)
 loaded=docker(['load','--input',str(archive)],timeout=180)
 inspect=json.loads(docker(['image','inspect',tag]))[0]
 if inspect.get('Architecture')!='arm64' or inspect.get('Os')!='linux':raise ValueError('Loaded image architecture mismatch.')
 version=docker(['run','--rm','--network=none','--platform','linux/arm64',tag,*spec['command']],timeout=30)
 if spec['version'] not in version:raise ValueError('Loaded runtime version mismatch.')
 record={'repository':'library/'+repo,'tag':tag,'platform':'linux/arm64','index_digest':spec['index'],'manifest_digest':manifest_digest,'config_digest':config_info['digest'],'image_id':inspect['Id'],'repo_digests':inspect.get('RepoDigests',[]),'version_output':version,'layers':layer_reports,'archive':str(archive.relative_to(ROOT)),'archive_sha256':digest(archive),'archive_bytes':archive.stat().st_size,'load_output':loaded,'verified_at':now(),'passed':True}
 (work/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
 emit('runtime_verified',repository=repo,image_id=inspect['Id'],version=version)
 return record

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('repository',nargs='?',choices=['node','postgres','all'],default='all');args=parser.parse_args()
 CACHE.mkdir(parents=True,exist_ok=True);REPORT.parent.mkdir(parents=True,exist_ok=True)
 report={'schema_version':1,'started_at':now(),'actor_type':'automated','method':'anonymous-official-registry-v2-verified-docker-archive-local-load','sources':['https://github.com/docker-library/official-images','https://nodejs.org/en/download/archive/v22.23.4','https://www.postgresql.org/support/security/17/'],'images':[],'passed':False,'remote_deployment':False,'tokens_logged_or_persisted':False}
 try:
  for repo in SPECS if args.repository=='all' else [args.repository]:
   report['images'].append(acquire(repo));REPORT.write_text(json.dumps(report,indent=2)+'\n')
  report['passed']=True
 except Exception as error:
  report['error']=safe_failure(error);emit('runtime_acquisition_failed',error=report['error']);raise SystemExit(1)
 finally:
  report['completed_at']=now();REPORT.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
