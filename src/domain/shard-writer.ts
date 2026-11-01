import { createReadStream, createWriteStream } from 'node:fs';
import { createHash } from 'node:crypto';
import { link, lstat, mkdir, mkdtemp, realpath, rename, rm, writeFile, readFile } from 'node:fs/promises';
import { basename, dirname, relative, resolve, sep } from 'node:path';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createGzip } from 'node:zlib';
import type { Learning, Relation } from '../shared/contracts';
import { validateShardedManifest, type ShardPart, type ShardedManifest } from './shards';

type Kind = ShardPart['kind'];
export type ShardedArtifactHeader = Omit<ShardedManifest, 'format'|'item_count'|'relation_count'|'parts'|'content_identity'> & Record<string, unknown>;
export interface ShardedArtifactOptions { directory:string; root?:string; }
export interface ShardedArtifactResult { manifest:ShardedManifest; filename:string; sha256:string; bytes:number; root:string; }
const MAX_RECORD = 8*1024*1024, MAX_PART = 20*1024*1024, MAX_RECORDS = 5000, MAX_METADATA = 64*1024*1024;
const digest = (value:Buffer|string) => createHash('sha256').update(value).digest('hex');
const inside = (path:string, root:string) => path.startsWith(root+sep);

async function mkdirUnder(base:string,path:string){
 let current=base;
 for(const component of relative(base,path).split(sep).filter(Boolean)){
  if(component==='..')throw Error('Diretório fora da raiz permitida.');
  current=resolve(current,component);
  try{await mkdir(current);}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;}
  const info=await lstat(current);if(!info.isDirectory()||info.isSymbolicLink())throw Error('Destino de artefato deve ser diretório real.');
 }
}

/** Count before encoding; reject non-JSON values rather than silently losing them. */
function canonical(value:unknown, limit:number):Buffer {
 const seen = new Set<object>();let budget=1; // Final LF belongs to the byte limit.
 const charge=(bytes:number)=>{budget+=bytes;if(budget>limit)throw Error('JSON excede limite de tamanho documentado.');};
 const stringBytes=(text:string)=>{
  charge(2);
  for(let i=0;i<text.length;i++){
   const c=text.charCodeAt(i);
   if(c===34||c===92||[8,9,10,12,13].includes(c))charge(2);
   else if(c<32)charge(6);
   else if(c<128)charge(1);
   else if(c<2048)charge(2);
   else if(c>=0xd800&&c<=0xdbff){const next=text.charCodeAt(i+1);if(next>=0xdc00&&next<=0xdfff){charge(4);i++;}else charge(6);}
   else if(c>=0xdc00&&c<=0xdfff)charge(6);
   else charge(3);
  }
 };
 const walk=(input:unknown,depth:number):unknown=>{
  if(depth>100)throw Error('JSON excede profundidade permitida.');
  if(input===null){charge(4);return null;}
  if(typeof input==='string'){stringBytes(input);return input;}
  if(typeof input==='boolean'){charge(input?4:5);return input;}
  if(typeof input==='number'){if(!Number.isFinite(input))throw Error('JSON contém número não finito.');charge(JSON.stringify(input).length);return input;}
  if(typeof input!=='object')throw Error('Valor não representável em JSON.');
  if(seen.has(input))throw Error('JSON contém referência cíclica.');
  if(!Array.isArray(input)&&Object.getPrototypeOf(input)!==Object.prototype&&Object.getPrototypeOf(input)!==null)throw Error('JSON exige objetos simples.');
  seen.add(input);charge(2);
  let output:unknown;
  if(Array.isArray(input))output=input.map((v,index)=>{if(index)charge(1);return walk(v,depth+1);});
  else {const object:Record<string,unknown>=Object.create(null);let index=0;for(const key of Object.keys(input).sort()){if(index++)charge(1);stringBytes(key);charge(1);object[key]=walk((input as Record<string,unknown>)[key],depth+1);}output=object;}
  seen.delete(input);return output;
 };
 const result=Buffer.from(JSON.stringify(walk(value,0))+'\n');
 if(result.length>limit)throw Error('JSON excede limite de tamanho documentado.');
 return result;
}

/** Compute the exact JSONL collection identities without writing duplicate shards. */
export async function hashShardedRecords(records:{items:AsyncIterable<Learning>;relations:AsyncIterable<Relation>}){
 const identities={items:createHash('sha256'),relations:createHash('sha256')};
 for(const kind of ['items','relations'] as const)for await(const record of records[kind])identities[kind].update(canonical(record,MAX_RECORD));
 return{items_jsonl_sha256:identities.items.digest('hex'),relations_jsonl_sha256:identities.relations.digest('hex')};
}

async function sameFile(filename:string, bytes:number, sha256:string):Promise<boolean> {
 let info;try{info=await lstat(filename);}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return false;throw error;}
 if(!info.isFile()||info.isSymbolicLink()||info.size!==bytes)throw Error('Artefato imutável já existe com tamanho ou tipo divergente.');
 const hash=createHash('sha256');for await(const chunk of createReadStream(filename))hash.update(chunk);
 if(hash.digest('hex')!==sha256)throw Error('Artefato imutável já existe com conteúdo divergente.');
 return true;
}

class PartWriter {
 readonly gzip=createGzip({level:9});
 readonly compressedHash=createHash('sha256');
 readonly decodedHash=createHash('sha256');
 records=0;decodedBytes=0;compressedBytes=0;
 private failure:unknown;
 private readonly completion:Promise<void>;
 constructor(readonly kind:Kind,readonly name:string,readonly stage:string,readonly directory:string){
  const meter=new Transform({transform:(chunk:Buffer,_encoding,callback)=>{this.compressedBytes+=chunk.length;this.compressedHash.update(chunk);callback(null,chunk);}});
  // Attach rejection handling immediately, including errors before finish().
  this.completion=pipeline(this.gzip,meter,createWriteStream(resolve(stage,name),{flags:'wx',mode:0o600})).catch(error=>{this.failure=error;});
 }
 async add(line:Buffer){
  if(this.failure)throw this.failure;
  await new Promise<void>((resolve,reject)=>this.gzip.write(line,error=>error?reject(error):resolve()));
  this.records++;this.decodedBytes+=line.length;this.decodedHash.update(line);
 }
 async finish():Promise<ShardPart>{
  this.gzip.end();await this.completion;if(this.failure)throw this.failure;
  return{kind:this.kind,path:relative(process.cwd(),resolve(this.directory,this.name)).split(sep).join('/'),sha256:this.compressedHash.digest('hex'),bytes:this.compressedBytes,decoded_sha256:this.decodedHash.digest('hex'),decoded_bytes:this.decodedBytes,records:this.records};
 }
 async abort(){this.gzip.destroy();await this.completion;}
}

/** Stream a public snapshot to bounded immutable JSONL/gzip parts. No database access. */
export async function writeShardedArtifact(
 header:ShardedArtifactHeader,
 records:{items:AsyncIterable<Learning>;relations:AsyncIterable<Relation>},
 options:ShardedArtifactOptions,
):Promise<ShardedArtifactResult>{
 for(const key of ['items','relations','users','contributions','admin','sessions','passwords'])if(Object.hasOwn(header,key))throw Error('Coleções embutidas ou dados administrativos não pertencem ao manifesto público.');
 const workspace=await realpath(process.cwd());const requestedRoot=resolve(options.root??'data/bundles');
 if(!inside(requestedRoot,workspace))throw Error('Raiz do artefato deve estar no workspace.');
 await mkdirUnder(workspace,requestedRoot);const root=await realpath(requestedRoot);
 if(!inside(root,workspace))throw Error('Raiz física do artefato fora do workspace.');
 const requestedDirectory=resolve(options.directory);
 if(!inside(requestedDirectory,root))throw Error('Diretório de artefato fora da raiz permitida.');
 await mkdirUnder(root,dirname(requestedDirectory));const parent=await realpath(dirname(requestedDirectory));
 if(parent!==root&&!inside(parent,root))throw Error('Diretório físico de artefato fora da raiz permitida.');
 const directory=resolve(parent,basename(requestedDirectory));
 try{const info=await lstat(directory);if(!info.isDirectory()||info.isSymbolicLink())throw Error('Destino de artefato deve ser diretório real.');}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}
 const stage=await mkdtemp(resolve(root,'.sharded-writer-'));let active:PartWriter|undefined;
 try{
  // Bound and validate header before consuming a potentially expensive generator.
  canonical(header,MAX_METADATA);
  validateShardedManifest({...header,format:'curriculos-abertos/sharded-v1',source_count:Array.isArray(header.sources)?header.sources.length:0,item_count:0,relation_count:0,parts:[]});
  const parts:ShardPart[]=[],counts={items:0,relations:0};
  const identities={items:createHash('sha256'),relations:createHash('sha256')};
  for(const kind of ['items','relations'] as const){
   let sequence=0;
   for await(const record of records[kind]){
    const line=canonical(record,MAX_RECORD);
    if(active&&(active.records>=MAX_RECORDS||active.decodedBytes+line.length>MAX_PART)){parts.push(await active.finish());active=undefined;if(parts.length>=10000)throw Error('Manifesto excede limite documentado de partes.');}
    if(!active)active=new PartWriter(kind,`${kind}-${String(++sequence).padStart(5,'0')}.jsonl.gz`,stage,directory);
    await active.add(line);identities[kind].update(line);counts[kind]++;
    if(counts[kind]>(kind==='items'?1_000_000:5_000_000))throw Error('Coleção excede limite de registros documentado.');
   }
   if(active){parts.push(await active.finish());active=undefined;}
  }
  const manifest={...header,format:'curriculos-abertos/sharded-v1',source_count:(header.sources as unknown[]).length,item_count:counts.items,relation_count:counts.relations,parts,content_identity:{items_jsonl_sha256:identities.items.digest('hex'),relations_jsonl_sha256:identities.relations.digest('hex')}};
  validateShardedManifest(manifest);
  const manifestBytes=canonical(manifest,MAX_METADATA),sha256=digest(manifestBytes),name='snapshot.manifest.json';
  const files=parts.map(part=>({name:basename(part.path),bytes:part.bytes,sha256:part.sha256}));
  // Every part and the manifest carry independently verifiable sidecars.
  for(const file of files){const bytes=Buffer.from(file.sha256+'  '+file.name+'\n');await writeFile(resolve(stage,file.name+'.sha256'),bytes,{flag:'wx',mode:0o600});}
  await writeFile(resolve(stage,name),manifestBytes,{flag:'wx',mode:0o600});
  const sidecar=Buffer.from(sha256+'  '+name+'\n');await writeFile(resolve(stage,name+'.sha256'),sidecar,{flag:'wx',mode:0o600});
  const artifacts=[...files,...files.map(file=>{const bytes=Buffer.from(file.sha256+'  '+file.name+'\n');return{name:file.name+'.sha256',bytes:bytes.length,sha256:digest(bytes)};}),{name:name+'.sha256',bytes:sidecar.length,sha256:digest(sidecar)},{name,bytes:manifestBytes.length,sha256}];
  await mkdirUnder(root,directory);
  // Preflight every collision before publishing anything; manifest is linked last.
  for(const artifact of [...artifacts].reverse())await sameFile(resolve(directory,artifact.name),artifact.bytes,artifact.sha256);
  for(const artifact of artifacts){
   const destination=resolve(directory,artifact.name);
   try{await link(resolve(stage,artifact.name),destination);}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;await sameFile(destination,artifact.bytes,artifact.sha256);}
  }
  return{manifest:manifest as ShardedManifest,filename:resolve(directory,name),sha256,bytes:manifestBytes.length,root};
 }finally{if(active)await active.abort();await rm(stage,{recursive:true,force:true});}
}

/** Rewrite metadata on a private, freshly written candidate without touching its immutable data shards. */
export async function rewritePrivateShardedManifest(result:ShardedArtifactResult,manifest:ShardedManifest):Promise<ShardedArtifactResult>{
 validateShardedManifest(manifest);
 const current=await readFile(result.filename);
 if(digest(current)!==result.sha256)throw Error('Manifesto privado mudou antes da revalidação.');
 const oldSidecar=await readFile(result.filename+'.sha256','utf8');
 if(oldSidecar.split(/\s+/)[0]!==result.sha256)throw Error('Checksum do manifesto privado diverge antes da revalidação.');
 const bytes=canonical(manifest,MAX_METADATA),sha256=digest(bytes),name=basename(result.filename),sidecar=Buffer.from(sha256+'  '+name+'\n');
 const stage=await mkdtemp(resolve(dirname(result.filename),'.manifest-rewrite-'));
 try{
  const stagedManifest=resolve(stage,name),stagedSidecar=resolve(stage,name+'.sha256');
  await writeFile(stagedManifest,bytes,{flag:'wx',mode:0o600});await writeFile(stagedSidecar,sidecar,{flag:'wx',mode:0o600});
  await rename(stagedSidecar,result.filename+'.sha256');await rename(stagedManifest,result.filename);
 }finally{await rm(stage,{recursive:true,force:true});}
 return{...result,manifest,sha256,bytes:bytes.length};
}
