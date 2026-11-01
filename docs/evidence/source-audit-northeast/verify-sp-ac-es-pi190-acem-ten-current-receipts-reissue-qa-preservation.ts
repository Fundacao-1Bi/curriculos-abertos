import {execFileSync} from 'node:child_process';

const dbContainer='curriculos-abertos-clean-20261028205403-f517a7-db-1';
const credentials=execFileSync('docker',['exec',dbContainer,'sh','-lc','printf "%s\\n%s" "$POSTGRES_USER" "$POSTGRES_PASSWORD"'],{encoding:'utf8'}).split('\n');
if(credentials.length<2||!credentials[0]||!credentials[1])throw Error('QA container credentials unavailable');
const connection=new URL('postgresql://localhost:55439/curriculos_qa');
connection.username=credentials[0];connection.password=credentials[1];process.env.DATABASE_URL=connection.toString();

const {pool}=await import('../../../src/db/client');
const base='ca-7d302a9c674a97b83278';
const candidate='ca-update-ad940b94fa9214ecf6b3d9cbc2abf46f';
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
try{
 const db=(await pool.query('SELECT current_database() AS database')).rows[0]?.database;
 const defaultPublication=(await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
 const artifact=(await pool.query('SELECT sha256,payload->\'update_scope\' AS scope FROM publications WHERE id=$1',[candidate])).rows[0];
 if(db!=='curriculos_qa'||defaultPublication!=='ca-297c7ec9ab33fcaae579')throw Error('Unexpected QA database/default; refusing verification');
 if(!artifact||artifact.scope?.base_publication!==base||JSON.stringify(artifact.scope.target_source_ids)!==JSON.stringify(targets))throw Error('Candidate lineage or target scope mismatch');
 const {verifyGlobalIngestionPreservation}=await import('../../../src/domain/ingestion-update');
 const result=await verifyGlobalIngestionPreservation(base,candidate,targets,'curriculos-abertos:sp-ac-es-pi190-acem-ten-current-receipts-reissue-qa-composer');
 console.log(JSON.stringify({database:db,default_publication:defaultPublication,candidate,artifact_sha256:artifact.sha256,preservation:result},null,2));
}finally{await pool.end();}
