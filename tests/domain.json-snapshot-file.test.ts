import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { gzipSync } from 'node:zlib';
import { convertSnapshotFileToShards } from '../src/domain/json-snapshot-file';
import { shardRecords, verifyShardedManifest } from '../src/domain/shards';
import type { Bundle, Learning, Source } from '../src/shared/contracts';
const digest=(value:Buffer|string)=>createHash('sha256').update(value).digest('hex');
const source:Source={id:'fixture-source',uf:'BR',title:'Synthetic isolated parser test',issuer:'Test only',official_url:'https://example.org/source',artifact_url:'https://example.org/source.pdf',stages:['EF'],components:['Matemática'],edition:'fixture',document_date:null,homologation_date:null,application_period:null,document_type:'fixture',normative_parts:['test'],redistribution:'Synthetic test only',collected_at:null,sha256:null,local_path:null,status:'fixture'};
const learning=(index:number):Learning=>({id:`fixture:${String(index).padStart(5,'0')}`,curriculum_id:'fixture-curriculum',source_id:source.id,uf:'BR',code:`TEST-${index}`,text:`Texto canônico ${index}: frações, \"aspas\", vírgulas e\nsegunda linha. 😀`,normalized_text:'test',editorial_note:null,kind:'habilidade',parent_id:null,positions:[{stage:'EF',component:'Matemática',area:null,years:[6,7],year_label:'6º e 7º',age_group:null,period:null}],evidence:[{source_id:source.id,page:1,printed_page:null,section:null,excerpt:`Texto canônico ${index}`}],extraction_revision:'fixture-v1'});
const fixture=(count=2):Bundle=>({id:'fixture-stream-import',schema_version:'1.0.0',created_at:'2026-10-28T01:00:00Z',extraction_revision:'fixture-v1',mapping_revision:'fixture-v1',sources:[source],items:Array.from({length:count},(_,i)=>learning(i)),relations:[],coverage:[{uf:'BR',stage:'EF',ready:false}],changelog:[],rights:{code:'fixture-only'},content_identity:{items_jsonl_sha256:'legacy-byte-identity'},extension:{preserve:'metadata sem alteração'}});
async function scope(action:(root:string,cache:string)=>Promise<void>){await mkdir('var',{recursive:true});const root=await mkdtemp(resolve('var','json-snapshot-file-test-'));try{const cache=resolve(root,'cache');await action(root,cache);}finally{await rm(root,{recursive:true,force:true});}}
async function artifact(root:string,name:string,raw:Buffer|string){const path=resolve(root,name);await writeFile(path,raw);await writeFile(path+'.sha256',digest(raw)+'  '+name+'\n');return path;}

test('snapshot conversion preserves canonical records and metadata while emitting bounded deterministic shards',async()=>scope(async(root,cache)=>{
 const original=fixture(5001),raw=Buffer.from(JSON.stringify(original));const path=await artifact(root,'snapshot.json',raw);
 const output=await convertSnapshotFileToShards(path,{root,cacheRoot:cache,expected:{sha256:digest(raw),bytes:raw.length}});
 assert.equal(output.manifest.id,original.id);assert.equal(output.manifest.item_count,5001);assert.equal(output.manifest.relation_count,0);assert.equal(output.manifest.parts.length,2);assert.deepEqual(output.manifest.parts.map(p=>p.records),[5000,1]);assert.ok(output.manifest.parts.every(p=>p.decoded_bytes<=20*1024*1024));
 assert.equal(Object.hasOwn(output.manifest,'items'),false);assert.equal(Object.hasOwn(output.manifest,'relations'),false);assert.deepEqual(output.manifest.extension,original.extension);assert.deepEqual(output.manifest.source_content_identity,original.content_identity);
 const hash=createHash('sha256');let count=0;for(const part of output.manifest.parts){for await(const row of shardRecords(part,output.root,chunk=>hash.update(chunk))){assert.deepEqual(row,original.items[count++]);}}
 assert.equal((output.manifest.content_identity as Record<string,unknown>).items_jsonl_sha256,hash.digest('hex'));
 assert.equal(count,5001);assert.equal((await verifyShardedManifest(output.manifest,output.root)).item_count,5001);
 const second=await convertSnapshotFileToShards(path,{root,cacheRoot:cache});assert.equal(second.path,output.path);assert.equal(second.manifest_sha256,output.manifest_sha256);assert.deepEqual(await readFile(path),raw);
 const file=await readFile(output.path);assert.equal(digest(file),output.manifest_sha256);assert.equal((await readFile(output.path+'.sha256','utf8')).split(/\s/)[0],output.manifest_sha256);
}));

test('gzip snapshots validate both byte identities and preserve the same publication and texts',async()=>scope(async(root,cache)=>{
 const original=fixture(),decoded=Buffer.from(JSON.stringify(original)),raw=gzipSync(decoded);const path=await artifact(root,'snapshot.json.gz',raw);await writeFile(resolve(root,'snapshot.json.sha256'),digest(decoded));
 const output=await convertSnapshotFileToShards(path,{root,cacheRoot:cache,expected:{sha256:digest(raw),bytes:raw.length,decoded_sha256:digest(decoded),decoded_bytes:decoded.length}});
 assert.equal(output.manifest.id,original.id);assert.equal(output.input.file_sha256,digest(raw));assert.equal(output.input.decoded_sha256,digest(decoded));assert.equal(output.input.decoded_bytes,decoded.length);assert.deepEqual(output.manifest.sources,original.sources);assert.deepEqual(output.manifest.coverage,original.coverage);assert.deepEqual(output.manifest.changelog,original.changelog);assert.equal((output.manifest.transcode_provenance as Record<string,unknown>).input_decoded_sha256,digest(decoded));
 const rows=[];for await(const row of shardRecords(output.manifest.parts[0],output.root))rows.push(row);assert.deepEqual(rows,original.items);
 await assert.rejects(()=>convertSnapshotFileToShards(path,{root,cacheRoot:cache,expected:{decoded_sha256:'0'.repeat(64)}}),/Checksum/);
 await writeFile(resolve(root,'snapshot.json.sha256'),'f'.repeat(64));await assert.rejects(()=>convertSnapshotFileToShards(path,{root,cacheRoot:cache}),/Checksum decodificado/);
}));

test('conversion rejects raw corruption, decoded corruption and a modified cached shard',async()=>scope(async(root,cache)=>{
 const raw=Buffer.from(JSON.stringify(fixture())),path=await artifact(root,'snapshot.json',raw);const output=await convertSnapshotFileToShards(path,{root,cacheRoot:cache});
 await writeFile(resolve(output.manifest.parts[0].path),'modified');await assert.rejects(()=>convertSnapshotFileToShards(path,{root,cacheRoot:cache}),/Tamanho|Checksum/);
 await writeFile(path,Buffer.from('tampered'));await assert.rejects(()=>convertSnapshotFileToShards(path,{root,cacheRoot:cache}),/Checksum/);
 const compressed=gzipSync(raw);const gzipPath=await artifact(root,'other.json.gz',compressed);await writeFile(resolve(root,'other.json.sha256'),'f'.repeat(64));await assert.rejects(()=>convertSnapshotFileToShards(gzipPath,{root,cacheRoot:cache}),/Checksum do JSON decodificado/);
}));

test('stream bounds and grammar guards fail without changing the input artifact',async()=>scope(async(root,cache)=>{
 const raw=Buffer.from(JSON.stringify(fixture())),path=await artifact(root,'snapshot.json',raw);const previous=process.env.DATA_MAX_STREAM_BYTES;
 try{process.env.DATA_MAX_STREAM_BYTES='10';await assert.rejects(()=>convertSnapshotFileToShards(path,{root,cacheRoot:cache}),/limite de fluxo/);}finally{if(previous===undefined)delete process.env.DATA_MAX_STREAM_BYTES;else process.env.DATA_MAX_STREAM_BYTES=previous;}
 const bombDecoded=Buffer.from(JSON.stringify({...fixture(1),extension:'x'.repeat(20000)})),bombRaw=gzipSync(bombDecoded);const bombPath=await artifact(root,'bomb.json.gz',bombRaw);await writeFile(resolve(root,'bomb.json.sha256'),digest(bombDecoded));
 try{process.env.DATA_MAX_STREAM_BYTES='2048';assert.ok(bombRaw.length<2048);await assert.rejects(()=>convertSnapshotFileToShards(bombPath,{root,cacheRoot:cache}),/decodificado excede/);}finally{if(previous===undefined)delete process.env.DATA_MAX_STREAM_BYTES;else process.env.DATA_MAX_STREAM_BYTES=previous;}
 const oversized={...fixture(1),extension:'x'.repeat(8*1024*1024+1)};const largePath=await artifact(root,'oversized.json',JSON.stringify(oversized));await assert.rejects(()=>convertSnapshotFileToShards(largePath,{root,cacheRoot:cache}),/String JSON excede/);
 const duplicatePath=await artifact(root,'duplicate.json','{"id":"a","id":"b","items":[],"relations":[]}');await assert.rejects(()=>convertSnapshotFileToShards(duplicatePath,{root,cacheRoot:cache}),/Chave de topo duplicada/);
 const privatePath=await artifact(root,'private.json',JSON.stringify({...fixture(),users:[]}));await assert.rejects(()=>convertSnapshotFileToShards(privatePath,{root,cacheRoot:cache}),/administrativos/);
 assert.deepEqual(await readFile(path),raw);
}));

test('JSONL preserves Unicode line and paragraph separators inside canonical strings',async()=>scope(async(root,cache)=>{
 const original=fixture(2);original.items[0].text='Texto antes\u2028separador de linha\u2029separador de parágrafo depois.';original.items[0].evidence[0].excerpt=original.items[0].text;
 const path=await artifact(root,'unicode-separators.json',JSON.stringify(original));const output=await convertSnapshotFileToShards(path,{root,cacheRoot:cache});
 const rows=[];for(const part of output.manifest.parts)for await(const row of shardRecords(part,output.root))rows.push(row);
 assert.deepEqual(rows,original.items);assert.equal((await verifyShardedManifest(output.manifest,output.root)).item_count,2);
 const cached=await convertSnapshotFileToShards(path,{root,cacheRoot:cache});assert.equal(cached.manifest_sha256,output.manifest_sha256);
}));
