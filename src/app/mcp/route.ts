import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import { createMcpServer } from '@/mcp/server';
import { recordRequestMetric } from '@/admin/metrics';
import { checkRequest, errorResponse } from '@/mcp/http';

export const runtime='nodejs';
export const dynamic='force-dynamic';
async function handle(request:Request){
 const started=performance.now();let status=500;
 try{
  const headers=checkRequest(request,'mcp');
  // Uma instância por requisição em modo stateless é o transporte oficial,
  // incluindo initialize/notifications e validação de versão pelo SDK.
  const server=createMcpServer();
  const transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true,maxRequestBodySize:65536});
  await server.connect(transport);
  const response=await transport.handleRequest(request);
  await server.close();
  const output=new Response(response.body,{status:response.status,statusText:response.statusText,headers:response.headers});
  for(const[k,v]of Object.entries(headers))output.headers.set(k,v);
  output.headers.set('Cache-Control','no-store');
  status=output.status;return output;
 }catch(error){const response=errorResponse(request,error);status=response.status;return response;}
 finally{await recordRequestMetric('/mcp',status,performance.now()-started).catch(()=>{});}
}
export const POST=handle;
export const GET=handle;
export const DELETE=handle;
