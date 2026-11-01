import {execFileSync} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';

const dbContainer='curriculos-abertos-clean-20261028205403-f517a7-db-1';
const credentials=execFileSync('docker',['exec',dbContainer,'sh','-lc','printf "%s\\n%s" "$POSTGRES_USER" "$POSTGRES_PASSWORD"'],{encoding:'utf8'}).split('\n');
if(credentials.length<2||!credentials[0]||!credentials[1])throw Error('QA container credentials unavailable');
const connection=new URL('postgresql://localhost:55439/curriculos_qa');
connection.username=credentials[0];connection.password=credentials[1];
process.env.DATABASE_URL=connection.toString();

const {pool}=await import('../../../src/db/client');
try{
 const db=(await pool.query('SELECT current_database() AS database')).rows[0]?.database;
 if(db!=='curriculos_qa')throw Error('Unexpected database; refusing composer');
 const before=(await pool.query('SELECT publication_id FROM current_publication')).rows[0]?.publication_id;
 if(before!=='ca-297c7ec9ab33fcaae579')throw Error('Unexpected QA default; refusing composer');
 const base='ca-7d302a9c674a97b83278';
 const baseSha='be4427301b0300d3ac751f9bb0627216ad84e5be16b9b733273e71522ec5360d';
 const actualBase=(await pool.query('SELECT sha256 FROM publications WHERE id=$1',[base])).rows[0]?.sha256;
 if(actualBase!==baseSha)throw Error('Pinned published base missing or checksum differs');
 const {prepareGlobalIngestionUpdate}=await import('../../../src/domain/ingestion-update');
 const rawArtifact='data/bundles/ca-e30b13fd827f056f79a0.manifest.json';
 const rawSha='0f444e874a9c6ec772597cb01c36270daa0881a0e3d8ce4e92c98e9413e0b202';
 const targets=[
  'ac-cru-ei-ef',
  'ac-cru-em',
  'es-resolucao-cee-es-no-5-190-2018-ei-e-ef',
  'es-resolucao-cee-es-no-5-777-2020-ensino-medio',
  'pi-parecer-190-2025',
  'sp-curriculo-eief-isbn',
  'sp-curriculo-em-isbn',
  'sp-educacao-digital-midiatica-2026',
  'sp-seduc156-anexos-matrizes-2026',
  'sp-seduc156-corpo-2026'
 ];
 const evaluationPath='var/jobs/sp-ac-es-pi190-acem-10-source-current-reissue-20261031/technical-evaluation.json';
 const result=await prepareGlobalIngestionUpdate({
  base_publication:base,
  target_source_ids:targets,
  raw_artifact:rawArtifact,
  raw_artifact_sha256:rawSha,
  base_artifact_sha256:baseSha,
  output_directory:resolve('data/bundles','ingestion-update-sp-ac-es-pi190-acem-ten-current-receipts-reissue-qa'),
  actor_id:'curriculos-abertos:sp-ac-es-pi190-acem-ten-current-receipts-reissue-qa-composer',
  provenance:{
   original_raw_receipt:{publication:'ca-e30b13fd827f056f79a0',artifact:rawArtifact,artifact_sha256:rawSha},
   raster_stage_receipt:null,
   technical_evaluation_receipt:{path:evaluationPath,sha256:'c47834cf41ef388bef931ad64a08dca9c22f0cc59c2bae96cdfa901dd9039600'},
   receipt_directory:'var/jobs/sp-ac-es-pi190-acem-10-source-current-reissue-20261031/receipts'
  }
 });
 const after=(await pool.query('SELECT publication_id FROM current_publication')).rows[0]?.publication_id;
 if(after!==before)throw Error('QA default changed during prepare-only composition');
 const report={schema:'sp-ac-es-pi190-acem-ten-current-receipts-reissue-global-composition-qa-v1',method:'prepareGlobalIngestionUpdate with exact published latest base, ten current-source RAW targets, reissued hash-pinned SourceWhole ES receipt and same-ID AC text correction technical provenance; no QA default or public pointer change',created_at:new Date().toISOString(),database:db,default_before:before,default_after:after,base_publication:base,base_sha256:baseSha,target_source_ids:targets,raw_publication:'ca-e30b13fd827f056f79a0',raw_artifact:rawArtifact,raw_artifact_sha256:rawSha,technical_evaluation_receipt:evaluationPath,technical_evaluation_receipt_sha256:'c47834cf41ef388bef931ad64a08dca9c22f0cc59c2bae96cdfa901dd9039600',publication:result.publication,artifact:result.artifact,artifact_sha256:result.artifact_sha256,import_receipt:result.import_receipt,raw_receipt:result.raw_receipt,provenance_receipt:result.provenance_receipt,update_scope:result.update_scope};
 const output='docs/evidence/source-audit-northeast/sp-ac-es-pi190-acem-ten-current-receipts-reissue-composition-qa.json';
 await mkdir('docs/evidence/source-audit-northeast',{recursive:true});
 await writeFile(output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({output,publication:result.publication,artifact:result.artifact,artifact_sha256:result.artifact_sha256,default_before:before,default_after:after,preserved_sources:result.update_scope.unaffected_sources.length,relations_before:result.update_scope.relations_excluding_target.before_count,relations_after:result.update_scope.relations_excluding_target.after_count,coverage_before:result.update_scope.coverage_excluding_target.before_count,coverage_after:result.update_scope.coverage_excluding_target.after_count,technical_events_sha256:result.provenance_receipt?.technical_events_sha256}));
}catch(error){console.error(JSON.stringify({error_code:(error as {code?:string}).code??null,error_message:(error as Error).message}));process.exitCode=1;}finally{await pool.end();}
