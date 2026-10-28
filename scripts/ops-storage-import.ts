/** Preserve completed host exports/checkpoints when moving this project to its Compose volume. */
import {spawn} from 'node:child_process';
import {randomUUID,createHash} from 'node:crypto';
import {mkdir,readdir,lstat,copyFile,writeFile} from 'node:fs/promises';
import {existsSync,createReadStream,constants} from 'node:fs';
import {join,resolve,relative} from 'node:path';
import {pool} from '../src/db/client';
const volume='curriculos-abertos_storage';
const image='curriculos-abertos:local';
const token=randomUUID();
const container='curriculos-storage-import-'+token.slice(0,8);
const staging=resolve('var/storage-import-'+token);
const started_at=new Date().toISOString();
const manifest:{path:string;bytes:number;sha256:string}[]=[];
async function sha(path:string){const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);return hash.digest('hex');}
async function run(args:string[],input?:NodeJS.ReadableStream){
 const child=spawn('docker',args,{stdio:['pipe','pipe','pipe']});let out='',err='';child.stdout.on('data',(b:Buffer)=>{out+=b.toString();});child.stderr.on('data',(b:Buffer)=>{err=(err+b.toString()).slice(-3000);});
 if(input)input.pipe(child.stdin);else child.stdin.end();
 const code=await new Promise<number|null>((done,reject)=>{child.once('close',done);child.once('error',reject);});if(code!==0)throw new Error(`docker ${args[0]} falhou: ${err}`);return out.trim();
}
async function copy(relativePath:string){
 const source=resolve('var',relativePath),stat=await lstat(source);if(stat.isSymbolicLink())throw new Error('Symlink não permitido no estado operacional.');
 if(stat.isDirectory()){await mkdir(join(staging,relativePath),{recursive:true,mode:0o700});for(const name of await readdir(source)){if(name.startsWith('.')||name.includes('.tmp-')||name.endsWith('.tmp'))continue;await copy(join(relativePath,name));}}
 else if(stat.isFile()){const destination=join(staging,relativePath);await mkdir(resolve(destination,'..'),{recursive:true,mode:0o700});await copyFile(source,destination,constants.COPYFILE_EXCL);const written=await lstat(destination);manifest.push({path:relative(staging,destination).replaceAll('\\','/'),bytes:written.size,sha256:await sha(destination)});}
 else throw new Error('Tipo de arquivo não permitido no estado operacional.');
}
try{
 await mkdir(staging,{recursive:true,mode:0o700});for(const dir of ['exports','jobs','source-monitor'])if(existsSync(join('var',dir)))await copy(dir);
 const exports=(await pool.query("SELECT id,result FROM jobs WHERE type='export' AND status='succeeded' ORDER BY id")).rows;
 for(const job of exports){const key=job.result?.storage_key;if(typeof key!=='string'||!/^exports\/[a-f0-9-]{36}(?:\/[0-9]{1,4}-[a-f0-9-]{36})?\.(?:json|csv)$/.test(key))throw new Error('Chave de exportação persistida inválida.');const file=manifest.find(row=>row.path===key);if(!file||file.sha256!==job.result.sha256||file.bytes!==Number(job.result.size))throw new Error(`Exportação concluída ${job.id} não confere com o arquivo do host.`);}
 await writeFile(join(staging,'storage-import-manifest.json'),JSON.stringify({created_at:new Date().toISOString(),files:manifest},null,2)+'\n',{mode:0o600});
 const found=await run(['volume','ls','--filter',`name=^${volume}$`,'--format','{{.Name}}']);
 if(found)throw new Error('Volume de destino já existe; preservar e inspecionar antes de repetir importação.');
 await run(['volume','create','--label','com.docker.compose.project=curriculos-abertos','--label','com.docker.compose.volume=storage',volume]);
 await run(['create','--name',container,'--network','none','--user','root','--mount',`type=volume,src=${volume},dst=/app/var`,'--entrypoint','sh',image,'-c','trap "exit 0" TERM INT; while :; do sleep 30; done']);
 await run(['start',container]);
 const archive=spawn('tar',['--no-xattrs','-cf','-','-C',staging,'.'],{stdio:['ignore','pipe','pipe'],env:{...process.env,COPYFILE_DISABLE:'1'}});
 const extract=run(['exec','-i',container,'tar','-xf','-','-C','/app/var'],archive.stdout);
 const archiveCode=await new Promise<number|null>((done,reject)=>{archive.once('close',done);archive.once('error',reject);});await extract;if(archiveCode!==0)throw new Error('TAR do estado operacional falhou.');
 await run(['exec',container,'chown','-R','node:node','/app/var']);
 const verification=JSON.parse(await run(['exec','--user','node',container,'node','--input-type=module','-e',`import{readFileSync,createReadStream}from'node:fs';import{createHash}from'node:crypto';const m=JSON.parse(readFileSync('/app/var/storage-import-manifest.json','utf8'));let bytes=0;for(const file of m.files){const h=createHash('sha256');for await(const chunk of createReadStream('/app/var/'+file.path))h.update(chunk);if(h.digest('hex')!==file.sha256)throw Error('Checksum divergente.');bytes+=file.bytes;}console.log(JSON.stringify({files:m.files.length,bytes,uid:process.getuid()}));`]));
 const report={schema_version:1,started_at,completed_at:new Date().toISOString(),volume,source:'host var/exports + var/jobs + var/source-monitor',staging_private:staging,completed_exports_verified:exports.length,verification,manifest_sha256:await sha(join(staging,'storage-import-manifest.json')),passed:true,container_started_as_application:false,notes:'Somente volume dedicado criado; arquivos verificados por SHA-256 e propriedade node1000; nenhum app/worker iniciado.'};
 await writeFile('docs/evidence/runtime-storage-import.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}catch(error){await writeFile('docs/evidence/runtime-storage-import.json',JSON.stringify({schema_version:1,started_at,completed_at:new Date().toISOString(),passed:false,error:error instanceof Error?error.message:String(error)},null,2)+'\n');throw error;}
finally{await run(['rm','-f',container]).catch(()=>{});await pool.end();}
