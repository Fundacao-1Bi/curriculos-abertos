// Passwords enter through the terminal or stdin, never command arguments or logs.
export async function readPassword(prompt='Nova senha (mínimo 14 caracteres): '):Promise<string> {
  process.stderr.write(prompt);
  if(!process.stdin.isTTY){let input='';for await(const chunk of process.stdin){input+=chunk.toString();if(input.length>1024)throw new Error('Entrada excessiva.');}return input.trimEnd();}
  process.stdin.setRawMode(true);process.stdin.resume();process.stdin.setEncoding('utf8');
  return new Promise((resolve,reject)=>{
    let value='';
    const done=()=>{process.stdin.setRawMode(false);process.stdin.pause();process.stdin.off('data',onData);process.stderr.write('\n');};
    const onData=(chunk:string)=>{
      for(const c of chunk){
        if(c==='\u0003'){done();reject(new Error('Cancelado.'));return;}
        if(c==='\r'||c==='\n'){done();resolve(value);return;}
        if(c==='\u007f'||c==='\b')value=value.slice(0,-1);
        else if(c>=' '&&value.length<128)value+=c;
      }
    };
    process.stdin.on('data',onData);
  });
}
export function cliArgs(){const args:Record<string,string>={};for(let i=2;i<process.argv.length;i+=2){const key=process.argv[i];if(!key.startsWith('--')||process.argv[i+1]===undefined)throw new Error('Argumentos inválidos.');args[key.slice(2)]=process.argv[i+1];}return args;}
