/** Reproducible fallback when the daemon build endpoint stalls but normal container lifecycle works.
 * No daemon reset, account change, host mount, credential forwarding, or external publication.
 * The same pinned public runtime, dependencies, source and production command as Dockerfile are used.
 */
import { spawn, spawnSync } from 'node:child_process';
import { randomUUID,createHash } from 'node:crypto';
import { createWriteStream, createReadStream, readFileSync, existsSync } from 'node:fs';
import { mkdir,writeFile,rm } from 'node:fs/promises';
import { sourceTreeHash } from './release-check';
import { resolve } from 'node:path';
const runtime=process.env.NODE_IMAGE || 'node:22.23.4-bookworm-slim';
let platform=process.env.BUILD_PLATFORM || '';
const image=`curriculos-abertos:${process.env.RELEASE_TAG || 'local'}`;
const name=`curriculos-build-${randomUUID().slice(0,12)}`;
const toolsImage='curriculos-runtime-tools:node22-pdf-npm11-v3';
const requirementsHash=createHash('sha256').update(readFileSync('pipeline/requirements.txt')).digest('hex');
const started_at=new Date().toISOString();
await mkdir('docs/evidence',{recursive:true});await mkdir('var',{recursive:true});
const output=createWriteStream('docs/evidence/docker-fallback-build.log');
const commands:string[][]=[];
async function run(args:string[],input?:string){
 commands.push(['docker',...args]);
 console.log(JSON.stringify({event:'build_step_started',operation:args[0],step:commands.length}));
 const child=spawn('docker',args,{stdio:['pipe','pipe','pipe'],env:process.env});
 if(input!==undefined)child.stdin.end(input);else child.stdin.end();
 let text='';for(const stream of [child.stdout,child.stderr])stream.on('data',(chunk:Buffer)=>{text+=chunk.toString();output.write(chunk);});
 const timer=setTimeout(()=>child.kill('SIGKILL'),15*60*1000);
 const code=await new Promise<number|null>((resolve,reject)=>{child.on('close',resolve);child.on('error',reject);});clearTimeout(timer);
 if(code!==0)throw new Error(`docker ${args[0]} terminou com código ${code}.`);return text.trim();
}
async function copyContext(paths:string[],snapshot=false):Promise<string> {
 const archivePath=`var/build-context-${randomUUID()}.tar`;
 const checkRoot=`var/build-context-check-${randomUUID()}`;
 const archiveArgs=['--no-xattrs','-cf',archivePath,'--exclude=.env','--exclude=.env.local','--exclude=node_modules','--exclude=.next','--exclude=.git','--exclude=.venv','--exclude=var','--exclude=data/raw','--exclude=data/extracted',...paths.filter(path=>existsSync(path))];
 commands.push(['tar',...archiveArgs],['docker','cp','-',`${name}:/app`]);
 try {
  const archive=spawn('tar',archiveArgs,{stdio:['ignore','ignore','pipe'],env:{...process.env,COPYFILE_DISABLE:'1'}});
  archive.stderr.on('data',(chunk:Buffer)=>output.write(chunk));
  const archiveCode=await new Promise<number|null>((resolve,reject)=>{archive.on('close',resolve);archive.on('error',reject);});
  if(archiveCode!==0)throw new Error('Preparação do contexto imutável falhou.');
  let expected='';
  if(snapshot) {
   await mkdir(checkRoot,{recursive:true});
   // Hash the immutable context with its own fingerprint implementation; no second list of tracked files.
   const extracted=spawnSync('tar',['-xf',archivePath,'-C',checkRoot],{encoding:'utf8'});
   if(extracted.status!==0)throw new Error('Conferência do contexto imutável falhou.');
   const fingerprint=spawnSync(process.execPath,['--import','tsx',resolve(checkRoot,'scripts/release-check.ts'),'fingerprint'],{cwd:resolve(checkRoot),encoding:'utf8'});
   if(fingerprint.status!==0)throw new Error('Fingerprint do contexto imutável não pôde ser calculado.');
   expected=fingerprint.stdout.trim();
  }
  const target=spawn('docker',['cp','-',`${name}:/app`],{stdio:['pipe','pipe','pipe']});
  createReadStream(archivePath).pipe(target.stdin);
  for(const stream of [target.stdout,target.stderr])stream.on('data',(chunk:Buffer)=>output.write(chunk));
  const code=await new Promise<number|null>((resolve,reject)=>{target.on('close',resolve);target.on('error',reject);});
  if(code!==0)throw new Error('Cópia do contexto imutável falhou.');
  return expected;
 } finally {await rm(archivePath,{force:true});await rm(checkRoot,{recursive:true,force:true});}
}
let source_tree_sha256='';
try{
 // inspect must succeed locally. No implicit pulling of another account/image is performed.
 const inspect=JSON.parse(await run(['image','inspect',runtime]));const inspected=inspect[0];
 if(!platform)platform=`linux/${inspected.Architecture}`;
 const cached=spawnSync('docker',['image','inspect',toolsImage],{encoding:'utf8'});
 const cachedInfo=cached.status===0?JSON.parse(cached.stdout)[0]:null;
 const useToolsCache=cachedInfo?.Config?.Labels?.['org.curriculos-abertos.runtime-base']===inspected.Id && cachedInfo?.Config?.Labels?.['org.curriculos-abertos.pipeline-requirements']===requirementsHash;
 const builderBase=useToolsCache?toolsImage:runtime;
 await run(['create','--platform',platform,'--name',name,'--cpus','4','--memory','6g','--entrypoint','sh',builderBase,'-c','trap "exit 0" TERM INT; while :; do sleep 30; done']);
 await run(['start',name]);
 await run(['exec','--user','root',name,'sh','-c','mkdir -p /app /app/var /app/data/raw /app/data/extracted']);
 await copyContext(['package.json','package-lock.json','pipeline/requirements.txt']);
 if(!useToolsCache)await run(['exec','--user','root',name,'sh','-c','apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-venv poppler-utils tesseract-ocr tesseract-ocr-por ca-certificates && rm -rf /var/lib/apt/lists/* && python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /app/pipeline/requirements.txt && npm install --global npm@11.6.2']);
 if(!useToolsCache)await run(['commit','--change',`LABEL org.curriculos-abertos.runtime-base=${inspected.Id}`,'--change',`LABEL org.curriculos-abertos.pipeline-requirements=${requirementsHash}`,name,toolsImage]);
 await run(['exec','--user','root','--workdir','/app',name,'npm','ci']);
 source_tree_sha256=await copyContext(['src','scripts','pipeline','tests','public','docs','data/manifests','data/bundles','data/coverage-manifest.json','package.json','package-lock.json','tsconfig.json','next.config.ts','next-env.d.ts','eslint.config.mjs','playwright.config.ts','Dockerfile','compose.yaml','Makefile','.env.example','.gitignore','.dockerignore','README.md','LICENSE','DATA-RIGHTS.md','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md'],true);
 await run(['exec','--user','root','--workdir','/app','--env','NEXT_TELEMETRY_DISABLED=1',name,'npm','run','build']);
 await run(['exec','--user','root',name,'sh','-c','chown -R node:node /app && rm -rf /root/.npm /root/.cache /tmp/*']);
 const imageHash=await run(['exec','--user','node','--workdir','/app',name,'node','--import','tsx','scripts/release-check.ts','fingerprint']);
 if(imageHash!==source_tree_sha256)throw new Error('Hash do contexto copiado difere do código esperado.');
 const id=await run(['commit','--change','ENTRYPOINT ["docker-entrypoint.sh"]','--change','USER node','--change','WORKDIR /app','--change','ENV NODE_ENV=production','--change','ENV NEXT_TELEMETRY_DISABLED=1','--change','ENV PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','--change','EXPOSE 3000','--change','CMD ["npm","start"]','--change',`LABEL org.curriculos-abertos.source-tree-sha256=${source_tree_sha256}`,name,image]);
 const report={schema_version:1,method:'docker-container-lifecycle-fallback',started_at,completed_at:new Date().toISOString(),runtime,runtime_image_id:inspected.Id,runtime_repo_digests:inspected.RepoDigests,builder_base_image:builderBase,tools_cache_used:useToolsCache,platform,image,image_id:id,source_tree_sha256,host_source_tree_after_build:sourceTreeHash(),matches_current_source:sourceTreeHash()===source_tree_sha256,context_exclusions:['.env','.env.local','.git','node_modules','.next','.venv','var','data/raw','data/extracted'],commands,passed:true,limitation:'Daemon build/pull endpoints stalled in this environment. Production image was built using normal isolated create/cp/exec/commit operations; Dockerfile remains the default distribution recipe. No remote deployment.'};
 await writeFile('docs/evidence/docker-build.json',JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({event:'production_image_built',image,image_id:id,source_tree_sha256,method:report.method}));
}catch(error){await writeFile('docs/evidence/docker-build.json',JSON.stringify({schema_version:1,started_at,completed_at:new Date().toISOString(),runtime,platform,image,commands,source_tree_sha256,passed:false,error:error instanceof Error?error.message:String(error)},null,2)+'\n');throw error;}
finally{try{await run(['rm','-f',name]);}catch{/* Only the uniquely named build container is targeted. */}output.end();}
