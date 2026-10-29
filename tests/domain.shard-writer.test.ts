import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { lstat, mkdir, mkdtemp, readFile, readdir, rm, symlink, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { gunzipSync } from 'node:zlib';
import { writeShardedArtifact, type ShardedArtifactHeader } from '../src/domain/shard-writer';
import { shardRecords, verifyShardedManifest } from '../src/domain/shards';
import type { Learning, Relation, Source } from '../src/shared/contracts';
const digest=(value:Buffer|string)=>createHash('sha256').update(value).digest('hex');
const source:Source={id:'shard-writer-source',uf:'BR',title:'Synthetic writer fixture',issuer:'Isolated test',official_url:'https://example.org/fixture',artifact_url:'https://example.org/fixture.pdf',stages:['EF'],components:['Matemática'],edition:'test',document_date:null,homologation_date:null,application_period:null,document_type:'test_fixture',normative_parts:['test'],redistribution:'Synthetic test only',collected_at:null,sha256:null,local_path:null,status:'test'};
const header:ShardedArtifactHeader={id:'test-shard-writer',schema_version:'1.0.0',created_at:'2026-10-28T00:00:00Z',extraction_revision:'test',mapping_revision:'test',sources:[source],coverage:[],changelog:[],extension:{preserved:true}};
const item=(index:number,text=`Texto canônico ${index}: 😀, "aspas"\nlinha\u2028e\u2029parágrafo.`):Learning=>({id:'writer-'+index,curriculum_id:source.id,source_id:source.id,uf:'BR',code:'TEST-'+index,text,normalized_text:'',editorial_note:null,kind:'habilidade',parent_id:null,positions:[{stage:'EF',component:'Matemática',area:null,years:[5],year_label:'5º',age_group:null,period:null}],evidence:[{source_id:source.id,page:1,printed_page:null,section:null,excerpt:'Evidência canônica.'}],extraction_revision:'test'});
const relation:Relation={id:'writer-relation',members:[{item_id:'writer-0',role:'source',scope:'part'},{item_id:'writer-1',role:'target',scope:'reference'}],relation_type:'referencia_nacional',origin:'declaracao_fonte',technical_validation_status:'verified',pedagogical_review_status:'not_reviewed',publication_status:'published',method:'Synthetic test',evidence:[]};
async function* generate<T>(values:Iterable<T>){yield* values;}
const records=(count=2)=>({items:(async function*(){for(let i=0;i<count;i++)yield item(i);})(),relations:generate([relation])});
async function scope(action:(root:string,directory:string)=>Promise<void>){await mkdir('var',{recursive:true});const root=await mkdtemp(resolve('var','shard-writer-test-'));try{await action(root,resolve(root,'artifact'));}finally{await rm(root,{recursive:true,force:true});}}

test('stream writer roundtrips every record, exact collection hashes and deterministic immutable retries',async()=>scope(async(root,directory)=>{
 const output=await writeShardedArtifact({...header,source_count:999},records(5001),{root,directory});
 assert.equal(output.root,root);assert.equal(output.manifest.source_count,1);assert.equal(output.manifest.item_count,5001);assert.equal(output.manifest.relation_count,1);assert.deepEqual(output.manifest.parts.map(p=>p.records),[5000,1,1]);
 assert.deepEqual(output.manifest.parts.map(p=>p.kind),['items','items','relations']);assert.equal(Object.hasOwn(output.manifest,'items'),false);assert.deepEqual(output.manifest.extension,{preserved:true});
 const hashes={items:createHash('sha256'),relations:createHash('sha256')};let count=0;
 for(const part of output.manifest.parts){
  const raw=await readFile(resolve(part.path)),decoded=gunzipSync(raw);
  assert.equal(raw.length,part.bytes);assert.equal(digest(raw),part.sha256);assert.equal(decoded.length,part.decoded_bytes);assert.equal(digest(decoded),part.decoded_sha256);assert.equal(raw.readUInt32LE(4),0);
  assert.equal((await lstat(resolve(part.path))).mode&0o777,0o600);assert.equal((await readFile(resolve(part.path)+'.sha256','utf8')).split(' ')[0],part.sha256);
  for await(const row of shardRecords(part,output.root,chunk=>hashes[part.kind].update(chunk))){if(part.kind==='items')assert.deepEqual(row,item(count++));else assert.deepEqual(row,relation);}
 }
 assert.equal(count,5001);assert.deepEqual(output.manifest.content_identity,{items_jsonl_sha256:hashes.items.digest('hex'),relations_jsonl_sha256:hashes.relations.digest('hex')});
 assert.deepEqual(await verifyShardedManifest(output.manifest,root),{item_count:5001,relation_count:1,source_count:1});
 const bytes=await readFile(output.filename);assert.equal(output.bytes,bytes.length);assert.equal(output.sha256,digest(bytes));assert.equal((await lstat(output.filename)).mode&0o777,0o600);assert.equal((await readFile(output.filename+'.sha256','utf8')).split(' ')[0],output.sha256);
 const reordered=Object.fromEntries(Object.entries(header).reverse()) as ShardedArtifactHeader;
 const again=await writeShardedArtifact(reordered,{items:(async function*(){for(let i=0;i<5001;i++)yield Object.fromEntries(Object.entries(item(i)).reverse()) as Learning;})(),relations:generate([relation])},{root,directory});
 assert.equal(again.sha256,output.sha256);assert.deepEqual(await readFile(output.filename),bytes);assert.ok(!(await readdir(root)).some(name=>name.startsWith('.sharded-writer-')));
}));

test('stream writer rolls parts at the decoded byte limit and rejects oversized records',async()=>scope(async(root,directory)=>{
 const long='x'.repeat(7*1024*1024);
 const output=await writeShardedArtifact(header,{items:(async function*(){for(let i=0;i<3;i++)yield item(i,long);})(),relations:generate([])},{root,directory});
 assert.deepEqual(output.manifest.parts.map(p=>p.records),[2,1]);assert.ok(output.manifest.parts.every(p=>p.decoded_bytes<=20*1024*1024));
 let count=0;for(const part of output.manifest.parts)for await(const row of shardRecords(part,root)){assert.equal((row as Learning).text,long);count++;}assert.equal(count,3);
 await assert.rejects(()=>writeShardedArtifact(header,{items:generate([item(0,'y'.repeat(8*1024*1024))]),relations:generate([])},{root,directory:resolve(root,'too-large')}),/limite de tamanho/);
 assert.ok(!(await readdir(root)).includes('too-large'));
}));

test('stream writer refuses collisions and damaged sidecars without replacing immutable bytes',async()=>scope(async(root,directory)=>{
 await mkdir(directory);const first=await writeShardedArtifact(header,records(),{root,directory});const original=await readFile(first.filename),part=first.manifest.parts[0],originalPart=await readFile(resolve(part.path));
 await assert.rejects(()=>writeShardedArtifact(header,{items:generate([item(0,'Alterado'),item(1)]),relations:generate([relation])},{root,directory}),/imutável/);
 assert.deepEqual(await readFile(first.filename),original);assert.deepEqual(await readFile(resolve(part.path)),originalPart);
 await writeFile(first.filename+'.sha256','invalid checksum');await assert.rejects(()=>writeShardedArtifact(header,records(),{root,directory}),/imutável/);assert.deepEqual(await readFile(first.filename),original);
}));

test('stream writer rejects path escapes, non-JSON records and generator failure without publishing a manifest',async()=>scope(async(root,directory)=>{
 await assert.rejects(()=>writeShardedArtifact(header,records(),{root,directory:resolve(root,'../escape')}),/fora da raiz/);
 const outside=resolve(root,'outside');await mkdir(outside);await symlink(outside,directory);await assert.rejects(()=>writeShardedArtifact(header,records(),{root,directory}),/diretório real/);
 await assert.rejects(()=>writeShardedArtifact({...header,users:[]},records(),{root,directory:resolve(root,'private')}),/administrativos/);
 const cyclic=item(0);cyclic.loop=cyclic;await assert.rejects(()=>writeShardedArtifact(header,{items:generate([cyclic]),relations:generate([])},{root,directory:resolve(root,'cyclic')}),/cíclica/);
 await assert.rejects(()=>writeShardedArtifact(header,{items:generate([{...item(0),value:Number.POSITIVE_INFINITY}]),relations:generate([])},{root,directory:resolve(root,'non-finite')}),/não finito/);
 await assert.rejects(()=>writeShardedArtifact(header,{items:(async function*(){yield item(0);throw Error('producer failed');})(),relations:generate([])},{root,directory:resolve(root,'failed')}),/producer failed/);
 assert.ok(!(await readdir(root)).some(name=>name==='failed'||name.startsWith('.sharded-writer-')));
}));

test('empty collections retain SHA256 identities and bounded metadata without emitting empty parts',async()=>scope(async(root,directory)=>{
 const empty=await writeShardedArtifact(header,{items:generate([]),relations:generate([])},{root,directory});
 assert.deepEqual(empty.manifest.parts,[]);assert.equal(empty.manifest.item_count,0);assert.equal(empty.manifest.relation_count,0);assert.deepEqual(empty.manifest.content_identity,{items_jsonl_sha256:digest(''),relations_jsonl_sha256:digest('')});
 assert.deepEqual(await verifyShardedManifest(empty.manifest,root),{item_count:0,relation_count:0,source_count:1});
}));
