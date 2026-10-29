/** Development/test convenience; never logs credentials, never used in public HTTP. */
import {spawn} from 'node:child_process';
const args=process.argv.slice(2).filter((v,i)=>!(i===0&&v==='--'));
if(!args.length)throw new Error('Comando obrigatório');
if(!process.env.DATABASE_URL) {
 const user=encodeURIComponent(process.env.POSTGRES_USER??'curriculos');
 const pass=process.env.POSTGRES_PASSWORD;
 if(!pass)throw new Error('Execute make configure e carregue .env com node --env-file=.env');
 process.env.DATABASE_URL=`postgresql://${user}:${encodeURIComponent(pass)}@127.0.0.1:${process.env.DATABASE_PORT??'55437'}/${process.env.POSTGRES_DB??'curriculos'}`;
}
const child=spawn(args[0],args.slice(1),{env:process.env,stdio:'inherit'});
for(const signal of ['SIGINT','SIGTERM'] as const)process.on(signal,()=>child.kill(signal));
child.on('error',error=>{console.error(error.message);process.exitCode=1;});
child.on('exit',(code)=>{process.exitCode=code??1;});
