import test from 'node:test';
import assert from 'node:assert/strict';
import {pauseOwnedQaIngestion,type QaGuardQueryResult} from '../scripts/qa-executor-job-guard';

const job='11111111-1111-4111-8111-111111111111',account='own-automated-actor';
function fixture(status='running',owner=account,options:{quiesceAfter?:number;loseOwnershipOnUpdate?:boolean;eventRows?:number}={}){
 let time=0,reads=0,updates=0,events=0;
 const row:Record<string,unknown>={id:job,type:'ingest',status,pause_requested:false,requested_by:owner,actor_type:'automated'};
 const query=async(sql:string,params:unknown[]):Promise<QaGuardQueryResult>=>{
  assert.equal(params[0],job,'Every query stays pinned to the single known job');
  if(sql.startsWith('SELECT')){reads++;if(options.quiesceAfter&&reads>=options.quiesceAfter)row.status='paused';return{rows:[{...row}],rowCount:1};}
  if(sql.startsWith('UPDATE')){
   updates++;assert.equal(params[1],account);assert.match(sql,/type='ingest'/);assert.match(sql,/requested_by/);assert.match(sql,/actor_type/);
   if(options.loseOwnershipOnUpdate){row.requested_by='foreign-actor';return{rows:[],rowCount:0};}
   assert.equal(row.requested_by,account);row.pause_requested=true;if(row.status==='queued')row.status='paused';return{rows:[{...row}],rowCount:1};
  }
  if(sql.startsWith('INSERT')){events++;assert.equal(params[1],account);const event=JSON.parse(String(params[2]));assert.equal(event.scope,'single_job');assert.equal(event.action,'pause_owned_ingestion');return{rows:[{id:9}],rowCount:options.eventRows??1};}
  throw new Error('Unexpected statement');
 };
 return{input:{jobId:job,accountId:account,runId:'qa-guard-test',query,now:()=>time,sleep:async(ms:number)=>{time+=ms;}},stats:()=>({time,reads,updates,events})};
}
test('guard pauses only the identity-proven queued ingestion and persists its technical event',async()=>{
 const f=fixture('queued'),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,true);assert.equal(proof.pause_requested,true);assert.equal(proof.retention_blocked,false);
 assert.equal(f.stats().updates,1);assert.equal(f.stats().events,1);
});
test('guard awaits a running owned job becoming paused without resuming or controlling a container',async()=>{
 const f=fixture('running',account,{quiesceAfter:4}),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,true);assert.equal(proof.final_status,'paused');assert.ok(f.stats().time>0);
});
test('foreign ownership prevents every write',async()=>{
 const f=fixture('running','another-actor'),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,false);assert.equal(proof.ownership_verified,false);assert.equal(f.stats().updates,0);assert.equal(f.stats().events,0);
});
test('ownership drift during conditional UPDATE is retained rather than claimed as contained',async()=>{
 const f=fixture('running',account,{loseOwnershipOnUpdate:true}),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,false);assert.equal(proof.retention_blocked,true);assert.equal(f.stats().events,0);
});
test('a job that ignores the cooperative pause leaves a blocked retention receipt at the bounded deadline',async()=>{
 const f=fixture(),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,false);assert.equal(proof.retention_blocked,true);assert.equal(f.stats().time,15_000);assert.equal(proof.final_status,'running');
});
test('already terminal owned work is observed without changing its state',async()=>{
 const f=fixture('succeeded'),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,true);assert.equal(proof.pause_requested,false);assert.equal(f.stats().updates,0);assert.equal(f.stats().events,0);
});
test('a missing event write cannot be reported as successful containment',async()=>{
 const f=fixture('running',account,{eventRows:0}),proof=await pauseOwnedQaIngestion(f.input);
 assert.equal(proof.quiesced,false);assert.equal(proof.retention_blocked,true);
});
