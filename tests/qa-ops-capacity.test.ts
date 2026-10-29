import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,access,rm,symlink} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {GiB,productionBudget,reimportBudget,recoveryBudget,assertCapacityAvailable,type ArtifactFootprint,type DatabaseFootprint} from '../scripts/qa-capacity';
import {cleanupVerifiedReimport} from '../scripts/qa-own-cleanup';
import type {CleanState} from '../scripts/qa-production';
const artifact:ArtifactFootprint={publication:'test-capacity',compressed_bytes:GiB/16,decoded_bytes:GiB,metadata_bytes:1024**2,items:200000,largest_uf:'SP',largest_uf_primary_bytes:GiB/10,largest_uf_items:20000,national_json_upper_bytes:2*GiB};
const database:DatabaseFootprint={database_bytes:2*GiB,item_payload_bytes:GiB,relation_payload_bytes:GiB/8,source_payload_bytes:GiB/256,metadata_bytes:1024**2,coverage_bytes:1024**2,id_bytes:4*1024**2,items:200000,largest_uf:'SP',largest_uf_primary_bytes:GiB/10,largest_uf_items:20000,national_json_upper_bytes:1.5*GiB};
test('FULL reimport cannot inherit the old 3GiB allowance or count only compressed bytes',()=>{
 const plan=reimportBudget(database,artifact);
 assert.throws(()=>assertCapacityAvailable(plan,{host:3*GiB,docker:100*GiB}),/reimport: requer/);
 assert.throws(()=>assertCapacityAvailable(plan,{host:100*GiB,docker:3*GiB}),/reimport: requer/);
 const compressedTenfold=reimportBudget(database,{...artifact,compressed_bytes:Math.floor(artifact.compressed_bytes/10)});
 assert.equal(compressedTenfold.required_free_bytes,plan.required_free_bytes,'Gzip ratio must not reduce the space for HTTP JSON copies or SQL');
 assert.ok(plan.required_free_bytes>15*GiB,'Large national/UF copies, conversion and measured PG coexist');
});
test('larger measured PG/export sizes and restore files increase the provisioned peak',()=>{
 assert.ok(reimportBudget({...database,database_bytes:4*GiB,national_json_upper_bytes:3*GiB},artifact).required_free_bytes>reimportBudget(database,artifact).required_free_bytes);
 assert.ok(recoveryBudget(2*GiB,GiB,GiB).required_free_bytes>recoveryBudget(GiB,GiB/2,0).required_free_bytes);
 assert.ok(productionBudget({...artifact,national_json_upper_bytes:4*GiB}).required_free_bytes>productionBudget(artifact).required_free_bytes);
 assert.throws(()=>recoveryBudget(Number.NaN,1,1));assert.throws(()=>recoveryBudget(Number.MAX_SAFE_INTEGER,1,1));
});
test('filesystem cleanup preserves foreign siblings and refuses hash drift, traversal and symlinks',async()=>{
 const old=process.cwd(),root=await mkdtemp(join(tmpdir(),'curriculos-qa-cleanup-'));
 try{
  process.chdir(root);const own='var/qa-reimport/abcdef012345',foreign='var/qa-reimport/ffffffffffff';await mkdir(own,{recursive:true});await mkdir(foreign,{recursive:true});
  const file=join(own,'national.json'),text='{"owned_test_file":true}\n';await writeFile(file,text);await writeFile(join(foreign,'keep'),'preserved');
  const state={project:'curriculos-abertos-clean-unit-123',publication:'test-capacity'} as CleanState;
  const receipt={path:file,bytes:Buffer.byteLength(text),sha256:createHash('sha256').update(text).digest('hex'),job_id:'11111111-1111-4111-8111-111111111111',created_by_this_run:false};
  await assert.rejects(()=>cleanupVerifiedReimport(state,own,[{...receipt,sha256:'0'.repeat(64)}]));assert.equal(await readFile(file,'utf8'),text);
  await assert.rejects(()=>cleanupVerifiedReimport(state,'var/qa-reimport/../outside',[]));
  await symlink('ffffffffffff','var/qa-reimport/aaaaaaaaaaaa');await assert.rejects(()=>cleanupVerifiedReimport(state,'var/qa-reimport/aaaaaaaaaaaa',[]));
  const result=await cleanupVerifiedReimport(state,own,[receipt]);assert.equal(result.cleaned.length,0,'Preexisting/foreign exports are never sent to server cleanup');
  await assert.rejects(()=>access(own));assert.equal(await readFile(join(foreign,'keep'),'utf8'),'preserved');
 }finally{process.chdir(old);await rm(root,{recursive:true,force:true});}
});
