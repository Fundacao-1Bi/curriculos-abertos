/** Logical PostgreSQL minor/OS migration for this project's dedicated local database.
 * Preserves source volume; verifies restoration and libc collation before any cutover.
 */
import {spawn} from 'node:child_process';
import {randomUUID,createHash} from 'node:crypto';
import {mkdir,writeFile,chmod} from 'node:fs/promises';
import {createReadStream,createWriteStream} from 'node:fs';
import {resolve} from 'node:path';
import pg from 'pg';
const prefix='curriculos-abertos';
const stamp=new Date().toISOString().replace(/\D/g,'').slice(0,14)+'-'+randomUUID().slice(0,8);
const project=process.env.COMPOSE_PROJECT_NAME || prefix;
if(project!==prefix)throw new Error('Esta migração local é restrita ao projeto dedicado curriculos-abertos.');
const database=process.env.POSTGRES_DB || 'curriculos';
const user=process.env.POSTGRES_USER || 'curriculos';
const secret=process.env.POSTGRES_PASSWORD;
if(!secret || !process.env.DATABASE_URL)throw new Error('Carregue .env seguro antes de executar.');
if(!/^[a-zA-Z0-9_]+$/.test(database)||!/^[a-zA-Z0-9_]+$/.test(user))throw new Error('Identificador PostgreSQL não suportado.');
const targetImage='postgres:17.11-bookworm';
const backupDir=resolve(`var/backups/pg1711-${stamp}`);
const statePath='var/pg1711-upgrade-state.json';
const publicReport='docs/evidence/postgres-upgrade-prepared.json';
const identity=(value:string)=>'"'+value.replaceAll('"','""')+'"';
async function command(args:string[],options:{input?:string;inputFile?:string;outputFile?:string;timeout?:number}={}){
 const child=spawn('docker',args,{stdio:['pipe','pipe','pipe'],env:process.env});
 let stdout='',stderr='';const sink=options.outputFile?createWriteStream(options.outputFile,{mode:0o600}):null;
 if(sink)child.stdout.pipe(sink);else child.stdout.on('data',(chunk:Buffer)=>{stdout+=chunk.toString();if(stdout.length>8*1024*1024)child.kill('SIGKILL');});
 child.stderr.on('data',(chunk:Buffer)=>{stderr=(stderr+chunk.toString()).slice(-5000);});
 if(options.inputFile)createReadStream(options.inputFile).pipe(child.stdin);else child.stdin.end(options.input);
 const timer=setTimeout(()=>child.kill('SIGKILL'),options.timeout || 300_000);
 const code=await new Promise<number|null>((done,reject)=>{child.once('close',done);child.once('error',reject);});clearTimeout(timer);
 if(sink)await new Promise<void>((done,reject)=>{if(sink.writableFinished)done();else {sink.once('finish',done);sink.once('error',reject);}});
 if(code!==0)throw new Error(`docker ${args[0]} falhou (exit ${code}): ${stderr.replaceAll(secret!,'[redacted]').slice(-3000)}`);
 return stdout.trim();
}
async function hashFile(path:string){const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);return hash.digest('hex');}
async function snapshot(client:pg.Client){
 const tables=(await client.query<{tablename:string}>("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename COLLATE \"C\"")).rows;
 const result:Record<string,{count:string;row_digest_md5:string|null}>={};
 for(const {tablename} of tables){
  const rows=await client.query<{count:string;digest:string|null}>(`SELECT count(*)::text AS count,md5(string_agg(md5(row_to_json(t)::text),',' ORDER BY md5(row_to_json(t)::text) COLLATE "C")) AS digest FROM ${identity(tablename)} t`);
  result[tablename]={count:rows.rows[0].count,row_digest_md5:rows.rows[0].digest};
 }
 return result;
}
async function collation(client:pg.Client){return(await client.query("SELECT current_setting('server_version') AS server_version,current_setting('server_encoding') AS encoding,current_setting('TimeZone') AS timezone,datname,datcollate,datctype,datcollversion,pg_database_collation_actual_version(oid) AS actual_version FROM pg_database WHERE datname=current_database()" )).rows[0];}
const started_at=new Date().toISOString();
await mkdir(backupDir,{recursive:true,mode:0o700});await chmod(backupDir,0o700);await mkdir('docs/evidence',{recursive:true});
const source=new pg.Client({connectionString:process.env.DATABASE_URL,statement_timeout:180000});
let target:pg.Client|undefined;
try{
 const sourceContainer=await command(['compose','ps','-q','db']);if(!/^[a-f0-9]{12,64}$/.test(sourceContainer))throw new Error('Container dedicado não encontrado.');
 const inspected=JSON.parse(await command(['inspect',sourceContainer]))[0];
 if(inspected.Config.Labels['com.docker.compose.project']!==project || inspected.Config.Labels['com.docker.compose.service']!=='db')throw new Error('Container fora do projeto dedicado.');
 const binding=inspected.HostConfig.PortBindings?.['5432/tcp']?.[0];
 if(binding?.HostPort!=='55437'||binding?.HostIp!=='127.0.0.1')throw new Error('Porta de origem não é a porta dedicada 55437.');
 const sourceVolume=inspected.Mounts.find((m:{Type:string;Destination:string})=>m.Type==='volume'&&m.Destination==='/var/lib/postgresql/data')?.Name;
 if(!sourceVolume?.startsWith(prefix+'_'))throw new Error('Volume de origem não é dedicado ao projeto.');
 const targetInfo=JSON.parse(await command(['image','inspect',targetImage]))[0];
 if(targetInfo.Architecture!=='arm64')throw new Error('Imagem PostgreSQL alvo inesperada.');
 await source.connect();await source.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');await source.query("SET LOCAL statement_timeout='180s'");await source.query("SET LOCAL TIME ZONE 'UTC'");
 const exported=(await source.query('SELECT pg_export_snapshot() AS snapshot')).rows[0].snapshot as string;
 const sourceCollation=await collation(source);
 console.log(JSON.stringify({event:'consistent_database_backup_started',source_version:sourceCollation.server_version,source_volume:sourceVolume,backup_dir:backupDir}));
 const databaseDump=resolve(backupDir,'database.dump');
 await command(['exec',sourceContainer,'pg_dump','-U',user,'-d',database,'-Fc','--snapshot',exported],{outputFile:databaseDump,timeout:600_000});
 const before=await snapshot(source);await source.query('COMMIT');
 const dumpSha=await hashFile(databaseDump);
 const targetVolume=`${prefix}_database_pg1711_${stamp}`;
 const targetContainer=`${prefix}-pg1711-restore-${stamp}`;
 const envPath=resolve(backupDir,'restore.env');
 await writeFile(envPath,`POSTGRES_USER=${user}\nPOSTGRES_DB=${database}\nPOSTGRES_PASSWORD=${secret}\nPOSTGRES_INITDB_ARGS=--locale=en_US.utf8 --encoding=UTF8\n`,{mode:0o600,flag:'wx'});
 await command(['volume','create',targetVolume]);
 await command(['run','-d','--name',targetContainer,'--env-file',envPath,'--mount',`type=volume,src=${targetVolume},dst=/var/lib/postgresql/data`,'--publish','127.0.0.1:55439:5432',targetImage]);
 let ready=false;for(let n=0;n<60;n++){try{await command(['exec',targetContainer,'pg_isready','-U',user,'-d',database],{timeout:5000});ready=true;break;}catch{await new Promise(r=>setTimeout(r,1000));}}
 if(!ready)throw new Error('PostgreSQL isolado não ficou pronto.');
 console.log(JSON.stringify({event:'logical_restore_started',target_version:'17.11',target_volume:targetVolume}));
 await command(['exec','-i',targetContainer,'pg_restore','-U',user,'-d',database,'--exit-on-error'],{inputFile:databaseDump,timeout:600000});
 target=new pg.Client({connectionString:`postgresql://${encodeURIComponent(user)}:${encodeURIComponent(secret)}@127.0.0.1:55439/${database}`,statement_timeout:180000});
 await target.connect();await target.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');await target.query("SET LOCAL statement_timeout='180s'");await target.query("SET LOCAL TIME ZONE 'UTC'");
 const restored=await snapshot(target);const targetCollation=await collation(target);await target.query('COMMIT');
 if(JSON.stringify(before)!==JSON.stringify(restored))throw new Error('Contagens/digests das tabelas restauradas divergem do snapshot.');
 if(targetCollation.datcollversion!==targetCollation.actual_version)throw new Error('Versão da collation do banco restaurado diverge da libc atual.');
 if(!String(targetCollation.server_version).startsWith('17.11'))throw new Error('Versão PostgreSQL restaurada incorreta.');
 const state={schema_version:1,started_at,completed_at:new Date().toISOString(),project,source_container:sourceContainer,source_volume:sourceVolume,source_image:inspected.Image,target_image:targetImage,target_image_id:targetInfo.Id,target_container:targetContainer,target_volume:targetVolume,backup_dir:backupDir,backup_dump_sha256:dumpSha,database,user,source_collation:sourceCollation,target_collation:targetCollation,snapshot:before,restored_snapshot:restored,restoration_verified:true,cutover_executed:false,collation_method:'Logical restore into fresh database and newly built indexes under libc2.36; oldlibc2.41 data directory was not mounted by the new runtime.'};
 await writeFile(statePath,JSON.stringify(state,null,2)+'\n',{mode:0o600});await writeFile(resolve(backupDir,'manifest.json'),JSON.stringify({contains_admin_private_data:true,database_dump_sha256:dumpSha,source_volume:sourceVolume,target_volume:targetVolume,source_collation:sourceCollation,target_collation:targetCollation,snapshot:before},null,2)+'\n',{mode:0o600});
 await writeFile(publicReport,JSON.stringify(state,null,2)+'\n');
 console.log(JSON.stringify({event:'logical_restore_verified',source_volume:sourceVolume,target_volume:targetVolume,tables:Object.keys(restored).length,database_dump_sha256:dumpSha,source_collation_version:sourceCollation.datcollversion,target_collation_version:targetCollation.datcollversion,cutover_executed:false,report:publicReport}));
}catch(error){await writeFile(publicReport,JSON.stringify({schema_version:1,started_at,completed_at:new Date().toISOString(),passed:false,error:error instanceof Error?error.message.replaceAll(secret,'[redacted]'):String(error)},null,2)+'\n');throw error;}
finally{await source.end().catch(()=>{});await target?.end().catch(()=>{});}
