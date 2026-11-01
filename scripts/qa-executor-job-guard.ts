/** Cooperative containment of one identity-proven ingestion job. No worker/container control. */
import assert from 'node:assert/strict';

export interface QaGuardQueryResult {rows:Record<string,unknown>[];rowCount:number|null;}
export interface QaIngestionGuardProof {
 job_id:string;ownership_verified:boolean;pause_requested:boolean;quiesced:boolean;
 final_status?:string;reason:string;retention_blocked:boolean;elapsed_ms:number;
}
const jobQuery=`SELECT id,type,status,pause_requested,payload->'requested_by'->>'id' AS requested_by,
 payload->'requested_by'->>'actor_type' AS actor_type FROM jobs WHERE id=$1`;

export async function pauseOwnedQaIngestion(input:{
 jobId:string;accountId:string;runId:string;
 query:(sql:string,params:unknown[])=>Promise<QaGuardQueryResult>;
 timeoutMs?:number;now?:()=>number;sleep?:(ms:number)=>Promise<void>;
}):Promise<QaIngestionGuardProof>{
 assert.match(input.jobId,/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i);
 assert.ok(input.accountId&&input.accountId.length<=200);
 const timeout=input.timeoutMs??15_000;assert.ok(Number.isSafeInteger(timeout)&&timeout>0&&timeout<=15_000);
 const clock=input.now??Date.now,sleep=input.sleep??(ms=>new Promise(resolve=>setTimeout(resolve,ms)));
 const started=clock(),deadline=started+timeout;
 let owned=false,pauseRequested=false,finalStatus:string|undefined;
 const result=(quiesced:boolean,reason:string):QaIngestionGuardProof=>({job_id:input.jobId,
  ownership_verified:owned,pause_requested:pauseRequested,quiesced,final_status:finalStatus,
  reason,retention_blocked:!quiesced,elapsed_ms:Math.max(0,clock()-started)});
 const belongs=(row:Record<string,unknown>|undefined)=>!!row&&row.id===input.jobId&&
  row.type==='ingest'&&row.requested_by===input.accountId&&row.actor_type==='automated';
 const read=async()=>{const rows=(await input.query(jobQuery,[input.jobId])).rows;return rows.length===1?rows[0]:undefined;};
 let row=await read();
 if(!belongs(row))return result(false,'Job ownership could not be proven; no pause or event mutation executed');
 owned=true;finalStatus=String(row!.status);
 if(['paused','failed','succeeded'].includes(finalStatus))return result(true,'Owned job was already quiescent');
 if(!['queued','running'].includes(finalStatus))return result(false,'Unknown job state retained for review');
 if(clock()>=deadline)return result(false,'Containment deadline reached before pause request');
 const updated=await input.query(`UPDATE jobs SET pause_requested=true,
  status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=now()
  WHERE id=$1 AND type='ingest' AND payload->'requested_by'->>'id'=$2
  AND payload->'requested_by'->>'actor_type'='automated' AND status IN ('queued','running')
  RETURNING id,status,pause_requested`,[input.jobId,input.accountId]);
 if(updated.rowCount!==1){
  row=await read();if(!belongs(row))return result(false,'Ownership changed while requesting containment');
  finalStatus=String(row!.status);
  return result(['paused','failed','succeeded'].includes(finalStatus),'Concurrent state change; no forced transition');
 }
 pauseRequested=true;
 const event={event:'qa_executor_guard_pause',run_id:input.runId,actor_type:'automated',
  action:'pause_owned_ingestion',scope:'single_job',pause_requested:true};
 const inserted=await input.query(`INSERT INTO job_events(job_id,event)
  SELECT id,$3::jsonb FROM jobs WHERE id=$1 AND type='ingest'
  AND payload->'requested_by'->>'id'=$2 AND payload->'requested_by'->>'actor_type'='automated'
  RETURNING id`,[input.jobId,input.accountId,JSON.stringify(event)]);
 if(inserted.rowCount!==1)return result(false,'Pause requested but technical event could not be persisted under proven ownership');
 while(clock()<deadline){
  row=await read();if(!belongs(row))return result(false,'Ownership changed while awaiting quiescence');
  finalStatus=String(row!.status);
  if(['paused','failed','succeeded'].includes(finalStatus))return result(true,'Owned job quiesced without resuming or stopping any worker');
  await sleep(Math.min(250,Math.max(0,deadline-clock())));
 }
 return result(false,'Owned job did not quiesce within containment deadline; retain resources and block continuation');
}
