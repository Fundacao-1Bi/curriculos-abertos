import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const dbContainer='curriculos-abertos-clean-20261028205403-f517a7-db-1';
const password=execFileSync('docker',['exec',dbContainer,'sh','-c','printf %s "$POSTGRES_PASSWORD"'],{encoding:'utf8'}).trim();
const connection=new URL('postgresql://curriculos_qa@127.0.0.1:55439/curriculos_qa');
connection.password=password;
// Scope the PostgreSQL planner adjustment to this process's QA connections only.
connection.searchParams.set('options','-c enable_nestloop=off');
process.env.DATABASE_URL=connection.toString();

const base='ca-7d302a9c674a97b83278';
const raw='ca-4a608c1dc23a0d9e4d8e';
const targets=['ac-cru-ei-ef','sp-curriculo-eief-isbn','sp-curriculo-em-isbn','sp-seduc156-anexos-matrizes-2026','sp-educacao-digital-midiatica-2026','sp-seduc156-corpo-2026'];
const basePath='data/bundles/ca-7d302a9c674a97b83278.manifest.json';
const rawPath='data/bundles/ca-4a608c1dc23a0d9e4d8e.manifest.json';
const baseBytes=await readFile(basePath),rawBytes=await readFile(rawPath);
const baseSha=createHash('sha256').update(baseBytes).digest('hex');
const rawSha=createHash('sha256').update(rawBytes).digest('hex');
if(baseSha!=='be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d')throw new Error('Base artifact SHA changed');
if(rawSha!=='8bdbbfec60b30f87f3dd0fbd3ccf80d8a5193a52305a5efbe7bf36e28f6b71fd')throw new Error('RAW artifact SHA changed');

const {pool}=await import('../src/db/client');
try{
 const baseRow=(await pool.query('SELECT sha256,item_count,source_count FROM publications WHERE id=$1',[base])).rows[0];
 if(!baseRow||baseRow.sha256!==baseSha||baseRow.item_count!==200724||baseRow.source_count!==303)throw new Error('QA database base differs from the pinned artifact');
 const before=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 if(before!=='ca-297c7ec9ab33fcaae579')throw new Error('Unexpected QA default; refusing composition');
 const {prepareGlobalIngestionUpdate}=await import('../src/domain/ingestion-update');
 let stopMonitor=false,statsAnalyzed=false;
 const statsMonitor=(async()=>{
  while(!stopMonitor){
   const candidateRow=(await pool.query("SELECT id FROM publications WHERE payload->'update_scope'->>'base_publication'=$1 AND payload->'update_scope'->'target_source_ids'=$2::jsonb LIMIT 1",[base,JSON.stringify(targets)])).rows[0];
   if(candidateRow){
    // Import commits before preservation proofs. Analyze during the base proof
    // so candidate reads use current publication-level statistics.
    await pool.query('ANALYZE items');
    await pool.query('ANALYZE sources');
    await pool.query('ANALYZE relations');
    await pool.query('ANALYZE relation_members');
    await pool.query('ANALYZE publication_coverage');
    statsAnalyzed=true;break;
   }
   await new Promise(resolve=>setTimeout(resolve,500));
  }
 })();
 let result;
 try{
  result=await prepareGlobalIngestionUpdate({
   base_publication:base,
   target_source_ids:targets,
   raw_artifact:rawPath,
   raw_artifact_sha256:rawSha,
   base_artifact_sha256:baseSha,
   output_directory:resolve('data/bundles','ingestion-update-sp-ac-six-source-qa'),
   actor_id:'curriculos-abertos:sp-ac-six-source-qa-composition'
  });
 }finally{stopMonitor=true;}
 await statsMonitor;
 const after=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 if(after!==before)throw new Error('QA default changed during private composition');
 const report={
  schema:'sp-ac-four-source-global-composition-qa-v1',checked_at:new Date().toISOString(),actor_type:'automated',
  method:'prepareGlobalIngestionUpdate on isolated QA database; six current whole-source RAW targets; planner options and post-import ANALYZE scoped to this QA run; no publication/default change',
  base_publication:base,base_artifact_sha256:baseSha,raw_publication:raw,raw_artifact_sha256:rawSha,
  target_source_ids:targets,qa_default_before:before,qa_default_after:after,post_import_analyze_completed:statsAnalyzed,result
 };
 const out='docs/evidence/source-audit-sp/sp-ac-six-source-global-composition-qa.json';
 await mkdir('docs/evidence/source-audit-sp',{recursive:true});
 await writeFile(out,JSON.stringify(report,null,2)+'\n',{mode:0o644});
 console.log(JSON.stringify({publication:result.publication,artifact_sha256:result.artifact_sha256,source_count:result.import_receipt.source_count,item_count:result.import_receipt.item_count,relation_count:result.import_receipt.relation_count,unaffected_sources:result.update_scope.unaffected_sources.length,unaffected_relations:result.update_scope.relations_excluding_target,unaffected_coverage:result.update_scope.coverage_excluding_target,qa_default_before:before,qa_default_after:after,evidence:out}));
}finally{await pool.end();}
