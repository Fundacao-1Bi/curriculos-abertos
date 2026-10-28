import { spawn, type ChildProcess } from 'node:child_process';
import { mkdir, readFile, rename } from 'node:fs/promises';
import { dirname } from 'node:path';
import { randomUUID } from 'node:crypto';
import { pool } from '../db/client';
import { claimJob, enqueueJob, jobEvent, safeExportPath, type Job } from './jobs';
import { streamExportToFile } from '../domain/stream-exports';
import type { Query } from '../shared/contracts';
const owner=`worker-${randomUUID()}`;
let stopping=false;
let activeChild:ChildProcess|null=null;
let activeJob:string|null=null;
function log(event:Record<string,unknown>) { process.stdout.write(JSON.stringify({at:new Date().toISOString(),worker:owner,...event})+'\n'); }
function sleep(ms:number){return new Promise<void>(resolve=>setTimeout(resolve,ms));}
const killTimers=new Map<ChildProcess,NodeJS.Timeout>();
function terminateChild(child=activeChild){
  if(!child || child.exitCode!==null)return;
  child.kill('SIGTERM');
  if(!killTimers.has(child)){const timer=setTimeout(()=>child.kill('SIGKILL'),5000);timer.unref();killTimers.set(child,timer);child.once('close',()=>{clearTimeout(timer);killTimers.delete(child);});}
}
for(const signal of ['SIGTERM','SIGINT'] as const)process.on(signal,()=>{stopping=true;terminateChild();});
async function runPipeline(job:Job) {
  const args=['pipeline/ingest.py',job.type==='source-check'?'sources-check':'ingest','--job-id',job.id];
  if(typeof job.payload.source==='string') {
    if(!/^[a-zA-Z0-9_.:-]{1,200}$/.test(job.payload.source))throw new Error('ID da fonte inválido.');
    args.push('--source',job.payload.source);
  }
  // Every parameter is a discrete argv; source data never becomes a shell program.
  const child=spawn(process.env.PYTHON_BIN || 'python3',args,{stdio:['ignore','pipe','pipe'],env:process.env});
  activeChild=child;
  let buffer='',stderr='',outputBytes=0;
  const timeout=setTimeout(()=>terminateChild(child),Number(process.env.JOB_TIMEOUT_SECONDS || 7200)*1000);
  const pending:Promise<unknown>[]=[];
  child.stdout.on('data',(chunk:Buffer)=>{
    outputBytes+=chunk.length;
    if(outputBytes>10*1024*1024){terminateChild(child);return;}
    buffer+=chunk.toString();
    const lines=buffer.split('\n');buffer=lines.pop() || '';
    for(const line of lines) {
      let event:Record<string,unknown>;
      try { event=JSON.parse(line); } catch { event={message:line.slice(0,1000)}; }
      pending.push(jobEvent(job.id,{...event,attempt:job.attempts}).catch(()=>{terminateChild(child);}));
      pending.push(pool.query("UPDATE jobs SET progress=$2::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running'",[job.id,JSON.stringify(event),owner,job.attempts]).catch(()=>{terminateChild(child);}));
      log({job_id:job.id,stage:event.stage || event.event || 'pipeline'});
    }
  });
  child.stderr.on('data',(chunk:Buffer)=>{stderr=(stderr+chunk.toString()).slice(-4000);});
  try {
    const code=await new Promise<number|null>((resolve,reject)=>{child.on('error',reject);child.on('close',resolve);});
    await Promise.all(pending);
    if(stderr)await jobEvent(job.id,{warning:'Pipeline emitiu mensagens diagnósticas; confira logs locais restritos.'});
    if(job.type==='source-check') {
      try {
        let report:Record<string,unknown>;
        try{report=JSON.parse(await readFile(`var/source-monitor/${job.id}.json`,'utf8'));}
        catch{report=JSON.parse(await readFile('var/source-monitor/latest.json','utf8'));if(report.job_id!==job.id)throw new Error('Monitor report de outro job.');}
        const rows=Array.isArray(report)?report:(report.sources || report.checks || report.results || []) as Record<string,unknown>[];
        for(const row of rows) {
          if(!row.source_id && !row.id)continue;
          await pool.query('INSERT INTO source_checks(id,source_id,status,prior_hash,observed_hash,detail) VALUES($1,$2,$3,$4,$5,$6::jsonb)',[randomUUID(),row.source_id || row.id,row.status || 'checked',row.prior_hash || row.baseline_sha256 || null,row.sha256 || row.observed_hash || null,JSON.stringify(row)]);
        }
      }catch{await jobEvent(job.id,{warning:'Relatório do monitor não pôde ser carregado na administração.'});}
    }
    if(code!==0)throw new Error(stopping?'Worker interrompido.':`Pipeline terminou com código ${code}; consulte o checkpoint do job.`);
    return {checkpoint:`var/jobs/${job.id}.json`,stage:'complete'};
  }finally{clearTimeout(timeout);activeChild=null;}
}
async function execute(job:Job) {
  if(job.type==='export') {
    const format=job.payload.format==='csv'?'csv':'json';
    const query=(job.payload.query || {}) as Query;
    if(!query.publication)throw new Error('Exportação exige publicação fixada.');
    const storage_key=`exports/${job.id}/${job.attempts}-${owner.slice(7)}.${format}`;
    const path=safeExportPath(storage_key);
    await mkdir(dirname(path),{recursive:true});
    const temporary=`${path}.tmp-${owner}`;
    await pool.query("UPDATE jobs SET progress=$2::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running'",[job.id,JSON.stringify({stage:'exporting',publication:query.publication,format}),owner,job.attempts]);
    const result=await streamExportToFile(query,format,temporary);
    await rename(temporary,path);
    return {...result,storage_key};
  }
  if(job.type==='ingest' || job.type==='source-check')return runPipeline(job);
  if(job.type==='validate') {
    const { validateDraft }=await import('../admin/curation');
    if(typeof job.payload.draft_id!=='string')throw new Error('Draft ausente.');
    return validateDraft(job.payload.draft_id);
  }
  throw new Error('Tipo de job não implementado.');
}
async function main() {
  const interval=Math.max(60,Number(process.env.SOURCE_CHECK_INTERVAL_SECONDS || 86400));
  let lastSchedule=0;
  log({event:'worker_started'});
  while(!stopping) {
    try {
      await pool.query('INSERT INTO worker_heartbeats(id,active_job) VALUES($1,$2) ON CONFLICT(id) DO UPDATE SET seen_at=now(),active_job=excluded.active_job',[owner,activeJob]);
      if(Date.now()-lastSchedule>interval*1000) {
        const bucket=Math.floor(Date.now()/(interval*1000));
        if(process.env.SOURCE_CHECK_ENABLED==='true')await enqueueJob('source-check',{},`source-check:${bucket}`);
        lastSchedule=Date.now();
      }
      await pool.query("UPDATE jobs SET status='failed',error='Limite de tentativas atingido após expiração de lease.',lease_owner=NULL,lease_until=NULL,updated_at=now() WHERE status='running' AND lease_until<now() AND attempts>=max_attempts");
      const job=await claimJob(owner);
      if(!job){await sleep(1500);continue;}
      activeJob=job.id;
      await jobEvent(job.id,{event:'started',attempt:job.attempts,worker:owner});
      let leaseLost=false;
      const heartbeat=setInterval(()=>{
        void pool.query("UPDATE jobs SET lease_until=now()+interval '45 seconds',updated_at=now() WHERE id=$1 AND lease_owner=$2 AND attempts=$3 AND status='running' RETURNING pause_requested",[job.id,owner,job.attempts]).then(result=>{
          if(!result.rowCount){leaseLost=true;if(activeJob===job.id)terminateChild();}
          else if(result.rows[0]?.pause_requested&&activeJob===job.id)terminateChild();
        }).catch(()=>{leaseLost=true;if(activeJob===job.id)terminateChild();log({job_id:job.id,event:'lease_renewal_failed'});});
        void pool.query('UPDATE worker_heartbeats SET seen_at=now(),active_job=$2 WHERE id=$1',[owner,job.id]).catch(()=>{log({event:'heartbeat_write_failed',job_id:job.id});});
      },10000);
      try {
        const result=await execute(job);
        if(leaseLost){log({job_id:job.id,event:'lease_lost_result_discarded'});continue;}
        const pause=(await pool.query('SELECT pause_requested FROM jobs WHERE id=$1',[job.id])).rows[0]?.pause_requested;
        if(stopping || pause) {
          const updated=await pool.query("UPDATE jobs SET status=$2,lease_owner=NULL,lease_until=NULL,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running'",[job.id,pause?'paused':'queued',owner,job.attempts]);
          if(updated.rowCount)await jobEvent(job.id,{event:pause?'paused':'interrupted'});
          else log({job_id:job.id,event:'lease_lost_result_discarded'});
        }else {
          const updated=await pool.query("UPDATE jobs SET status='succeeded',result=$2::jsonb,lease_owner=NULL,lease_until=NULL,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running'",[job.id,JSON.stringify(result),owner,job.attempts]);
          if(updated.rowCount)await jobEvent(job.id,{event:'succeeded'});
          else log({job_id:job.id,event:'lease_lost_result_discarded'});
        }
      }catch(error) {
        if(leaseLost){log({job_id:job.id,event:'lease_lost_error_discarded'});continue;}
        const pause=(await pool.query('SELECT pause_requested FROM jobs WHERE id=$1',[job.id])).rows[0]?.pause_requested;
        const message=error instanceof Error?error.message.slice(0,1000):'Falha de processamento.';
        const status=pause?'paused':stopping?'queued':job.attempts<job.max_attempts?'queued':'failed';
        const updated=await pool.query("UPDATE jobs SET status=$2,error=$3,lease_owner=NULL,lease_until=NULL,run_after=now()+($4*interval '1 second'),updated_at=now() WHERE id=$1 AND lease_owner=$5 AND attempts=$6 AND status='running'",[job.id,status,message,Math.min(300,2**job.attempts*5),owner,job.attempts]);
        if(updated.rowCount)await jobEvent(job.id,{event:status,message});
        else log({job_id:job.id,event:'lease_lost_error_discarded'});
        log({job_id:job.id,event:status});
      }finally{clearInterval(heartbeat);activeJob=null;}
    }catch(error) {log({event:'worker_error',message:error instanceof Error?error.message:'Erro'});await sleep(5000);}
  }
  await pool.query('DELETE FROM worker_heartbeats WHERE id=$1',[owner]);
  await pool.end();
  log({event:'worker_stopped'});
}
main().catch(()=>{log({event:'fatal_worker_error'});process.exitCode=1;});
