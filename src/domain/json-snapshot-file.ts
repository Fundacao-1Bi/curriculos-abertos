import { createReadStream } from 'node:fs';
import { mkdir, mkdtemp, readFile, realpath, rename, rm, stat, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { relative, resolve, sep } from 'node:path';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { createGunzip, gzipSync } from 'node:zlib';
import parserStream from 'stream-json';
import FlexAssembler, { arrayRule } from 'stream-json/utils/flex-assembler.js';
import type { Token } from 'stream-json/parser.js';
import type { BundleFileExpected } from './bundle-file';
import { shardRecords, validateShardedManifest, type ShardPart, type ShardedManifest } from './shards';

export interface SnapshotConversionOptions { root?:string; expected?:BundleFileExpected; cacheRoot?:string; }
const MAX_RECORD_BYTES=8*1024*1024;
const MAX_PART_BYTES=20*1024*1024;
const MAX_METADATA_BYTES=64*1024*1024;
const MAX_PART_RECORDS=5000;
const KINDS=['items','relations'] as const;
type Kind=typeof KINDS[number];
type Counter={kind:Kind;count:number};
type SourceMarker={file_sha256:string;bytes:number;decoded_sha256:string;decoded_bytes:number};
const digest=(value:Buffer|string)=>createHash('sha256').update(value).digest('hex');
const isHash=(value:unknown):value is string=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
function streamLimit(){const n=Number(process.env.DATA_MAX_STREAM_BYTES??10*1024*1024*1024);if(!Number.isSafeInteger(n)||n<1||n>64*1024*1024*1024)throw Error('DATA_MAX_STREAM_BYTES deve estar entre 1 byte e 64 GiB.');return n;}
async function sidecar(path:string){const value=(await readFile(path+'.sha256','utf8')).trim().split(/\s/)[0];if(!isHash(value))throw Error('Sidecar SHA-256 inválido.');return value;}
function workspaceRelative(path:string){const value=relative(process.cwd(),path).split(sep).join('/');if(!value||value==='..'||value.startsWith('../')||value.startsWith('/'))throw Error('Cache de importação precisa estar dentro do workspace para caminhos portáveis.');return value;}
function ordered(value:unknown):unknown {if(Array.isArray(value))return value.map(ordered);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered((value as Record<string,unknown>)[key])]));return value;}

class PartsWriter {
 readonly parts:ShardPart[]=[];
 readonly counts={items:0,relations:0};
 readonly hashes={items:createHash('sha256'),relations:createHash('sha256')};
 private readonly state:Record<Kind,{lines:string[];bytes:number;records:number;part:number}>={items:{lines:[],bytes:0,records:0,part:0},relations:{lines:[],bytes:0,records:0,part:0}};
 constructor(readonly temporary:string,readonly destination:string){}
 async add(kind:Kind,value:unknown){
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Cada registro de item/relação precisa ser um objeto JSON.');
  const line=JSON.stringify(ordered(value))+'\n';const bytes=Buffer.byteLength(line);
  if(bytes>MAX_RECORD_BYTES)throw Error('Registro JSON excede o limite de 8 MiB.');
  const state=this.state[kind];if(state.records&&(state.records>=MAX_PART_RECORDS||state.bytes+bytes>MAX_PART_BYTES))await this.flush(kind);
  state.lines.push(line);state.bytes+=bytes;state.records++;this.counts[kind]++;this.hashes[kind].update(line);
  if(this.counts[kind]>(kind==='items'?1_000_000:5_000_000))throw Error('Contagem de registros excede o limite de publicação.');
  if(state.records===MAX_PART_RECORDS||state.bytes===MAX_PART_BYTES)await this.flush(kind);
 }
 async flush(kind:Kind){
  const state=this.state[kind];if(!state.records)return;
  const decoded=Buffer.from(state.lines.join(''));const compressed=gzipSync(decoded,{level:9});
  const name=`${kind}-${String(++state.part).padStart(5,'0')}.jsonl.gz`;
  await writeFile(resolve(this.temporary,name),compressed,{mode:0o600,flag:'wx'});
  this.parts.push({kind,path:workspaceRelative(resolve(this.destination,name)),sha256:digest(compressed),bytes:compressed.length,decoded_sha256:digest(decoded),decoded_bytes:decoded.length,records:state.records});
  state.lines=[];state.bytes=0;state.records=0;
 }
 async finish(){await this.flush('items');await this.flush('relations');return{parts:this.parts.sort((a,b)=>a.kind===b.kind?a.path.localeCompare(b.path):a.kind==='items'?-1:1),item_count:this.counts.items,relation_count:this.counts.relations,items_jsonl_sha256:this.hashes.items.digest('hex'),relations_jsonl_sha256:this.hashes.relations.digest('hex')};}
}

async function cachedResult(directory:string,rawHash:string,bytes:number,expected:BundleFileExpected|undefined,maxDecoded:number){
 const path=resolve(directory,'snapshot.manifest.json');let marker:SourceMarker;
 try{marker=JSON.parse(await readFile(resolve(directory,'source.json'),'utf8'));}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return undefined;throw Error('Cache de conversão inválido; preserve-o para inspeção e reconstrua em outro cache.');}
 if(marker.file_sha256!==rawHash||marker.bytes!==bytes||!isHash(marker.decoded_sha256)||!Number.isSafeInteger(marker.decoded_bytes)||marker.decoded_bytes<1||marker.decoded_bytes>maxDecoded)throw Error('Identidade do cache de conversão não confere.');
 if(expected?.decoded_sha256!==undefined&&expected.decoded_sha256!==marker.decoded_sha256)throw Error('Checksum decodificado diverge do manifesto.');
 if(expected?.decoded_bytes!==undefined&&expected.decoded_bytes!==marker.decoded_bytes)throw Error('Tamanho decodificado diverge do manifesto.');
 const info=await stat(path);if(info.size>MAX_METADATA_BYTES)throw Error('Manifesto do cache excede limite de metadados.');
 const raw=await readFile(path);const hash=digest(raw);if(hash!==await sidecar(path))throw Error('Checksum do manifesto de conversão divergente.');
 const manifest=JSON.parse(raw.toString('utf8'));validateShardedManifest(manifest);
 if(manifest.transcode_provenance&&((manifest.transcode_provenance as Record<string,unknown>).input_file_sha256!==rawHash))throw Error('Proveniência do cache diverge do arquivo de entrada.');
 for(const part of manifest.parts)for await(const _record of shardRecords(part,directory)){void _record;}
 return{manifest,manifest_sha256:hash,root:directory,path};
}

/** Converts complete JSON snapshots without retaining their national item/relation arrays. */
export async function convertSnapshotFileToShards(filename:string,options:SnapshotConversionOptions={}) {
 const sourceRoot=await realpath(resolve(options.root??'data/bundles'));
 const path=await realpath(resolve(filename));
 if(!path.startsWith(sourceRoot+sep)||!/\.json(?:\.gz)?$/.test(path))throw Error('Snapshot precisa ser .json/.json.gz sob a raiz permitida.');
 const maxDecoded=streamLimit();const info=await stat(path);if(!info.isFile()||info.size<1||info.size>maxDecoded)throw Error('Arquivo de snapshot excede o limite de fluxo.');
 if(options.expected?.bytes!==undefined&&options.expected.bytes!==info.size)throw Error('Tamanho do snapshot diverge do manifesto.');
 const expectedRaw=await sidecar(path);if(options.expected?.sha256!==undefined&&options.expected.sha256!==expectedRaw)throw Error('Checksum do manifesto diverge do sidecar.');
 const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);const rawHash=hash.digest('hex');
 if(rawHash!==expectedRaw)throw Error('Checksum do arquivo de snapshot divergente.');
 const compressed=path.endsWith('.gz');const expectedDecoded=compressed?options.expected?.decoded_sha256??await sidecar(path.slice(0,-3)):rawHash;
 if(!isHash(expectedDecoded))throw Error('Checksum decodificado obrigatório para snapshot gzip.');
 if(options.expected?.decoded_sha256!==undefined&&options.expected.decoded_sha256!==expectedDecoded)throw Error('Checksum decodificado diverge do manifesto.');
 if(options.expected?.decoded_bytes!==undefined&&(!Number.isSafeInteger(options.expected.decoded_bytes)||options.expected.decoded_bytes<1||options.expected.decoded_bytes>maxDecoded))throw Error('Tamanho decodificado excede limite de fluxo.');
 const cacheRoot=resolve(options.cacheRoot??'data/extracted');workspaceRelative(cacheRoot);await mkdir(cacheRoot,{recursive:true});
 const cacheBase=await realpath(cacheRoot);workspaceRelative(cacheBase);
 const directory=resolve(cacheBase,`import-${rawHash}`);
 const previous=await cachedResult(directory,rawHash,info.size,options.expected,maxDecoded);if(previous)return previous;
 const temporary=await mkdtemp(resolve(cacheBase,`.import-${rawHash}-tmp-`));
 try{
  const writer=new PartsWriter(temporary,directory);const pending:{kind:Kind;value:unknown}[]=[];const seenArrays=new Set<Kind>();
  const assembler=new FlexAssembler<Record<string,unknown>>({maxDepth:100,arrayRules:[arrayRule<Counter>({filter:p=>p.length===1&&KINDS.includes(p[0] as Kind),create:p=>{const kind=p[0] as Kind;if(seenArrays.has(kind))throw Error('Coleção JSON duplicada.');seenArrays.add(kind);return{kind,count:0};},add:(counter,value)=>{counter.count++;pending.push({kind:counter.kind,value});},finalize:counter=>({transcoded_records:counter.count})})]});
  const rawMeterHash=createHash('sha256'),decodedHash=createHash('sha256');let rawBytes=0,decodedBytes=0;
  const rawMeter=new Transform({transform(chunk:Buffer,_encoding,callback){rawBytes+=chunk.length;rawMeterHash.update(chunk);if(rawBytes>info.size)callback(new Error('Arquivo mudou durante a conversão.'));else callback(null,chunk);}});
  const decodedMeter=new Transform({transform(chunk:Buffer,_encoding,callback){decodedBytes+=chunk.length;if(decodedBytes>maxDecoded||(options.expected?.decoded_bytes!==undefined&&decodedBytes>options.expected.decoded_bytes)){callback(new Error('Snapshot decodificado excede limite de fluxo.'));return;}decodedHash.update(chunk);callback(null,chunk);}});
  const parser=parserStream({packValues:true,streamValues:true});let started=false,completed=false,stringBytes=0,numberBytes=0,metadataBudget=0,recordBudget=0;const topKeys=new Set<string>();
  const consume=new Transform({objectMode:true,transform(token:Token,_encoding,callback){
   const run=async()=>{
    if(!started){if(token.name!=='startObject')throw Error('Snapshot JSON precisa ser um único objeto.');started=true;}
    if(completed)throw Error('Mais de um valor JSON no snapshot.');
    const first=assembler.keyStack[0]??(assembler.depth===1?assembler.key:null);const inRecords=KINDS.includes(first as Kind);
    if(token.name==='startString'||token.name==='startKey')stringBytes=0;
    if(token.name==='stringChunk'){stringBytes+=Buffer.byteLength(token.value);if(stringBytes>MAX_RECORD_BYTES)throw Error('String JSON excede limite de 8 MiB.');}
    if(token.name==='startNumber')numberBytes=0;if(token.name==='numberChunk'){numberBytes+=token.value.length;if(numberBytes>1024)throw Error('Número JSON excede limite de tamanho.');}
    if(token.name==='numberValue'&&!Number.isFinite(Number(token.value)))throw Error('Número JSON não finito não pode ser preservado.');
    const cost=token.name==='stringChunk'?Buffer.byteLength(token.value):token.name==='numberChunk'?token.value.length:16;
    // Packed values repeat streamed bytes; do not double-count them in budgets.
    if(!['keyValue','stringValue','numberValue'].includes(token.name)){if(inRecords){recordBudget+=cost;if(recordBudget>MAX_RECORD_BYTES)throw Error('Registro JSON excede orçamento de 8 MiB.');}else{metadataBudget+=cost;if(metadataBudget>MAX_METADATA_BYTES)throw Error('Metadados do snapshot excedem limite de 64 MiB.');}}
    if(token.name==='keyValue'&&assembler.depth===1){if(topKeys.has(token.value))throw Error('Chave de topo duplicada no snapshot.');topKeys.add(token.value);if(['users','contributions','admin','sessions','passwords'].includes(token.value))throw Error('Dados administrativos não pertencem a um snapshot público.');}
    assembler.consume(token);while(pending.length){const record=pending.shift()!;await writer.add(record.kind,record.value);recordBudget=0;}
    if(assembler.done)completed=true;
   };run().then(()=>callback(),error=>callback(error));
  }});
  if(compressed)await pipeline(createReadStream(path),rawMeter,createGunzip(),decodedMeter,parser,consume);else await pipeline(createReadStream(path),rawMeter,decodedMeter,parser,consume);
  const actualRaw=rawMeterHash.digest('hex'),actualDecoded=decodedHash.digest('hex');
  if(rawBytes!==info.size||actualRaw!==rawHash)throw Error('Arquivo mudou durante a conversão; resultado descartado.');
  if(actualDecoded!==expectedDecoded)throw Error('Checksum do JSON decodificado divergente.');
  if(options.expected?.decoded_bytes!==undefined&&decodedBytes!==options.expected.decoded_bytes)throw Error('Tamanho do JSON decodificado divergente.');
  if(!completed||!assembler.done||!seenArrays.has('items')||!seenArrays.has('relations'))throw Error('Snapshot incompleto ou sem coleções obrigatórias.');
  const metadata=assembler.current;if(!metadata||typeof metadata!=='object'||Array.isArray(metadata))throw Error('Metadados do snapshot inválidos.');
  if(metadata.format==='curriculos-abertos/sharded-v1'||Object.hasOwn(metadata,'parts'))throw Error('Este conversor recebe snapshots completos, não manifestos de partes.');
  const finished=await writer.finish();
  if(Object.hasOwn(metadata,'item_count')&&metadata.item_count!==finished.item_count)throw Error('Contagem de itens difere do snapshot.');
  if(Object.hasOwn(metadata,'relation_count')&&metadata.relation_count!==finished.relation_count)throw Error('Contagem de relações difere do snapshot.');
  delete metadata.items;delete metadata.relations;
  const manifest={...metadata,format:'curriculos-abertos/sharded-v1',item_count:finished.item_count,relation_count:finished.relation_count,parts:finished.parts,...(metadata.content_identity?{source_content_identity:metadata.content_identity}:{}),content_identity:{items_jsonl_sha256:finished.items_jsonl_sha256,relations_jsonl_sha256:finished.relations_jsonl_sha256},transcode_provenance:{input_file_sha256:rawHash,input_decoded_sha256:actualDecoded,format:'snapshot-json-stream'}};
  validateShardedManifest(manifest);
  const manifestBytes=Buffer.from(JSON.stringify(ordered(manifest))+'\n');if(manifestBytes.length>MAX_METADATA_BYTES)throw Error('Manifesto convertido excede limite de metadados.');
  const manifestHash=digest(manifestBytes);await writeFile(resolve(temporary,'snapshot.manifest.json'),manifestBytes,{flag:'wx',mode:0o600});await writeFile(resolve(temporary,'snapshot.manifest.json.sha256'),manifestHash+'  snapshot.manifest.json\n',{flag:'wx',mode:0o600});
  await writeFile(resolve(temporary,'source.json'),JSON.stringify({file_sha256:rawHash,bytes:info.size,decoded_sha256:actualDecoded,decoded_bytes:decodedBytes} satisfies SourceMarker)+'\n',{flag:'wx',mode:0o600});
  try{await rename(temporary,directory);}catch(error){if(!['EEXIST','ENOTEMPTY'].includes((error as NodeJS.ErrnoException).code??''))throw error;const winner=await cachedResult(directory,rawHash,info.size,options.expected,maxDecoded);if(!winner||winner.manifest_sha256!==manifestHash)throw Error('Conversões concorrentes produziram cache divergente.');await rm(temporary,{recursive:true,force:true});return winner;}
  return{manifest:manifest as ShardedManifest,manifest_sha256:manifestHash,root:directory,path:resolve(directory,'snapshot.manifest.json')};
 }catch(error){await rm(temporary,{recursive:true,force:true});throw error;}
}
