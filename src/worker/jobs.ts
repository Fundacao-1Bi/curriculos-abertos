import { randomUUID } from 'node:crypto';
import { resolve, sep } from 'node:path';
import { pool } from '../db/client';
export type Job = {id:string;type:string;status:'queued'|'running'|'paused'|'succeeded'|'failed';payload:Record<string,unknown>;result:Record<string,unknown>|null;progress:Record<string,unknown>;error:string|null;attempts:number;max_attempts:number;lease_owner:string|null;created_at:string;updated_at:string};
export async function enqueueJob(type:string,payload:Record<string,unknown>,idempotencyKey?:string):Promise<Job> {
  if(!['ingest','source-check','export','validate'].includes(type)) throw new Error('Tipo de job não permitido.');
  if(JSON.stringify(payload).length>20000) throw new Error('Payload do job excede o limite.');
  const id=randomUUID();
  const result=await pool.query<Job>('INSERT INTO jobs(id,type,payload,idempotency_key) VALUES($1,$2,$3::jsonb,$4) ON CONFLICT(idempotency_key) DO UPDATE SET idempotency_key=excluded.idempotency_key RETURNING *',[id,type,JSON.stringify(payload),idempotencyKey || null]);
  return result.rows[0];
}
export async function getJob(id:string):Promise<Job|null> {
  if(!/^[a-f0-9-]{36}$/i.test(id))return null;
  return (await pool.query<Job>('SELECT * FROM jobs WHERE id=$1',[id])).rows[0] || null;
}
export async function getPublicExport(id:string) {
  const job=await getJob(id);
  if(!job || job.type!=='export')return null;
  const query=job.payload.query as {publication?:string}|undefined;
  return {id:job.id,status:job.status,publication:query?.publication || null,progress:job.progress,result:job.result,error:job.error ? 'A exportação falhou. Tente novamente mais tarde.' : null};
}
export function safeExportPath(storageKey:string) {
  if(!/^exports\/[a-f0-9-]{36}(?:\/[0-9]{1,4}-[a-f0-9-]{36})?\.(json|csv)$/.test(storageKey))throw new Error('Chave de exportação inválida.');
  const root=resolve(/* turbopackIgnore: true */ process.env.EXPORT_STORAGE_DIR || process.env.STORAGE_DIR || 'var');
  const result=resolve(/* turbopackIgnore: true */ root,storageKey);
  if(!result.startsWith(root+sep))throw new Error('Caminho inválido.');
  return result;
}
export async function jobEvent(id:string,event:Record<string,unknown>) {
  await pool.query('INSERT INTO job_events(job_id,event) VALUES($1,$2::jsonb)',[id,JSON.stringify(event)]);
}
export async function claimJob(owner:string):Promise<Job|null> {
  const result=await pool.query<Job>(`WITH candidate AS (
    SELECT id FROM jobs WHERE pause_requested=false AND attempts<max_attempts AND run_after<=now()
      AND (status='queued' OR (status='running' AND lease_until<now()))
    ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
  ) UPDATE jobs SET status='running',attempts=attempts+1,lease_owner=$1,lease_until=now()+interval '45 seconds',updated_at=now()
    FROM candidate WHERE jobs.id=candidate.id RETURNING jobs.*`,[owner]);
  return result.rows[0] || null;
}
export async function controlJob(id:string,action:'pause'|'resume'|'retry') {
  if(!/^[a-f0-9-]{36}$/i.test(id))throw new Error('ID de job inválido.');
  let result;
  if(action==='pause') result=await pool.query("UPDATE jobs SET pause_requested=true,status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=now() WHERE id=$1 AND status IN ('queued','running') RETURNING *",[id]);
  else result=await pool.query("UPDATE jobs SET pause_requested=false,status='queued',attempts=CASE WHEN $2='retry' OR attempts>=max_attempts THEN 0 ELSE attempts END,lease_owner=NULL,lease_until=NULL,error=NULL,run_after=now(),updated_at=now() WHERE id=$1 AND status IN ('paused','failed') RETURNING *",[id,action]);
  if(!result.rows[0])throw new Error('O job não está em um estado compatível com a ação.');
  await jobEvent(id,{action});
  return result.rows[0];
}
