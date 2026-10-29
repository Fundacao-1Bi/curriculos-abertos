import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { resolve, sep } from 'node:path';
import { pool } from '../db/client';
import { resolvePublication } from '../domain/service';
import { DomainError } from '../domain/errors';
import {readdir,readFile} from 'node:fs/promises';
export type Job = {id:string;type:string;status:'queued'|'running'|'paused'|'succeeded'|'failed';payload:Record<string,unknown>;result:Record<string,unknown>|null;progress:Record<string,unknown>;error:string|null;attempts:number;max_attempts:number;lease_owner:string|null;created_at:string;updated_at:string};
async function ingestionTargetSources(source:unknown):Promise<string[]> {
  if(source!==undefined&&(typeof source!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._-]{0,239}$/.test(source)))throw new DomainError(422,'INVALID_SOURCE_SCOPE','ID de fonte inválido.');
  const directory=resolve('data/manifests'),registered=new Map<string,{included:boolean;uf:unknown}>();
  for(const file of await readdir(directory,{withFileTypes:true})){
    if(!file.isFile()||!file.name.endsWith('.json'))continue;
    const value=JSON.parse(await readFile(resolve(directory,file.name),'utf8'));
    const rows=Array.isArray(value)?value:value.sources;
    if(!Array.isArray(rows))continue;
    for(const row of rows){
      if(!row||typeof row.id!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._-]{0,239}$/.test(row.id))throw new DomainError(422,'INVALID_SOURCE_SCOPE','Inventário contém ID inválido.');
      if(registered.has(row.id))throw new DomainError(422,'DUPLICATE_SOURCE_SCOPE','Inventário contém fonte duplicada.');
      registered.set(row.id,{included:row.include_in_corpus!==false&&row.publication_eligible!==false,uf:row.uf});
    }
  }
  if(source!==undefined&&!registered.get(source as string)?.included)throw new DomainError(422,'INVALID_SOURCE_SCOPE','Fonte solicitada não está registrada para processamento.');
  if(source!==undefined&&registered.get(source as string)?.uf==='BR')throw new DomainError(422,'NATIONAL_UPDATE_REQUIRES_GLOBAL_REBUILD','Atualizar o referencial nacional exige reconstrução explícita dos vínculos dependentes.');
  const targets=source===undefined?[...registered].filter(([,row])=>row.included&&row.uf!=='BR').map(([id])=>id):[source as string];
  if(!targets.length)throw new DomainError(422,'EMPTY_SOURCE_SCOPE','Atualização exige fontes alvo registradas.');
  if(targets.length>500)throw new DomainError(422,'SOURCE_SCOPE_TOO_LARGE','Atualização admite até 500 fontes alvo; separe as solicitações.');
  return targets.sort();
}
export async function enqueueJob(type:string,payload:Record<string,unknown>,idempotencyKey?:string):Promise<Job> {
  if(!['ingest','source-check','export','validate'].includes(type)) throw new Error('Tipo de job não permitido.');
  if(type==='ingest'){
    if(idempotencyKey){const existing=(await pool.query<Job>('SELECT * FROM jobs WHERE idempotency_key=$1',[idempotencyKey])).rows[0];if(existing){if(existing.type!==type)throw new DomainError(409,'IDEMPOTENCY_CONFLICT','Chave de idempotência já usada por outro tipo de job.');return existing;}}
    const target_sources=await ingestionTargetSources(payload.source),client=await pool.connect();
    try{
      await client.query('BEGIN');await client.query('SELECT pg_advisory_xact_lock(81726354)');
      const base=(await client.query("SELECT p.id,p.sha256 FROM current_publication c JOIN publications p ON p.id=c.publication_id JOIN publication_visibility v ON v.publication_id=p.id WHERE c.singleton=true AND v.status='published'")).rows[0];
      if(!base)throw new DomainError(409,'INGESTION_BASE_REQUIRED','Importe e publique uma base antes de iniciar atualização global.');
      const fixed={...payload,base_publication:base.id,base_publication_sha256:base.sha256,target_sources,update_mode:'base-plus-source-update'};
      if(JSON.stringify(fixed).length>20000)throw new DomainError(422,'JOB_PAYLOAD_TOO_LARGE','Escopo da atualização excede o limite de payload. Solicite fontes separadamente.');
      const result=await client.query<Job>('INSERT INTO jobs(id,type,payload,idempotency_key) VALUES($1,$2,$3::jsonb,$4) ON CONFLICT(idempotency_key) DO UPDATE SET idempotency_key=excluded.idempotency_key RETURNING *',[randomUUID(),type,JSON.stringify(fixed),idempotencyKey||null]);
      if(result.rows[0].type!==type)throw new DomainError(409,'IDEMPOTENCY_CONFLICT','Chave de idempotência já usada por outro tipo de job.');
      await client.query('COMMIT');return result.rows[0];
    }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
  }
  if(JSON.stringify(payload).length>20000) throw new Error('Payload do job excede o limite.');
  const id=randomUUID();
  const result=await pool.query<Job>('INSERT INTO jobs(id,type,payload,idempotency_key) VALUES($1,$2,$3::jsonb,$4) ON CONFLICT(idempotency_key) DO UPDATE SET idempotency_key=excluded.idempotency_key RETURNING *',[id,type,JSON.stringify(payload),idempotencyKey || null]);
  return result.rows[0];
}
export async function getJob(id:string):Promise<Job|null> {
  if(!z.uuid().safeParse(id).success)return null;
  return (await pool.query<Job>('SELECT * FROM jobs WHERE id=$1',[id])).rows[0] || null;
}
export async function getPublicExport(id:string) {
  const job=await getJob(id);
  if(!job || job.type!=='export')return null;
  const query=job.payload.query as {publication?:string}|undefined;
  if(typeof query?.publication!=='string')return null;
  try{await resolvePublication(query.publication);}catch(error){if(error instanceof DomainError&&error.status===404)return null;throw error;}
  if(job.result&&job.result.publication!==query.publication)return null;
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
