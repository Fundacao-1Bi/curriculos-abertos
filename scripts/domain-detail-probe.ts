import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { pool } from '../src/db/client';

// Bounded incident diagnostic, deliberately separate from the production load gate.
const id='ca:ac-cru-em:0090948210886854c3a6';
const publications=['ca-77fb8076598b567e1ba3','ca-77fb8076598b567e1ba3.r-1e4bc6d6-e20a-465d-b4b1-1c14a0c857ab'];
const base=process.env.DETAIL_PROBE_BASE_URL??'http://127.0.0.1:3000';
const started_at=new Date().toISOString();
const samples:{index:number;publication:string;status:number;ms:number;bytes:number;request_id:string|null}[]=[];
let next=0;
try {
 const stats=(await pool.query(`SELECT relname,n_live_tup,n_mod_since_analyze,last_analyze,last_autoanalyze FROM pg_stat_user_tables WHERE schemaname='public' AND relname=ANY($1::text[]) ORDER BY relname`,[['items','relation_members','relations','publications']])).rows;
 const database=(await pool.query('SELECT current_database() AS database,version() AS version')).rows[0];
 await Promise.all(Array.from({length:4},async()=>{
  while(next<24){
   const index=next++;const publication=publications[index%publications.length];
   const url=new URL(`/api/v1/aprendizagens/${encodeURIComponent(id)}`,base);url.searchParams.set('publication',publication);
   const start=performance.now();const response=await fetch(url);const body=await response.text();
   samples.push({index,publication,status:response.status,ms:performance.now()-start,bytes:Buffer.byteLength(body),request_id:response.headers.get('x-request-id')});
   assert.equal(response.status,200);const value=JSON.parse(body);assert.equal(value.publication,publication);assert.equal(value.data.id,id);assert.equal(value.data.source_id,'ac-cru-em');assert.ok(value.data.relations.length>0);
  }
 }));
 const times=samples.map(x=>x.ms).sort((a,b)=>a-b);
 const summary={requests:samples.length,concurrency:4,failures:samples.filter(x=>x.status!==200).length,p50_ms:times[Math.ceil(times.length*.5)-1],p95_ms:times[Math.ceil(times.length*.95)-1],max_ms:times.at(-1)};
 const report={producer:'scripts/domain-detail-probe.ts',started_at,completed_at:new Date().toISOString(),scope:'Small warm HTTP diagnostic of the exact previously slow item in two published snapshots. Not the final 10-client/200-request production performance gate; no cold-plan reproduction or causal attribution.',id,publications,database,planner_statistics:stats,summary,samples:samples.sort((a,b)=>a.index-b.index),exit_code:0};
 await writeFile('docs/evidence/detail-http-probe.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(summary));
}catch(error){console.error((error as Error).message);process.exitCode=1;}finally{await pool.end();}
