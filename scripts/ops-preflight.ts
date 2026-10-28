/** Host-side installation guard. No builds, source downloads, DB access or paid services. */
import {statfsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
try{process.loadEnvFile('.env');}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;}
const minimum=Number(process.env.BUILD_MIN_FREE_BYTES || 15*1024**3),diskOnly=process.argv.includes('--disk-only');
const checks:{name:string;passed:boolean;detail?:unknown}[]=[];
const check=(name:string,passed:boolean,detail?:unknown)=>{checks.push({name,passed,...(detail===undefined?{}:{detail})});if(!passed)throw new Error(name);};
function docker(args:string[],timeout=15000){return spawnSync('docker',args,{encoding:'utf8',timeout,maxBuffer:1024*1024});}
try{
 check('Limite de espaço válido',Number.isSafeInteger(minimum)&&minimum>0);
 const stats=statfsSync(process.cwd()),available=stats.bavail*stats.bsize;
 check('Espaço livre para o pico de build e uma reserva',available>=minimum,{available_bytes:available,minimum_bytes:minimum,available_gib:Number((available/1024**3).toFixed(2))});
 if(!diskOnly){
  const major=Number(process.versions.node.split('.')[0]);check('Node compatível com package.json',major>=22&&major<26,{version:process.version});
  check('Configuração local obrigatória presente',Boolean(process.env.POSTGRES_PASSWORD)&&String(process.env.BETTER_AUTH_SECRET || '').length>=32);
  const publicUrl=new URL(process.env.PUBLIC_URL || 'http://localhost:3000');check('URL pública HTTP(S) sem credenciais embutidas',['http:','https:'].includes(publicUrl.protocol)&&!publicUrl.username&&!publicUrl.password);
  const engine=docker(['version','--format','{{.Server.Version}}']);check('Docker Engine acessível',engine.status===0,{version:engine.status===0?engine.stdout.trim():null});
  const compose=docker(['compose','version','--short']);check('Docker Compose v2 disponível',compose.status===0&&Number(compose.stdout.trim().replace(/^v/,'').split('.')[0])>=2);
  const image=process.env.NODE_IMAGE || 'node:22.23.4-bookworm-slim';check('Referência de imagem sem credenciais embutidas',/^[A-Za-z0-9][A-Za-z0-9._/:@-]*$/.test(image)&&(!image.includes('@')||image.includes('@sha256:')));
  const local=docker(['image','inspect',image,'--format','{{.Id}}']);
  if(local.status===0){
   const name='curriculos-preflight-'+randomUUID();let probe;
   try{probe=docker(['run','--rm','--pull=never','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','96m','--cpus','0.25','--pids-limit','32','--user','node','--label','org.curriculos-abertos.preflight=true','--name',name,image,'node','-e',"const s=require('fs').statfsSync('/');console.log(JSON.stringify({available_bytes:s.bavail*s.bsize,uid:process.getuid()}))"],20000);}
   finally{if(!probe||probe.status!==0)docker(['rm','-f',name]);}
   check('Leitura real do armazenamento Docker',probe?.status===0);
   const space=JSON.parse(probe!.stdout);check('Espaço livre no filesystem do Docker para o build',Number.isSafeInteger(space.available_bytes)&&space.available_bytes>=minimum,{available_bytes:space.available_bytes,minimum_bytes:minimum});
  }else{
   check('Content store Docker legível ou imagem ainda não adquirida',/No such image|does not exist/i.test(local.stderr));
   checks.push({name:'Espaço interno Docker ainda não verificável sem a imagem base local',passed:true,detail:'Nenhum pull foi iniciado pelo preflight. A primeira aquisição/build ainda pode falhar se o disco virtual do Docker estiver cheio.'});
  }
 }
 console.log(JSON.stringify({event:'ops_preflight_passed',at:new Date().toISOString(),disk_only:diskOnly,checks}));
}catch(error){console.error(JSON.stringify({event:'ops_preflight_failed',at:new Date().toISOString(),disk_only:diskOnly,checks,error:error instanceof Error?error.message:'Pré-requisito não atendido.',action:'Nenhum build foi iniciado. Libere espaço próprio ou corrija o daemon/configuração antes de continuar.'}));process.exitCode=1;}
