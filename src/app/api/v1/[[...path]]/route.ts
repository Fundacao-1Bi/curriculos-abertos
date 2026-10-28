import * as domain from '@/domain/service';
import { canonicalQuery, BatchSchema, CompareSchema, ContributionSchema, ExportSchema, ResultSchema, SearchResultSchema, LearningResultSchema, SourcesResultSchema, SourceResultSchema, RelationsResultSchema, BatchResultSchema, PanoramaResultSchema, ComparisonResultSchema, parseQuery } from '@/mcp/contracts';
import { checkRequest, errorResponse, HttpError, jsonResponse, readJson } from '@/mcp/http';
import { recordRequestMetric } from '@/admin/metrics';
import { openapi } from '@/mcp/openapi';
import { randomUUID, createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { Readable } from 'node:stream';
import { createContribution, getContribution } from '@/admin/contributions';
import { enqueueJob, getPublicExport, safeExportPath } from '@/worker/jobs';

export const runtime='nodejs';
export const dynamic='force-dynamic';
type Context={params:Promise<{path?:string[]}>};

async function handle(request:Request,context:Context){
 const requestId=randomUUID(),started=performance.now();let status=200,routeLabel='/api/v1/unknown';
 try{
  const {path=[]}=await context.params;
  const fixed=new Set(['ufs','redes','curriculos','aprendizagens','correspondencias','bncc','analises','cobertura','fontes','publicacoes','exportacoes','contribuicoes','openapi.json']);
  if(fixed.has(path[0]))routeLabel='/api/v1/'+path[0]+(path[1]?(path[1]==='consulta-lote'?'/consulta-lote':path[0]==='bncc'?'/aprendizagens/{id}/panorama':'/{id}'):'')+(path[2]==='estrutura'?'/estrutura':path[2]==='arquivo'?'/arquivo':'');
  const rateHeaders=checkRequest(request,path[0]==='contribuicoes'&&request.method==='POST'?'contribution':path[0]==='exportacoes'&&request.method==='POST'?'export':'read',path[0]==='contribuicoes'&&request.method==='POST'?Number(process.env.CONTRIBUTION_RATE_LIMIT??10):path[0]==='exportacoes'&&request.method==='POST'?Number(process.env.EXPORT_RATE_LIMIT??30):undefined);
  const headers={...rateHeaders,'X-Request-ID':requestId};
  const url=new URL(request.url);
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{...headers,Allow:'GET, POST, OPTIONS'}});
  if(path[0]==='openapi.json'&&request.method==='GET')return jsonResponse(request,openapi,200,headers);
  if(path[0]==='contribuicoes'){
   if(request.method==='POST'&&path.length===1){
    const raw=await readJson(request);const normalized=raw&&typeof raw==='object'?{...raw}:raw;
    if(normalized&&typeof normalized==='object'&&'website'in normalized){Object.assign(normalized,{honeypot:normalized.website});delete (normalized as Record<string,unknown>).website;}
    const input=ContributionSchema.parse(normalized);
    if(input.honeypot)throw new HttpError(400,'INVALID_CONTRIBUTION','Não foi possível receber a contribuição.');
    const saved=await createContribution(input);
    status=201;return jsonResponse(request,{data:saved},201,headers);
   }
   if(request.method==='GET'&&path.length===2){
    const saved=await getContribution(path[1]);if(!saved)throw new HttpError(404,'NOT_FOUND','Contribuição não encontrada.');
    return jsonResponse(request,{data:saved},200,headers);
   }
   throw new HttpError(405,'METHOD_NOT_ALLOWED','Método não permitido para esta operação.');
  }
  if(path[0]==='exportacoes'){
   if(request.method==='POST'&&path.length===1){
    const {format,...rawQuery}=ExportSchema.parse(await readJson(request));const query=canonicalQuery(rawQuery);
    const publication=await domain.resolvePublication(query.publication);
    const pinned={...query,publication};
    const key=createHash('sha256').update(JSON.stringify({query:pinned,format})).digest('hex');
    const job=await enqueueJob('export',{query:pinned,format},`public-export:${key}`);
    status=202;return jsonResponse(request,{publication,id:job.id,status:job.status,progress:job.progress,status_url:`/api/v1/exportacoes/${job.id}`,download_url:job.status==='succeeded'?`/api/v1/exportacoes/${job.id}/arquivo`:null},202,headers);
   }
   if(request.method==='GET'&&(path.length===2||path.length===3&&path[2]==='arquivo')){
    if(!/^[a-zA-Z0-9_-]{1,100}$/.test(path[1]))throw new HttpError(400,'INVALID_ID','Identificador de exportação inválido.');
    const job=await getPublicExport(path[1]);if(!job)throw new HttpError(404,'NOT_FOUND','Exportação não encontrada.');
    if(path[2]==='arquivo'){
     if(job.status!=='succeeded'||!job.result)throw new HttpError(409,'EXPORT_NOT_READY','Exportação ainda não disponível. Consulte o progresso.');
     const result=job.result as {storage_key:string;mime_type:string;filename:string;sha256:string;publication:string};
     const filePath=safeExportPath(result.storage_key);
     const hash=createHash('sha256');for await(const chunk of createReadStream(/* turbopackIgnore: true */ filePath))hash.update(chunk);
     const checksum=hash.digest('hex');
     if(checksum!==result.sha256)throw new HttpError(503,'EXPORT_INTEGRITY','Integridade da exportação não confirmada. Solicite uma nova exportação.');
     const body=Readable.toWeb(createReadStream(/* turbopackIgnore: true */ filePath)) as ReadableStream<Uint8Array>;
     return new Response(body,{headers:{...headers,'Content-Type':result.mime_type,'Content-Disposition':`attachment; filename="${result.filename.replace(/[^a-zA-Z0-9._-]/g,'_')}"`,'X-Content-SHA256':checksum,'X-Data-Publication':result.publication,'Cache-Control':'public, max-age=31536000, immutable','X-Content-Type-Options':'nosniff'}});
    }
    const result=job.result as Record<string,unknown>|null;
    return jsonResponse(request,{id:job.id,status:job.status,progress:job.progress,error:job.error?'Falha no processamento. Solicite novamente ou informe este identificador.':null,publication:result?.publication??null,sha256:result?.sha256??null,size:result?.size??null,record_count:result?.record_count??null,download_url:job.status==='succeeded'?`/api/v1/exportacoes/${job.id}/arquivo`:null},200,headers);
   }
   throw new HttpError(405,'METHOD_NOT_ALLOWED','Método não permitido para esta operação.');
  }
  let result:unknown;
  if(request.method==='POST'){
   if(path.join('/')==='aprendizagens/consulta-lote'){
    const{ids,...query}=BatchSchema.parse(await readJson(request));result=await domain.batchLearnings(ids,canonicalQuery(query));
   }else if(path.join('/')==='comparacoes'){result=await domain.compare(canonicalQuery(CompareSchema.parse(await readJson(request))));}
   else throw new HttpError(405,'METHOD_NOT_ALLOWED','Esta operação não aceita POST.');
  }else if(request.method==='GET'){
   const query=parseQuery(url.searchParams);
   switch(path[0]){
    case'ufs':result=await domain.listUfs(query);break;
    case'redes':result=await domain.listNetworks(query);break;
    case'curriculos':result=path[1]?path[2]==='estrutura'?await domain.getStructure(path[1],query):await domain.getCurriculum(path[1],query):await domain.listCurricula(query);break;
    case'aprendizagens':result=path[1]?await domain.getLearning(path[1],query):await domain.searchLearnings(query);break;
    case'correspondencias':result=await domain.listRelations(query);break;
    case'bncc':if(path[1]!=='aprendizagens'||!path[2]||path[3]!=='panorama')throw new HttpError(404,'NOT_FOUND','Operação não encontrada.');result=await domain.panorama(path[2],query);break;
    case'analises':result=await domain.analyses(query);break;
    case'cobertura':result=await domain.coverage(query);break;
    case'fontes':result=path[1]?await domain.getSource(path[1],query):await domain.listSources(query);break;
    case'publicacoes':result=await domain.listPublications(query);break;
    default:throw new HttpError(404,'NOT_FOUND','Operação não encontrada. Consulte /api/v1/openapi.json.');
   }
  }else throw new HttpError(405,'METHOD_NOT_ALLOWED','Método não permitido.');
  const outputSchema=path[0]==='aprendizagens'?(request.method==='POST'?BatchResultSchema:path[1]?LearningResultSchema:SearchResultSchema):path[0]==='fontes'?(path[1]?SourceResultSchema:SourcesResultSchema):path[0]==='correspondencias'?RelationsResultSchema:path[0]==='bncc'?PanoramaResultSchema:path[0]==='comparacoes'?ComparisonResultSchema:ResultSchema;
  const parsed=outputSchema.safeParse(result);
  if(!parsed.success)throw new HttpError(502,'DOMAIN_CONTRACT','Resposta de domínio inválida. Informe o identificador da requisição.');
  const validated=parsed.data;
  const response=jsonResponse(request,validated,200,{...headers,'X-Data-Publication':validated.publication});status=response.status;return response;
 }catch(error){const response=errorResponse(request,error,requestId);status=response.status;return response;}
 finally{await recordRequestMetric(routeLabel,status,performance.now()-started).catch(()=>{console.error(JSON.stringify({event:'metric_write_failed',request_id:requestId}));});console.info(JSON.stringify({event:'api_request',request_id:requestId,method:request.method,path:routeLabel,status,duration_ms:Math.round(performance.now()-started)}));}
}
export const GET=handle;
export const POST=handle;
export const OPTIONS=handle;
