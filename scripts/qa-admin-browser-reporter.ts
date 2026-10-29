import type { Reporter, TestCase, TestResult, FullResult } from '@playwright/test/reporter';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
export function redactAdminBrowser(value:string):string{
 let safe=value;
 for(const secret of [process.env.QA_ADMIN_PASSWORD,process.env.QA_ADMIN_WRONG_PASSWORD])if(secret)safe=safe.split(secret).join('[REDACTED]');
 return safe.replace(/(postgres(?:ql)?:\/\/)[^\s/@]+(?::[^\s/@]+)?@/gi,'$1[REDACTED]@').replace(/((?:__Secure-)?better-auth[.\w-]*\s*=\s*)[^;\s"}]+/gi,'$1[REDACTED]');
}
/** No built-in reporter receives raw auth call logs or writes traces/HAR/video. */
export default class AdminBrowserReporter implements Reporter {
 private results:Record<string,unknown>[]=[];
 onTestEnd(test:TestCase,result:TestResult){
  this.results.push({title:test.title,project:test.parent.project()?.name,status:result.status,duration_ms:result.duration,errors:result.errors.map(error=>redactAdminBrowser(error.message??'Falha sem mensagem.')),annotations:test.annotations.filter(a=>!a.type.startsWith('pw:')).map(a=>({type:a.type,description:redactAdminBrowser(a.description??'')}))});
 }
 onStdOut(){}onStdErr(){}
 async onEnd(result:FullResult){
  const path=process.env.QA_ADMIN_REPORT_FILE??'docs/evidence/admin-browser-results.json';mkdirSync(dirname(path),{recursive:true});
  const report={kind:'admin-browser',finished_at:new Date().toISOString(),status:result.status,trace:'off',video:'off',automatic_screenshots:'off',tests:this.results};
  writeFileSync(path,redactAdminBrowser(JSON.stringify(report,null,2))+'\n',{mode:0o600});
 }
}
