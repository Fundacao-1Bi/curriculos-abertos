/** A child keeps checking its authenticated owner while asynchronous SQL is in flight.
 * Failure contains only the work selected by the caller; this helper never signals
 * processes, deletes files or chooses a database itself.
 */
export function watchQaParent(options:{assertParent:()=>void;containOwnedWork:()=>Promise<void>;onFailure:(cause:unknown)=>void;intervalMs?:number}){
 let stopped=false,failed=false,pending:Promise<void>|undefined;
 const interval=options.intervalMs??500;
 if(!Number.isSafeInteger(interval)||interval<1)throw Error('Invalid parent guard interval');
 const check=()=>{
  if(stopped||failed)return;
  try{options.assertParent();}
  catch(cause){
   failed=true;clearInterval(timer);
   pending=(async()=>{try{await options.containOwnedWork();}catch{/* Failure still terminates the child; owned diagnostics remain retained. */}finally{options.onFailure(cause);}})();
  }
 };
 const timer=setInterval(check,interval);timer.unref();
 return{check,failed:()=>failed,stop:async()=>{stopped=true;clearInterval(timer);await pending;}};
}
