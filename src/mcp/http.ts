import { createHash, randomUUID } from 'node:crypto';
import { ZodError } from 'zod';

export class HttpError extends Error { constructor(public status:number,public code:string,message:string,public retryAfter?:number){super(message);} }
const windows = new Map<string,{count:number;reset:number}>();
export function checkRequest(request:Request,bucket='read',limit?:number) {
 const configured=process.env.PUBLIC_URL??'http://localhost:3000';
 const publicUrl=new URL(configured);
 const url=new URL(request.url);
 const hosts=new Set([publicUrl.host,...(process.env.ALLOWED_HOSTS??process.env.MCP_ALLOWED_HOSTS??'localhost:3000,127.0.0.1:3000').split(',').map(v=>v.trim()).filter(Boolean)]);
 const host=request.headers.get('host')??url.host;
 if(!hosts.has(host))throw new HttpError(403,'HOST_FORBIDDEN','Host não autorizado. Configure PUBLIC_URL/ALLOWED_HOSTS.');
 const origin=request.headers.get('origin');
 const origins=new Set([publicUrl.origin,...(process.env.ALLOWED_ORIGINS??'http://localhost:3000,http://127.0.0.1:3000').split(',').map(v=>v.trim()).filter(Boolean)]);
 if(origin&&!origins.has(origin))throw new HttpError(403,'ORIGIN_FORBIDDEN','Origem não autorizada.');
 // Cabeçalhos de proxy só são confiáveis sob configuração explícita.
 const peer=process.env.TRUST_PROXY==='true'?(request.headers.get('x-forwarded-for')??'shared').split(',')[0].trim():'shared';
 const key=createHash('sha256').update(`${bucket}:${peer}`).digest('hex');
 const now=Date.now();const duration=bucket==='contribution'?3600000:60000;
 if(windows.size>10000)for(const[k,v]of windows)if(v.reset<=now)windows.delete(k);
 const row=windows.get(key);
 if(!row&&windows.size>=10000)throw new HttpError(429,'RATE_LIMIT','Capacidade de proteção temporariamente atingida.',60);
 const state=row&&row.reset>now?row:{count:0,reset:now+duration};
 state.count++;windows.set(key,state);
 const max=limit??Number(process.env.PUBLIC_RATE_LIMIT??600);
 if(!Number.isSafeInteger(max)||max<1)throw new HttpError(503,'RATE_LIMIT_CONFIGURATION','Configuração de limites indisponível.');
 if(state.count>max)throw new HttpError(429,'RATE_LIMIT','Limite de uso atingido. Tente novamente após o intervalo indicado.',Math.max(1,Math.ceil((state.reset-now)/1000)));
 return {'X-RateLimit-Limit':String(max),'X-RateLimit-Remaining':String(Math.max(0,max-state.count)),'X-RateLimit-Reset':String(Math.ceil(state.reset/1000))};
}
export async function readJson(request:Request,max=65536):Promise<unknown>{
 if(!(request.headers.get('content-type')??'').includes('application/json'))throw new HttpError(415,'CONTENT_TYPE','Use Content-Type: application/json.');
 if(Number(request.headers.get('content-length')??0)>max)throw new HttpError(413,'PAYLOAD_TOO_LARGE','Corpo da requisição excede o limite.');
 const reader=request.body?.getReader();if(!reader)throw new HttpError(400,'INVALID_JSON','Corpo JSON obrigatório.');
 let size=0;const chunks:Uint8Array[]=[];
 while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>max){await reader.cancel();throw new HttpError(413,'PAYLOAD_TOO_LARGE','Corpo da requisição excede o limite.');}chunks.push(part.value);}
 const content=Buffer.concat(chunks).toString('utf8');try{return JSON.parse(content);}catch{throw new HttpError(400,'INVALID_JSON','JSON inválido.');}
}
export function jsonResponse(request:Request,value:unknown,status=200,extra:Record<string,string>={}){
 const content=JSON.stringify(value);const etag='"'+createHash('sha256').update(content).digest('hex')+'"';
 const headers={'Content-Type':'application/json; charset=utf-8','X-Content-Type-Options':'nosniff','Cache-Control':request.method==='GET'&&status===200?'public, max-age=30':'no-store',ETag:etag,...extra};
 if(status===200&&request.method==='GET'&&request.headers.get('if-none-match')===etag)return new Response(null,{status:304,headers});
 return new Response(content,{status,headers});
}
export function errorResponse(request:Request,error:unknown,requestId=randomUUID()){
 let status=500,code='INTERNAL_ERROR',message='Não foi possível concluir a operação.',details:unknown;
 if(error instanceof ZodError){status=400;code='INVALID_INPUT';message='Revise os parâmetros da requisição.';details=error.issues.map(i=>({path:i.path,message:i.message}));}
 else if(error&&typeof error==='object'&&'status'in error&&'code'in error&&'message'in error){const e=error as {status:number;code:string;message:string};status=e.status;code=e.code;message=e.message;}
 if(status>=500)console.error(JSON.stringify({event:'request_error',request_id:requestId,code,message:error instanceof Error?error.message:'Unknown error'}));
 return jsonResponse(request,{error:{code,message,request_id:requestId,...(details?{details}:{})}},status,{'X-Request-ID':requestId,...(status===429?{'Retry-After':String(error instanceof HttpError?error.retryAfter??60:60)}:{})});
}
