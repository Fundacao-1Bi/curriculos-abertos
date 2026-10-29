import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { LATEST_PROTOCOL_VERSION, SUPPORTED_PROTOCOL_VERSIONS } from '@modelcontextprotocol/sdk/types.js';
import { MCP_TOOL_NAMES } from '../src/mcp/server';

const base=process.env.TEST_BASE_URL??process.env.VERIFY_BASE_URL??process.env.PUBLIC_URL??'http://localhost:3000';
const report:{started_at:string;base:string;client:string;sdk:string;protocol_advertised:string;protocol_supported:string[];results:unknown[];success?:boolean}={started_at:new Date().toISOString(),base,client:'@modelcontextprotocol/sdk Client',sdk:'1.32.2',protocol_advertised:LATEST_PROTOCOL_VERSION,protocol_supported:SUPPORTED_PROTOCOL_VERSIONS,results:[]};
const api=async(path:string,init?:RequestInit)=>{const r=await fetch(`${base}/api/v1/${path}`,init);assert.equal(r.ok,true,`${path}: HTTP ${r.status} ${await r.clone().text()}`);return r.json();};
async function exercise(kind:'http'|'stdio'){
 const client=new Client({name:'curriculos-abertos-interoperability',version:'0.1.0'});
 const transport=kind==='http'?new StreamableHTTPClientTransport(new URL('/mcp',base)):new StdioClientTransport({command:process.execPath,args:['--import','tsx','scripts/mcp-stdio.ts'],cwd:process.cwd(),env:{...Object.fromEntries(Object.entries(process.env).filter((e):e is[string,string]=>typeof e[1]==='string'))},stderr:'pipe'});
 await client.connect(transport);
 const executed:string[]=['initialize'];const dataFailures:string[]=[];
 const partial:Record<string,unknown>={transport:kind,server:client.getServerVersion(),capabilities:client.getServerCapabilities(),protocol_negotiated:transport instanceof StreamableHTTPClientTransport?transport.protocolVersion:undefined,checks:executed,success:false};report.results.push(partial);
 try{
  const tools=await client.listTools();executed.push('tools/list');partial.tools=tools.tools.map(t=>t.name);assert.deepEqual(tools.tools.map(t=>t.name).sort(),[...MCP_TOOL_NAMES].sort());
  const call=async(name:string,args:Record<string,unknown>={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);assert.ok(r.structuredContent,`${name}: structuredContent obrigatório`);executed.push(name);return r.structuredContent as Record<string,unknown>;};
  const versions=await call('consultar_publicacoes');assert.notEqual(versions.publication,'none','Publicação real necessária.');const publication=process.env.TEST_PUBLICATION??String(versions.publication);partial.publication=publication;
  const search=await call('buscar_aprendizagens',{publication,limit:2});assert.ok(Array.isArray(search.data)&&search.data.length>0,'Corpus real deve conter itens.');
  const item=(search.data as Record<string,unknown>[])[0];partial.real_item_id=item.id;assert.equal(typeof item.id,'string');assert.ok(Array.isArray(item.evidence)&&item.evidence.length>0,'Aprendizagem deve ter evidência.');
  const actual=await api(`aprendizagens/${encodeURIComponent(String(item.id))}?publication=${encodeURIComponent(publication)}`);
  const batch=await call('consultar_aprendizagens',{publication,ids:[item.id,'id-inexistente-controlado','',null,{},'x'.repeat(501)]});assert.equal(batch.publication,actual.publication);assert.deepEqual((batch.data as {status:string}[]).map(r=>r.status),['found','not_found','invalid','invalid','invalid','invalid']);
  // A consulta individual está no lote e também se confere texto/ID com a API.
  assert.ok(JSON.stringify(batch.data).includes(String(item.id)));assert.ok(JSON.stringify(batch.data).includes(String(item.text)));assert.equal(actual.data.id,item.id);
  const second=await call('buscar_aprendizagens',{publication,limit:2,page:2});assert.equal(second.publication,publication);
  const firstIds=new Set((search.data as {id:string}[]).map(v=>v.id));for(const row of second.data as {id:string}[])assert.ok(!firstIds.has(row.id),'Paginação não pode duplicar itens.');
  const national=await call('buscar_aprendizagens',{publication,uf:'BR',limit:1});
  const bncc=Array.isArray(national.data)?(national.data as {id:string}[])[0]:undefined;
  if(bncc){const panorama=await call('consultar_panorama_bncc',{publication,id:bncc.id});const panoramaApi=await api(`bncc/aprendizagens/${encodeURIComponent(bncc.id)}/panorama?publication=${encodeURIComponent(publication)}`);assert.deepEqual(panorama,panoramaApi);}else{dataFailures.push('Panorama não verificável: BNCC real ausente na publicação.');}
  const compareArgs={publication,ufs:['SP','PE'],limit:2};const comparison=await call('comparar_curriculos',compareArgs);
  const compareApi=await api('comparacoes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(compareArgs)});assert.deepEqual(comparison,compareApi);
  const relations=await call('consultar_correspondencias',{publication,limit:2});const relationsApi=await api(`correspondencias?publication=${encodeURIComponent(publication)}&limit=2`);assert.deepEqual(relations,relationsApi);
  await call('listar_curriculos',{publication});await call('consultar_analises',{publication,limit:2});await call('consultar_fontes',{publication});await call('consultar_cobertura',{publication});
  const invalid=await client.callTool({name:'comparar_curriculos',arguments:{ufs:['SP']}});assert.equal(invalid.isError,true,'Entrada inválida deve ser recusada.');
  const nonexistent=await client.callTool({name:'consultar_panorama_bncc',arguments:{publication,id:'inexistente'}});assert.equal(nonexistent.isError,true,'ID inexistente deve produzir erro controlado.');
  Object.assign(partial,{transport:kind,server:client.getServerVersion(),capabilities:client.getServerCapabilities(),tools:tools.tools.map(t=>t.name),publication,real_item_id:item.id,national_item_id:bncc?.id,checks:[...executed,'invalid_input','controlled_error','api_consistency'],success:dataFailures.length===0,data_failures:dataFailures});assert.equal(dataFailures.length,0,dataFailures.join(' '));
 }finally{await client.close();}
}
let failed=false;for(const kind of ['http',...(process.argv.includes('--stdio')?['stdio']:[])] as ('http'|'stdio')[]){try{await exercise(kind);}catch(error){failed=true;report.results.push({transport:kind,error:error instanceof Error?error.message:String(error)});}}report.success=!failed;if(failed)process.exitCode=1;
await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/mcp-interoperability.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
