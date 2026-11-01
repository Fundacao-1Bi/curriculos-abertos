import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const dbContainer='curriculos-abertos-clean-20261028205403-f517a7-db-1';
const password=execFileSync('docker',['exec',dbContainer,'sh','-c','printf %s "$POSTGRES_PASSWORD"'],{encoding:'utf8'}).trim();
if(!password)throw new Error('QA database password was unavailable');
const connection=new URL('postgresql://curriculos_qa@127.0.0.1:55439/curriculos_qa');
connection.password=password;
process.env.DATABASE_URL=connection.toString();

const base='ca-7d302a9c674a97b83278';
const raw='ca-11ade612fb97b7427fca';
const currentExpected='ca-297c7ec9ab33fcaae579';
const basePath='data/bundles/ca-7d302a9c674a97b83278.manifest.json';
const rawPath='data/bundles/ca-11ade612fb97b7427fca.manifest.json';
const baseBytes=await readFile(basePath),rawBytes=await readFile(rawPath);
const baseSha=createHash('sha256').update(baseBytes).digest('hex');
const rawSha=createHash('sha256').update(rawBytes).digest('hex');
if(baseSha!=='be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d')throw new Error('Base artifact SHA changed');
if(rawSha!=='7e1cc9944c1dd813a0972ebff75429ef901712a700d151a4d52987db8947d9fc')throw new Error('RAW artifact SHA changed');

const {pool}=await import('../src/db/client');
try{
 const baseRow=(await pool.query('SELECT sha256,item_count,source_count FROM publications WHERE id=$1',[base])).rows[0];
 if(!baseRow||baseRow.sha256!==baseSha||baseRow.item_count!==200724||baseRow.source_count!==303)throw new Error('QA database base does not match the pinned artifact');
 const currentBefore=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 if(currentBefore!==currentExpected)throw new Error('Unexpected QA default publication; refusing composition');
 const {prepareGlobalIngestionUpdate}=await import('../src/domain/ingestion-update');
 const result=await prepareGlobalIngestionUpdate({
  base_publication:base,
  target_source_ids:['ac-cru-ei-ef'],
  raw_artifact:rawPath,
  raw_artifact_sha256:rawSha,
  base_artifact_sha256:baseSha,
  output_directory:resolve('data/bundles','ingestion-update-ac-p625-role-fix-qa'),
  actor_id:'curriculos-abertos:ac-p625-role-fix-qa-composition'
 });
 const currentAfter=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 if(currentAfter!==currentBefore)throw new Error('QA default changed during private composition');
 const report={
  schema:'ac-p625-role-fix-global-composition-qa-v1',
  checked_at:new Date().toISOString(),
  actor_type:'automated',
  method:'prepareGlobalIngestionUpdate on isolated QA database; direct domain invocation without worker job provenance; no publication or default change',
  base_publication:base,
  base_artifact_sha256:baseSha,
  raw_publication:raw,
  raw_artifact_sha256:rawSha,
  target_source_ids:['ac-cru-ei-ef'],
  qa_default_before:currentBefore,
  qa_default_after:currentAfter,
  result
 };
 const out='docs/evidence/source-audit-ac/ac-p625-role-fix-global-composition-qa.json';
 await mkdir('docs/evidence/source-audit-ac',{recursive:true});
 await writeFile(out,JSON.stringify(report,null,2)+'\n',{mode:0o644});
 console.log(JSON.stringify({publication:result.publication,artifact_sha256:result.artifact_sha256,source_count:result.import_receipt.source_count,item_count:result.import_receipt.item_count,relation_count:result.import_receipt.relation_count,unaffected_sources:result.update_scope.unaffected_sources.length,unaffected_relations:result.update_scope.relations_excluding_target,unaffected_coverage:result.update_scope.coverage_excluding_target,qa_default_before:currentBefore,qa_default_after:currentAfter,evidence:out}));
}finally{await pool.end();}
