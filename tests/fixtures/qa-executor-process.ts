/** Tiny real-process fixture. Never connects to Docker, PostgreSQL or HTTP. */
import {writeFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
import {QaExecutor,assertQaChildContext} from '../../scripts/qa-executor';

const [root,mode]=process.argv.slice(2);
if(!root||!mode)throw new Error('Fixture root/mode required');
if(mode==='child'){
 try{assertQaChildContext();console.log(JSON.stringify({event:'child-accepted'}));}
 catch(error){console.error(error instanceof Error?error.message:String(error));process.exitCode=2;}
}else{
 const executor=new QaExecutor({root,probes:{
  snapshot:()=>({host_free_bytes:100*1024**3,docker_free_bytes:100*1024**3,projects:[]}),
  inventory:()=>({fixture:true}),cleanupGuards:()=>{},
 }});
 try{
  await executor.run({kind:mode==='backup'?'recovery':'unit-process',purpose:'Isolated real-process lifecycle fixture',requiresDocker:false},async qa=>{
   qa.reserve({required_free_bytes:1024**2,reserve_bytes:256*1024});
   const path=join(executor.root,'var',...(mode==='backup'?['backups']:[]),'fixture-'+process.pid+'.txt');
   qa.registerResource({kind:mode==='backup'?'backup':'file',id:path,path,owned:true,disposition:'retain'});
   mkdirSync(join(root,'var',...(mode==='backup'?['backups']:[])),{recursive:true});writeFileSync(path,'retained process fixture\n');qa.markResource(path,'created');
   console.log(JSON.stringify({event:'acquired',pid:process.pid,path}));
   if(mode==='hold-child'){
    const ownedChild=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'ignore'});
    qa.trackChild(ownedChild);console.log(JSON.stringify({event:'tracked-child',pid:ownedChild.pid}));
   }
   if(mode==='hold'||mode==='hold-child')await new Promise<void>(resolve=>{
    const keepAlive=setInterval(()=>{},1000);
    process.once('SIGUSR2',()=>{clearInterval(keepAlive);resolve();});
   });
   if(mode==='exit-code')process.exitCode=9;
  });
 }catch(error){console.error(error instanceof Error?error.message:String(error));process.exitCode=2;}
}
