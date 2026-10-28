/** Exercise shipped backup/restore against the clean QA project and a separate disposable database. */
import assert from 'node:assert/strict';
import { existsSync,mkdirSync,readFileSync,writeFileSync,readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compose,loadCleanState,run,sql,snapshotSql,waitReady } from './qa-production';
import { sourceTreeHash } from './release-check';
import { hashArtifactFile,openAuditArtifact,inspectAuditArtifact } from './audit-artifact';
const started_at=new Date().toISOString();const checks:{name:string;passed:boolean;detail?:unknown}[]=[];
const digest=hashArtifactFile;
try{
const state=loadCleanState();assert.equal(state.source_tree_sha256,sourceTreeHash(),'QA deve corresponder ao código atual');
const before=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;assert.deepEqual(before,state.snapshot);assert.ok(state.artifact,'Instalação QA precisa identificar artefato e partes verificados');
await waitReady(state.base_url);
const expectedFiles:{path:string;sha256:string}[]=[];async function collect(directory:string){for(const entry of readdirSync(directory,{withFileTypes:true})){if(entry.name.startsWith('.'))continue;const path=join(directory,entry.name);assert.ok(!entry.isSymbolicLink(),'Backup de dados não aceita links simbólicos');if(entry.isDirectory())await collect(path);else if(entry.isFile())expectedFiles.push({path,sha256:await digest(path)});}}await collect('data/manifests');await collect('data/bundles');expectedFiles.push({path:'data/coverage-manifest.json',sha256:await digest('data/coverage-manifest.json')});
const env={COMPOSE_PROJECT_NAME:state.project,COMPOSE_ENV_FILES:state.env_file};
const isolatedConfig=JSON.parse(String(run('docker',['compose','config','--format','json'],{env}))) as {name:string;services:{db:{environment:{POSTGRES_DB:string}}}};assert.equal(isolatedConfig.name,state.project);assert.equal(isolatedConfig.services.db.environment.POSTGRES_DB,'curriculos_qa','Backup deve usar somente o projeto QA isolado');
const output=String(run('bash',['scripts/ops-backup.sh'],{env}));const match=output.match(/var\/backups\/[^\s]+/);assert.ok(match,'Comando backup precisa informar diretório criado');const backup=match[0];
const manifest=JSON.parse(readFileSync(join(backup,'manifest.json'),'utf8')) as {checksums:Record<string,string>;contains_admin_private_data:boolean};
assert.equal(manifest.contains_admin_private_data,true);
for(const file of ['database.dump','data.tgz','storage.tgz']){assert.ok(existsSync(join(backup,file)));assert.equal(await digest(join(backup,file)),manifest.checksums[file]);}
checks.push({name:'comando entregue backup executou pg_dump e arquivou dados/armazenamento com checksums',passed:true,detail:{backup,checksums:manifest.checksums,private:true}});
const database='curriculos_restore_qa_'+new Date().toISOString().replace(/\D/g,'').slice(0,14);
run('bash',['scripts/ops-restore.sh',backup,database],{env});
const restored=JSON.parse(sql(state,snapshotSql,database)) as Record<string,unknown>;assert.deepEqual(restored,before);
checks.push({name:'restauração real em banco descartável preservou default, IDs, textos, fontes, relações e administrador',passed:true,detail:{database,restored}});
const root=join('var/restore',database,'data');
let count=0;for(const expected of expectedFiles){const restoredFile=join(root,expected.path);assert.ok(existsSync(restoredFile),`Arquivo obrigatório não restaurado: ${expected.path}`);assert.equal(await digest(restoredFile),expected.sha256,`Checksum restaurado: ${expected.path}`);count++;}
assert.ok(count>1,'Artefatos de dados restaurados precisam corresponder aos entregues');
checks.push({name:'manifestos, todas partes e cobertura restaurados com hashes streaming iguais',passed:true,detail:{files:count}});
const restoredArtifact=await openAuditArtifact(state.publication,root),restoredInspection=await inspectAuditArtifact(restoredArtifact);assert.ok(restoredInspection.passed,JSON.stringify(restoredInspection.errors));assert.equal(restoredInspection.manifest_sha256,state.artifact.manifest_sha256);assert.equal(restoredInspection.items,state.artifact.items);assert.equal(restoredInspection.relations,state.artifact.relations);assert.equal(restoredInspection.sources,state.artifact.sources);assert.equal(restoredInspection.parts_verified,state.artifact.parts_verified);
checks.push({name:'artefato restaurado foi relido integralmente por parte, com schemas e referências conferidos',passed:true,detail:{format:restoredInspection.format,items:restoredInspection.items,relations:restoredInspection.relations,sources:restoredInspection.sources,parts_verified:restoredInspection.parts_verified,manifest_sha256:restoredInspection.manifest_sha256}});
// Confirm bootstrap/readiness still serves the original clean publication after restoration; restore never touched it.
assert.deepEqual(JSON.parse(sql(state,snapshotSql)),before);await waitReady(state.base_url);
checks.push({name:'restauração não alterou banco/publicação em execução',passed:true});
const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source_tree_sha256:sourceTreeHash(),publication:state.publication,project:state.project,backup,restored_database:database,artifact:state.artifact,checks,passed:true,limitations:['Backup contém dados administrativos privados e fica apenas em var/ ignorado no Git.','Não houve restauração sobre banco principal. Volumes QA preservados para auditoria.']};
mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/backup-restore.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
// Stop only the uniquely named QA project. Keep its volumes and backup for review.
compose(state,['stop']);
}catch(error){const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),checks,passed:false,error:error instanceof Error?error.message:String(error)};mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/backup-restore.json',JSON.stringify(report,null,2)+'\n');console.error(JSON.stringify(report,null,2));process.exitCode=1;}
