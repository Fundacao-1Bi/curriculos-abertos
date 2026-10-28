/** Promote the verified logical PostgreSQL17.11 restore; never reuse oldlibc2.41 data in Bookworm. */
import {spawn} from 'node:child_process';
import {readFile,writeFile,rename} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import pg from 'pg';
if(!process.argv.includes('--promote'))throw new Error('Use --promote para a migração explícita do banco dedicado local.');
const state=JSON.parse(await readFile('var/pg1711-upgrade-state.json','utf8'));
if(state.project!=='curriculos-abertos'||state.cutover_executed||!state.restoration_verified||!state.source_volume?.startsWith('curriculos-abertos_')||!state.target_volume?.startsWith('curriculos-abertos_database_pg1711_'))throw new Error('Estado de restauração não apto a promoção.');
const secret=process.env.POSTGRES_PASSWORD;if(!secret||!process.env.DATABASE_URL)throw new Error('Carregue .env seguro.');
const oldEnv=await readFile('.env','utf8');
const envBackup=state.backup_dir+'/.env.before-cutover';
await writeFile(envBackup,oldEnv,{mode:0o600,flag:'wx'});
const beforeConfig={POSTGRES_IMAGE:process.env.POSTGRES_IMAGE,DATABASE_VOLUME:process.env.DATABASE_VOLUME,DATABASE_VOLUME_EXTERNAL:process.env.DATABASE_VOLUME_EXTERNAL};
const started_at=new Date().toISOString();
const operations:{operation:string;completed_at:string}[]=[];
async function command(args:string[],timeout=180000){
 const child=spawn('docker',args,{stdio:['ignore','pipe','pipe'],env:process.env});let out='',err='';child.stdout.on('data',(chunk:Buffer)=>{out+=chunk.toString();});child.stderr.on('data',(chunk:Buffer)=>{err=(err+chunk.toString()).slice(-4000);});
 const timer=setTimeout(()=>child.kill('SIGKILL'),timeout);const code=await new Promise<number|null>((done,reject)=>{child.once('close',done);child.once('error',reject);});clearTimeout(timer);
 if(code!==0)throw new Error(`docker ${args[0]} falhou (${code}): ${err.replaceAll(secret!,'[redacted]')}`);operations.push({operation:args.slice(0,3).join(' '),completed_at:new Date().toISOString()});return out.trim();
}
async function digest(path:string){const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);return hash.digest('hex');}
async function snapshot(client:pg.Client){
 const tables=(await client.query<{tablename:string}>("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename COLLATE \"C\"")).rows;
 const result:Record<string,{count:string;row_digest_md5:string|null}>={};
 for(const {tablename} of tables){
  if(['worker_heartbeats','request_metrics'].includes(tablename))continue;
  const quoted='"'+tablename.replaceAll('"','""')+'"';
  const row=(await client.query(`SELECT count(*)::text AS count,md5(string_agg(md5(row_to_json(t)::text),',' ORDER BY md5(row_to_json(t)::text) COLLATE "C")) AS digest FROM ${quoted} t`)).rows[0];
  result[tablename]={count:row.count,row_digest_md5:row.digest};
 }return result;
}
let changed=false,complete=false;
const source=new pg.Client({connectionString:process.env.DATABASE_URL,statement_timeout:180000});
try{
 if(await digest(state.backup_dir+'/database.dump')!==state.backup_dump_sha256)throw new Error('Checksum do backup privado diverge.');
 await source.connect();await source.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');await source.query("SET LOCAL TIME ZONE 'UTC'");
 if(Number((await source.query("SELECT count(*)::int n FROM jobs WHERE status='running'")).rows[0].n)>0)throw new Error('Existem jobs em execução; pause os escritores antes do cutover.');
 const now=await snapshot(source);await source.query('COMMIT');
 const expected=Object.fromEntries(Object.entries(state.snapshot).filter(([table])=>!['worker_heartbeats','request_metrics'].includes(table)));
 if(JSON.stringify(now)!==JSON.stringify(expected))throw new Error('Estado durável mudou após o backup. Refazer backup/restore antes de promover.');
 await source.end();
 // Only the isolated restore container and this dedicated Compose database are stopped.
 await command(['stop',state.target_container]);
 await command(['rm',state.target_container]);
 await command(['compose','stop','db']);
 const values={POSTGRES_IMAGE:state.target_image,DATABASE_VOLUME:state.target_volume,DATABASE_VOLUME_EXTERNAL:'true'};
 const lines=oldEnv.split('\n');for(const[key,value]of Object.entries(values)){const n=lines.findIndex(line=>line.startsWith(key+'='));if(n<0)lines.push(key+'='+value);else lines[n]=key+'='+value;process.env[key]=value;}
 const temporary='.env.tmp-'+randomUUID();await writeFile(temporary,lines.join('\n').replace(/\n*$/,'\n'),{mode:0o600,flag:'wx'});await rename(temporary,'.env');changed=true;
 await command(['compose','up','-d','--no-deps','--wait','db']);
 const current=new pg.Client({connectionString:process.env.DATABASE_URL,statement_timeout:180000});await current.connect();
 try{
  await current.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');await current.query("SET LOCAL TIME ZONE 'UTC'");
  const data=await snapshot(current);if(JSON.stringify(data)!==JSON.stringify(expected))throw new Error('Estado durável divergente após promoção.');
  const collation=(await current.query("SELECT current_setting('server_version') AS server_version,datcollversion,pg_database_collation_actual_version(oid) AS actual_version FROM pg_database WHERE datname=current_database()" )).rows[0];
  if(!String(collation.server_version).startsWith('17.11')||collation.datcollversion!==collation.actual_version)throw new Error('Versão/collation não conferem após promoção.');
  const invalid=(await current.query('SELECT count(*)::int n FROM pg_index WHERE NOT indisvalid OR NOT indisready')).rows[0].n;if(invalid!==0)throw new Error('Índices inválidos após promoção.');
  const publication=(await current.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0]?.publication_id;
  await current.query('COMMIT');
  const oldVolume=JSON.parse(await command(['volume','inspect',state.source_volume]))[0];if(oldVolume.Name!==state.source_volume)throw new Error('Volume anterior de rollback não encontrado.');
  const report={schema_version:1,started_at,completed_at:new Date().toISOString(),passed:true,source_volume:state.source_volume,target_volume:state.target_volume,old_volume_preserved:true,backup_dir:state.backup_dir,backup_dump_sha256:state.backup_dump_sha256,configuration_rollback_file:envBackup,source_collation:state.source_collation,target_collation:collation,collation_method:state.collation_method,durable_tables_verified:Object.keys(data).length,snapshot:data,publication,invalid_indexes:invalid,operations,remote_deployment:false};
  await writeFile('docs/evidence/postgres-upgrade-cutover.json',JSON.stringify(report,null,2)+'\n');state.cutover_executed=true;state.cutover_report='docs/evidence/postgres-upgrade-cutover.json';await writeFile('var/pg1711-upgrade-state.json',JSON.stringify(state,null,2)+'\n',{mode:0o600});complete=true;
  console.log(JSON.stringify({event:'postgres1711_cutover_verified',publication,old_volume_preserved:true,collation,report:'docs/evidence/postgres-upgrade-cutover.json'}));
 }finally{await current.end();}
}catch(error){
 if(changed&&!complete){await writeFile('.env',oldEnv,{mode:0o600});for(const[key,value]of Object.entries(beforeConfig)){if(value===undefined)delete process.env[key];else process.env[key]=value;}await command(['compose','up','-d','--no-deps','--wait','db']).catch(()=>{});}
 await writeFile('docs/evidence/postgres-upgrade-cutover.json',JSON.stringify({schema_version:1,started_at,completed_at:new Date().toISOString(),passed:false,rolled_back_configuration:changed&&!complete,error:error instanceof Error?error.message.replaceAll(secret,'[redacted]'):String(error),operations},null,2)+'\n');throw error;
}finally{await source.end().catch(()=>{});}
