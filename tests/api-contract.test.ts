import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BatchSchema, CompareSchema, ContributionSchema, ExportSchema, canonicalQuery, parseQuery } from '../src/mcp/contracts';
import { checkRequest, HttpError, readJson } from '../src/mcp/http';
import { openapi } from '../src/mcp/openapi';

test('consulta aceita aliases e fixa paginação/publicação sem alterar código',()=>{
 const q=parseQuery(new URLSearchParams('publicacao=r1&etapa=EF&codigo=EF01MA01-ES*&pagina=2&limite=100&include_unpositioned=true'));
 assert.equal(q.publication,'r1');assert.equal(q.q,'EF01MA01-ES*');assert.equal(q.page,2);assert.equal(q.limit,100);assert.equal(q.include_unknown_positions,true);assert.deepEqual(canonicalQuery({include_unpositioned:true,ufs:['SP','PE']}),{include_unknown_positions:true,ufs:['SP','PE']});
 assert.throws(()=>parseQuery(new URLSearchParams('limit=101')));assert.throws(()=>parseQuery(new URLSearchParams('page=NaN')));assert.throws(()=>parseQuery(new URLSearchParams('uf=XX')));assert.throws(()=>parseQuery(new URLSearchParams('sql=select')));
});
test('comparação livre exige 2 ou 3 UFs distintas e lote preserva entrada inválida por item',()=>{
 assert.ok(CompareSchema.safeParse({ufs:['AC','RR','SP']}).success);assert.ok(!CompareSchema.safeParse({ufs:['SP','SP']}).success);assert.ok(!CompareSchema.safeParse({ufs:['SP']}).success);
 assert.deepEqual(BatchSchema.parse({ids:['real','',null,{},'x'.repeat(501)]}).ids,['real','',null,{},'x'.repeat(501)]);assert.throws(()=>parseQuery(new URLSearchParams('year=6,9')));assert.equal(parseQuery(new URLSearchParams('year=6-9')).year,'6-9');assert.ok(!BatchSchema.safeParse({ids:Array(101).fill('real')}).success);
});
test('contribuição admite URL relativa, restringe protocolos e evita campos privados inesperados',()=>{
 assert.ok(ContributionSchema.safeParse({description:'Correção documental de exemplo',record_url:'/aprendizagens/x',kind:'error'}).success);
 assert.ok(!ContributionSchema.safeParse({description:'Correção documental de exemplo',record_url:'javascript:alert(1)'}).success);
 assert.ok(!ContributionSchema.safeParse({description:'Correção documental de exemplo',contact:'não coletar'}).success);
});
test('HTTP recusa DNS rebinding e origem não autorizada sem confiar em proxy automaticamente',()=>{
 assert.throws(()=>checkRequest(new Request('http://localhost:3000/mcp',{headers:{host:'attacker.test'}})),e=>e instanceof HttpError&&e.status===403);
 assert.throws(()=>checkRequest(new Request('http://localhost:3000/mcp',{headers:{host:'localhost:3000',origin:'https://attacker.test'}})),e=>e instanceof HttpError&&e.status===403);
 assert.ok(checkRequest(new Request('http://localhost:3000/mcp',{headers:{host:'localhost:3000'}})));
});
test('leitor JSON aplica teto ao corpo recebido, inclusive sem content-length',async()=>{
 const request=new Request('http://localhost:3000/api/v1/comparacoes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:'x'.repeat(1000)})});
 await assert.rejects(readJson(request,100),e=>e instanceof HttpError&&e.status===413);
 const invalid=new Request('http://localhost:3000/api/v1/comparacoes',{method:'POST',headers:{'Content-Type':'application/json'},body:'invalid'});
 await assert.rejects(readJson(invalid),e=>e instanceof HttpError&&e.status===400);
});
test('OpenAPI documenta todas operações obrigatórias, exports e contribuições',()=>{
 for(const path of ['/ufs','/redes','/curriculos','/curriculos/{id}','/curriculos/{id}/estrutura','/aprendizagens','/aprendizagens/{id}','/aprendizagens/consulta-lote','/correspondencias','/bncc/aprendizagens/{id}/panorama','/comparacoes','/analises','/cobertura','/fontes','/fontes/{id}','/publicacoes','/exportacoes','/exportacoes/{id}'])assert.ok(path in openapi.paths,path);
});

test('exportação valida contexto antes de enfileirar trabalho persistente',()=>{assert.ok(!ExportSchema.safeParse({view:'panorama'}).success);assert.ok(!ExportSchema.safeParse({view:'comparison'}).success);assert.ok(!ExportSchema.safeParse({view:'comparison',ufs:'ZZ,SP'}).success);assert.ok(!ExportSchema.safeParse({view:'comparison',ufs:'SP,SP'}).success);assert.ok(ExportSchema.safeParse({view:'comparison',ufs:'SP,PE'}).success);});

test('limite de uso recusa excesso com retry-after sem ampliar confiança no proxy',()=>{const request=new Request('http://localhost:3000/api/v1/ufs',{headers:{host:'localhost:3000'}});const bucket='contract-rate-limit';assert.ok(checkRequest(request,bucket,1));assert.throws(()=>checkRequest(request,bucket,1),error=>error instanceof HttpError&&error.status===429&&Boolean(error.retryAfter&&error.retryAfter>0));});
