/** Verify actual exported image files before permitting recreation of running services. */
import {spawnSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {mkdirSync,writeFileSync} from 'node:fs';
import {sourceTreeHash} from './release-check';
try{process.loadEnvFile('.env');}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}
const imageIndex=process.argv.indexOf('--image');
const image=imageIndex>=0?process.argv[imageIndex+1]:`curriculos-abertos:${process.env.RELEASE_TAG||'local'}`;
const probeIndex=process.argv.indexOf('--probe-name');const configuredProbe=probeIndex>=0?process.argv[probeIndex+1]:undefined;
const qaRunIndex=process.argv.indexOf('--qa-run-id'),qaRunId=qaRunIndex>=0?process.argv[qaRunIndex+1]:undefined;
if(qaRunId!==undefined&&!/^qa-[a-z0-9-]+$/.test(qaRunId))throw new Error('Identidade de execução QA inválida.');
if(configuredProbe!==undefined&&!(qaRunId?/^curriculos-qa-command-[a-f0-9-]{36}$/:/^curriculos-image-verify-[a-f0-9-]{36}$/).test(configuredProbe))throw new Error('Nome de probe de imagem fora do isolamento.');
if(qaRunId&&!configuredProbe)throw new Error('Execução QA exige probe previamente registrado.');
const started_at=new Date().toISOString(),name=configuredProbe??'curriculos-image-verify-'+randomUUID(),probeOwner=randomUUID();
const report:Record<string,unknown>={schema_version:1,started_at,image,network:'none',read_only:true,runtime_secrets_injected:false,probe_name:name,probe_owner:probeOwner,passed:false};
let created=false;
function docker(args:string[],timeout=90000){const r=spawnSync('docker',args,{encoding:'utf8',timeout,maxBuffer:2*1024*1024});if(r.error||r.status!==0)throw new Error((r.stderr||r.error?.message||'Docker verification failed.').slice(0,2000));return r.stdout.trim();}
try{
 if(!image||! /^[A-Za-z0-9][A-Za-z0-9._/:@-]*$/.test(image))throw new Error('Referência de imagem inválida.');
 const expected=sourceTreeHash();report.expected_source_tree_sha256=expected;
 report.image_id=docker(['image','inspect',image,'--format','{{.Id}}']);
 const probe=String.raw`const fs=require('fs'),crypto=require('crypto'),cp=require('child_process');
 const files=['package.json','package-lock.json','.next/BUILD_ID'];const checked=[];
 for(const p of files){const b=fs.readFileSync('/app/'+p);if(!b.length)throw Error('Empty critical image file: '+p);if(p.endsWith('.json'))JSON.parse(b.toString('utf8'));checked.push({path:p,bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')});}
 const fingerprint=cp.execFileSync(process.execPath,['--import','tsx','scripts/release-check.ts','fingerprint'],{cwd:'/app',encoding:'utf8',timeout:60000,maxBuffer:1024*1024}).trim();if(!/^[a-f0-9]{64}$/.test(fingerprint))throw Error('Invalid image fingerprint');const disk=fs.statfsSync('/');console.log(JSON.stringify({critical_files:checked,source_tree_sha256:fingerprint,node:process.version,uid:process.getuid(),filesystem_free_bytes:disk.bavail*disk.bsize}));`;
 created=true;
 const actual=JSON.parse(docker(['run','--rm','--pull=never','--name',name,'--label','org.curriculos-abertos.image-verification='+probeOwner,...(qaRunId?['--label','org.curriculos-abertos.qa-run='+qaRunId]:[]),'--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=67108864','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','1g','--cpus','1','--pids-limit','64','--entrypoint','node',image,'-e',probe]));
 created=false;report.image_files=actual;
 if(actual.uid!==1000)throw new Error('A imagem deve executar como node/UID1000.');
 if(actual.source_tree_sha256!==expected)throw new Error('Fingerprint da imagem difere do repositório atual; congele o código e refaça o build antes de iniciar serviços.');
 report.passed=true;console.log(JSON.stringify({event:'image_verified',image,image_id:report.image_id,source_tree_sha256:expected}));
}catch(error){report.error=error instanceof Error?error.message:String(error);console.error(JSON.stringify({event:'image_verification_failed',image,error:report.error}));process.exitCode=1;}
finally{
 if(created){const inspected=spawnSync('docker',['inspect',name],{encoding:'utf8',timeout:15000,maxBuffer:2*1024*1024});if(inspected.status===0){try{const container=JSON.parse(inspected.stdout)[0];if(container?.Config?.Labels?.['org.curriculos-abertos.image-verification']===probeOwner&&/^[a-f0-9]{64}$/.test(container.Id)){const removed=spawnSync('docker',['rm','-f',container.Id],{encoding:'utf8',timeout:15000,maxBuffer:1024*1024});if(removed.status!==0)report.probe_cleanup_failed=true;}else report.probe_cleanup_refused_foreign_owner=true;}catch{report.probe_cleanup_failed=true;}}else if(!/No such (object|container)/i.test(inspected.stderr))report.probe_cleanup_failed=true;}
 report.completed_at=new Date().toISOString();mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/image-files-verification.json',JSON.stringify(report,null,2)+'\n');
}
