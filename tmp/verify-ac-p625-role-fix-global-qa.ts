import {execFileSync} from 'node:child_process';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const dbContainer='curriculos-abertos-clean-20261028205403-f517a7-db-1';
const password=execFileSync('docker',['exec',dbContainer,'sh','-c','printf %s "$POSTGRES_PASSWORD"'],{encoding:'utf8'}).trim();
const connection=new URL('postgresql://curriculos_qa@127.0.0.1:55439/curriculos_qa');
connection.password=password;
process.env.DATABASE_URL=connection.toString();
// ANALYZE was run after private import; fresh statistics let PostgreSQL choose
// a merge join over the (publication_id,id) primary key for exact JSONB equality.

const base='ca-7d302a9c674a97b83278';
const candidate='ca-update-083f49d783a8db16f357396ac9608a90';
const basePath='data/bundles/ca-7d302a9c674a97b83278.manifest.json';
const candidatePath='data/bundles/ingestion-update-ac-p625-role-fix-qa/snapshot.manifest.json';
const baseSha=createHash('sha256').update(await readFile(basePath)).digest('hex');
const candidateSha=createHash('sha256').update(await readFile(candidatePath)).digest('hex');
const {pool}=await import('../src/db/client');
try{
 const rows=(await pool.query("SELECT p.sha256,p.item_count,p.source_count,v.status FROM publications p JOIN publication_visibility v ON v.publication_id=p.id WHERE p.id=$1",[candidate])).rows;
 if(rows.length!==1||rows[0].sha256!==candidateSha||rows[0].item_count!==200724||rows[0].source_count!==303||rows[0].status!=='prepared')throw new Error('Prepared candidate does not match its pinned artifact and expected inventory');
 const before=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 if(before!=='ca-297c7ec9ab33fcaae579')throw new Error('Unexpected QA default before verification');
 const {verifyGlobalIngestionPreservation}=await import('../src/domain/ingestion-update');
 const proof=await verifyGlobalIngestionPreservation(base,candidate,['ac-cru-ei-ef'],'curriculos-abertos:ac-p625-role-fix-qa-composition');
 const after=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 if(after!==before)throw new Error('QA default changed during verification');
 const report={schema:'ac-p625-role-fix-global-composition-qa-v1',checked_at:new Date().toISOString(),actor_type:'automated',method:'Prepared private candidate revalidated with domain preservation proof after ANALYZE; exact PostgreSQL JSONB checks use primary-key merge join; no publication/default change',base_publication:base,base_artifact_sha256:baseSha,candidate_publication:candidate,candidate_artifact_sha256:candidateSha,target_source_ids:['ac-cru-ei-ef'],qa_default_before:before,qa_default_after:after,proof};
 const out='docs/evidence/source-audit-ac/ac-p625-role-fix-global-composition-qa.json';
 await mkdir('docs/evidence/source-audit-ac',{recursive:true});
 await writeFile(out,JSON.stringify(report,null,2)+'\n',{mode:0o644});
 console.log(JSON.stringify({candidate,artifact_sha256:candidateSha,source_count:rows[0].source_count,item_count:rows[0].item_count,status:rows[0].status,proof_mode:proof.mode,base:proof.base_publication,candidate_verified:proof.candidate_publication,unaffected_sources:proof.unaffected_sources.length,relations:proof.relations_excluding_target,coverage:proof.coverage_excluding_target,qa_default_before:before,qa_default_after:after,evidence:out}));
}finally{await pool.end();}
