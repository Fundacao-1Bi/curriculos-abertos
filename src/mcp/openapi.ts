import { z } from 'zod';
import { BatchSchema, CompareSchema, ContributionSchema, ExportSchema, QuerySchema, ErrorSchema, ResultSchema, LearningSchema, SourceSchema, RelationSchema, EvidenceSchema, PositionSchema, SearchResultSchema, LearningResultSchema, SourcesResultSchema, SourceResultSchema, RelationsResultSchema, BatchResultSchema, PanoramaResultSchema, ComparisonResultSchema } from './contracts';
const jsonSchema=(schema:z.ZodType)=>z.toJSONSchema(schema,{target:'draft-7'});
const parameters=Object.entries((jsonSchema(QuerySchema) as {properties:Record<string,unknown>}).properties).map(([name,schema])=>({name,in:'query',required:false,schema}));
const errorResponses=Object.fromEntries([400,403,404,409,413,415,429,500,503].map(status=>[String(status),{description:({400:'Entrada inválida',403:'Host ou origem recusados',404:'Registro/publicação inexistente',409:'Exportação não concluída',413:'Limite de payload',415:'Content-Type inválido',429:'Limite de uso',500:'Erro interno',503:'Serviço/publicação indisponível'} as Record<number,string>)[status],content:{'application/json':{schema:{$ref:'#/components/schemas/Error'}}}}]));
const resultResponse={description:'Resposta na publicação identificada. O campo data corresponde à operação; paginação fixa publication e preserva filtros.',headers:{ETag:{schema:{type:'string'}},'X-Data-Publication':{schema:{type:'string'}},'X-Request-ID':{schema:{type:'string'}}},content:{'application/json':{schema:{$ref:'#/components/schemas/Result'}}}};
const idParam={name:'id',in:'path',required:true,schema:{type:'string',maxLength:500}};
function responseFor(name:string){return {...resultResponse,content:{'application/json':{schema:{$ref:'#/components/schemas/'+name}}}};}
function get(summary:string,tag:string,id=false,responseName='Result',paginated=true){return{summary,tags:[tag],parameters:[...(id?[idParam]:[]),...parameters.filter(p=>paginated||!['page','limit'].includes(p.name))],responses:{200:responseFor(responseName),304:{description:'Conteúdo inalterado (ETag)'},...errorResponses}};}
function post(summary:string,tag:string,schema:unknown,status=200,responseName='Result'){return{summary,tags:[tag],requestBody:{required:true,content:{'application/json':{schema}}},responses:{[String(status)]:responseFor(responseName),...errorResponses}};}
export const openapi={
 openapi:'3.1.0',info:{title:'Currículos Abertos — API pública',version:'1.0.0',description:'Consulta gratuita e sem login. Limites efetivos nesta instância: '+(process.env.PUBLIC_RATE_LIMIT??600)+' requisições/minuto por categoria/transporte (ou cliente sob TRUST_PROXY explícito); páginas até 100, lote até 100 IDs, comparação de 2–3 UFs, corpo JSON 64 KiB; exportação '+(process.env.EXPORT_RATE_LIMIT??30)+'/min, contribuição '+(process.env.CONTRIBUTION_RATE_LIMIT??10)+'/h. Sem configuração, defaults 600/30/10; distribuição Compose usa 120/10/10. PUBLIC_RATE_LIMIT é configurável. Busca exata de código tem precedência; acentos são normalizados somente no índice. Publicação não é versão oficial do currículo. Ausência de relação não demonstra ausência pedagógica. Downloads incluem direitos das fontes, sem relenciamento de terceiros.'},servers:[{url:'/api/v1'}],
 paths:{
  '/ufs':{get:get('Listar as 27 UFs com disponibilidade real','Catálogo',false,'Result',false)},
  '/redes':{get:get('Listar jurisdições/redes e âmbito declarado','Catálogo',false,'Result',false)},
  '/curriculos':{get:get('Listar catálogo completo de currículos e edições, sem corte','Catálogo',false,'Result',false)},
  '/curriculos/{id}':{get:get('Consultar currículo','Catálogo',true)},
  '/curriculos/{id}/estrutura':{get:get('Navegar estrutura documentada','Catálogo',true)},
  '/aprendizagens':{get:get('Buscar código, trecho ou tema textual','Aprendizagens',false,'SearchResult')},
  '/aprendizagens/{id}':{get:get('Consultar aprendizagem e evidências','Aprendizagens',true,'LearningResult')},
  '/aprendizagens/consulta-lote':{post:post('Consultar IDs em lote com estado por entrada','Aprendizagens',jsonSchema(BatchSchema),200,'BatchResult')},
  '/correspondencias':{get:get('Relações com origem, tipo e revisões separados','Relações',false,'RelationsResult')},
  '/bncc/aprendizagens/{id}/panorama':{get:get('Panorama nacional das 27 UFs por item BNCC','Relações',true,'PanoramaResult')},
  '/comparacoes':{post:post('Comparar duas ou três UFs na mesma publicação','Relações',jsonSchema(CompareSchema),200,'ComparisonResult')},
  '/analises':{get:get('Matriz e indicadores com denominadores e critérios','Análises')},
  '/cobertura':{get:get('Disponibilidade e completude editorial','Análises')},
  '/fontes':{get:get('Listar catálogo completo de fontes e direitos, sem corte','Proveniência',false,'SourcesResult',false)},
  '/fontes/{id}':{get:get('Consultar fonte e edição','Proveniência',true,'SourceResult')},
  '/publicacoes':{get:get('Listar todas as publicações imutáveis e alterações','Proveniência',false,'Result',false)},
  '/exportacoes':{post:post('Solicitar exportação persistente completa JSON/CSV','Downloads',jsonSchema(ExportSchema),202,'ExportJob')},
  '/exportacoes/{id}':{get:{summary:'Consultar progresso/checksum/download de exportação',tags:['Downloads'],parameters:[idParam],responses:{200:{description:'Job público, sem payloads administrativos',content:{'application/json':{schema:{$ref:'#/components/schemas/ExportJob'}}}},...errorResponses}}},
  '/exportacoes/{id}/arquivo':{get:{summary:'Baixar arquivo completo persistido e verificado por SHA256',tags:['Downloads'],parameters:[idParam],responses:{200:{description:'JSON canônico ou CSV UTF-8 seguro para planilhas. Sem truncamento; Content-Disposition e X-Content-SHA256.',content:{'application/json':{schema:{type:'object'}},'text/csv':{schema:{type:'string'}}}},...errorResponses}}},
  '/contribuicoes':{post:post('Enviar relato sem alterar dados publicados','Contribuições',jsonSchema(ContributionSchema),201,'ContributionResponse')},
  '/contribuicoes/{id}':{get:{summary:'Consultar somente identificador e situação pública da contribuição',tags:['Contribuições'],parameters:[idParam],responses:{200:{description:'Situação pública, sem descrição/contato',content:{'application/json':{schema:{type:'object',properties:{data:{type:'object',properties:{id:{type:'string'},status:{type:'string'}}}}}}}},...errorResponses}}},
  '/openapi.json':{get:{summary:'Esta especificação OpenAPI',responses:{200:{description:'OpenAPI 3.1'}}}},
 },
 components:{schemas:{
  SearchResult:jsonSchema(SearchResultSchema),LearningResult:jsonSchema(LearningResultSchema),SourcesResult:jsonSchema(SourcesResultSchema),SourceResult:jsonSchema(SourceResultSchema),RelationsResult:jsonSchema(RelationsResultSchema),BatchResult:jsonSchema(BatchResultSchema),PanoramaResult:jsonSchema(PanoramaResultSchema),ComparisonResult:jsonSchema(ComparisonResultSchema),Source:jsonSchema(SourceSchema),Position:jsonSchema(PositionSchema),ContributionResponse:{type:'object',required:['data'],properties:{data:{type:'object',required:['id','status','message'],properties:{id:{type:'string'},status:{type:'string'},message:{type:'string'}}}}},Result:jsonSchema(ResultSchema),Error:jsonSchema(ErrorSchema),Query:jsonSchema(QuerySchema),Batch:jsonSchema(BatchSchema),Comparison:jsonSchema(CompareSchema),
  ExportJob:{type:'object',required:['id','status'],properties:{id:{type:'string'},status:{type:'string',enum:['queued','running','paused','succeeded','failed']},progress:{type:'object',additionalProperties:true,description:'Etapa, contagens e progresso estruturado do worker.'},publication:{type:['string','null']},download_url:{type:['string','null']},sha256:{type:['string','null']},size:{type:['number','null']},record_count:{type:['number','null']},error:{type:['string','null']}}},
  Evidence:jsonSchema(EvidenceSchema),Learning:jsonSchema(LearningSchema),Relation:jsonSchema(RelationSchema),
 }},
};
