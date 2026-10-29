import {spawn} from 'node:child_process';
import {randomBytes} from 'node:crypto';
import pg from 'pg';
const suffix=randomBytes(6).toString('hex'),container='ca-domain-provenance-'+suffix,database='curriculum_test_'+suffix,password=randomBytes(32).toString('hex');
const files=['tests/domain.ingestion-provenance.test.ts','tests/domain.ingestion-update.test.ts'];let started=false;
async function run(command:string,args:string[],env:NodeJS.ProcessEnv=process.env,capture=false){return new Promise<string>((yes,no)=>{const child=spawn(command,args,{env,stdio:['ignore',capture?'pipe':'inherit',capture?'pipe':'inherit']});let out='';child.stdout?.on('data',c=>out+=c.toString());child.stderr?.on('data',c=>out+=c.toString());child.on('error',no);child.on('close',code=>code===0?yes(out):no(Error(command+' failed '+code+(capture?': '+out.slice(-1000):''))));});}
try{
 await run('docker',['run','--pull=never','-d','--rm','--name',container,'-p','127.0.0.1::5432','-e','POSTGRES_USER=curriculum_test','-e','POSTGRES_DB='+database,'-e','POSTGRES_PASSWORD','postgres:17.11-bookworm'],{...process.env,POSTGRES_PASSWORD:password},true);started=true;
 const port=(await run('docker',['port',container,'5432/tcp'],process.env,true)).match(/127\.0\.0\.1:(\d+)/)?.[1];if(!port)throw Error('Own test port unavailable');const url='postgresql://curriculum_test:'+password+'@127.0.0.1:'+port+'/'+database;
 let ready=false;for(let i=0;i<40;i++){const client=new pg.Client({connectionString:url,connectionTimeoutMillis:500});try{await client.connect();await client.query('SELECT 1');ready=true;break;}catch{await new Promise(r=>setTimeout(r,250));}finally{await client.end().catch(()=>{});}}if(!ready)throw Error('Own disposable PostgreSQL unavailable');
 console.log(JSON.stringify({event:'owned_test_database_ready',container,database,port,files,scope:'Small synthetic SQL fixtures only; no QA/main access'}));
 await run(process.execPath,['--import','tsx','--test','--test-concurrency=1',...files],{...process.env,DATABASE_URL:url,DOMAIN_INTEGRATION_TEST:'1'});
}catch(error){console.error((error as Error).message);process.exitCode=1;}finally{if(started){await run('docker',['stop',container],process.env,true);console.log(JSON.stringify({event:'owned_test_container_removed',container,automatic_anonymous_volume_cleanup:true}));}}
