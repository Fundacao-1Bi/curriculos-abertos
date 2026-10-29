/** Pure receipt contracts and real bounded subprocesses; no DB, HTTP, main worker or corpus mutation. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {canonicalProvenance} from '../src/domain/ingestion-provenance';
import {runIngestionCommand,validateIngestionRasterTransition} from '../src/worker/ingestion';

const original={publication:'raw-original',artifact:'data/bundles/raw-original.manifest.json',artifact_sha256:'a'.repeat(64)};
const scope={base_publication:'published-base',base_publication_sha256:'b'.repeat(64),base_artifact_sha256:'c'.repeat(64),target_source_ids:['rn-referencial-em'],context_source_ids:['br-bncc']};
function stage(effective=original,jobScope=scope,bypass=true){
 const internal={format:'primary-raster-reference-augmentation-receipt-v1',original_raw_receipt:original,effective_raw_receipt:effective,...jobScope,bypass_exact:bypass,source_body_verified:false,ready_promoted:false,promotion_performed:false,added_records:bypass?0:3};
 return{original_raw_receipt:original,effective_raw_receipt:effective,augmentation_receipt:{...internal,receipt_sha256:createHash('sha256').update(canonicalProvenance(internal)).digest('hex')}};
}

test('RN bypass preserves exact original artifact path, identity and checksum',()=>{
 assert.deepEqual(validateIngestionRasterTransition(stage(),original,scope),original);
 for(const altered of [{...original,publication:'other'},{...original,artifact:'data/bundles/other.manifest.json'},{...original,artifact_sha256:'d'.repeat(64)}])assert.throws(()=>validateIngestionRasterTransition(stage(altered),original,scope),/Bypass raster/);
 assert.throws(()=>validateIngestionRasterTransition(stage(original,scope,false),original,scope),/não AM/);
});
test('AM effective RAW may differ while original and base/context pins remain independent',()=>{
 const am={...scope,target_source_ids:['am-rca-ei']},effective={publication:'raw-effective',artifact:'data/bundles/raw-effective.manifest.json',artifact_sha256:'e'.repeat(64)};
 assert.deepEqual(validateIngestionRasterTransition(stage(effective,am,false),original,am),effective);
 assert.throws(()=>validateIngestionRasterTransition(stage(effective,{...am,base_artifact_sha256:am.base_publication_sha256},false),original,am),/base_artifact_sha256/);
 assert.throws(()=>validateIngestionRasterTransition(stage(effective,am,false),{...original,publication:'forged-original'},am),/RAW original/);
});
test('stage rejects malformed digest, target/context substitution and promotion flags',()=>{
 const broken=stage();broken.augmentation_receipt.receipt_sha256='0'.repeat(64);
 assert.throws(()=>validateIngestionRasterTransition(broken,original,scope),/Digest interno/);
 for(const changed of [{target_source_ids:['other-source']},{context_source_ids:['other-br']},{base_publication:'other-base'}])assert.throws(()=>validateIngestionRasterTransition(stage(original,{...scope,...changed}),original,scope),/Escopo/);
 const promoted={...stage(),augmentation_receipt:{...stage().augmentation_receipt,promotion_performed:true}};
 assert.throws(()=>validateIngestionRasterTransition(promoted,original,scope));
});
test('subprocess argv stays literal, output is bounded and unsuccessful exit rejects',async()=>{
 const literal='$(touch should-never-exist); `echo dangerous`';
 assert.equal(await runIngestionCommand(process.execPath,['-e','process.stdout.write(process.argv[1])',literal]),literal);
 await assert.rejects(runIngestionCommand(process.execPath,['-e','process.stdout.write("x".repeat(256))'],{maxOutputBytes:64}),/excedeu o limite/);
 await assert.rejects(runIngestionCommand(process.execPath,['-e','process.exit(7)']),/código 7/);
 await assert.rejects(runIngestionCommand(process.execPath,['-e','setInterval(()=>{},1000)'],{timeoutMs:100}),/Tempo máximo/);
 const controller=new AbortController();controller.abort(new Error('already stopped'));
 await assert.rejects(runIngestionCommand(process.execPath,['-e','throw Error("must not spawn")'],{signal:controller.signal}),/already stopped/);
});
test('aborting a TERM-resistant subprocess waits for close after bounded SIGKILL escalation',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'ca-worker-cancel-')),pidFile=join(directory,'pid');
 const controller=new AbortController();
 const execution=runIngestionCommand(process.execPath,['-e','require("node:fs").writeFileSync(process.argv[1],String(process.pid));process.on("SIGTERM",()=>{});setInterval(()=>{},1000)',pidFile],{signal:controller.signal,timeoutMs:15000});
 let pid=0;
 try{
  for(let attempt=0;attempt<100&&!pid;attempt++){try{pid=Number(await readFile(pidFile,'utf8'));}catch{await new Promise(resolve=>setTimeout(resolve,20));}}
  assert.ok(pid,'child started and registered signal handler');
  // The pid write precedes registration by a few instructions; allow that handler to be installed.
  await new Promise(resolve=>setTimeout(resolve,30));
  const stoppedAt=Date.now();controller.abort(new Error('controlled pause'));
  await assert.rejects(execution,/controlled pause/);
  assert.ok(Date.now()-stoppedAt>=4500,'must await SIGKILL escalation and child close');
  assert.throws(()=>process.kill(pid,0),(error:unknown)=>(error as NodeJS.ErrnoException).code==='ESRCH');
 }finally{controller.abort();if(pid){try{process.kill(pid,'SIGKILL');}catch{}}await rm(directory,{recursive:true,force:true});}
});
