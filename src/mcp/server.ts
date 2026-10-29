import { McpServer, type ToolCallback } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import * as domain from '../domain/service';
import { canonicalQuery, BatchSchema, CompareSchema, IdSchema, QuerySchema, CatalogQuerySchema, ResultSchema, SearchResultSchema, BatchResultSchema, PanoramaResultSchema, ComparisonResultSchema, SourcesResultSchema, SourceResultSchema, RelationsResultSchema } from './contracts';

export const MCP_TOOL_NAMES=['listar_curriculos','buscar_aprendizagens','consultar_aprendizagens','consultar_correspondencias','consultar_panorama_bncc','comparar_curriculos','consultar_analises','consultar_fontes','consultar_cobertura','consultar_publicacoes'] as const;
export function createMcpServer(){
 const server=new McpServer({name:'curriculos-abertos',version:'0.1.0'},{instructions:'Dados curriculares documentais. Fixe publication retornada em paginação e comparação. Ausência de correspondência não demonstra ausência pedagógica. Interpretações e revisões automatizadas são identificadas.',maxToolInputElements:1000});
 const annotations={readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false};
 function register<T extends z.ZodObject>(name:string,description:string,schema:T,operation:(value:z.output<T>)=>Promise<unknown>,outputSchema:z.ZodObject=ResultSchema){
  const handler = async(args: z.output<T>):Promise<CallToolResult>=>{
   try{
    const value=canonicalQuery(args);
    const result=outputSchema.parse(await operation(value as z.output<T>)) as z.output<typeof ResultSchema>;
    const size=Array.isArray(result.data)?result.data.length:undefined;
    return {structuredContent:result,content:[{type:'text' as const,text:`Publicação ${result.publication}.${size===undefined?'':` ${size} registros nesta resposta.`}${result.total===undefined?'':` Total no recorte: ${result.total}.`}${result.next?` Próxima página: ${result.next}`:''} Consulte structuredContent para IDs, textos oficiais, fontes, revisão e contexto completos.`}]};
   }catch(error){
    const e=error as {status?:number;code?:string;message?:string};
    const controlled=typeof e.status==='number'&&e.status<500;
    return {isError:true,content:[{type:'text' as const,text:JSON.stringify({error:{code:e.code??'SERVICE_UNAVAILABLE',message:controlled?e.message:'Consulta indisponível no momento. Verifique a publicação carregada e tente novamente.'}})}]};
   }
  };
  // SDK aceita Zod 3/4; esta ponte preserva o tipo Zod 4 inferido do schema.
  server.registerTool(name,{description,inputSchema:schema,outputSchema,annotations},handler as ToolCallback<T>);
 }
 register('listar_curriculos','Lista catálogo completo de currículos e edições por UF/etapa, sem corte ou paginação. Fixe publication nas próximas consultas.',CatalogQuerySchema,q=>domain.listCurricula(q));
 register('buscar_aprendizagens','Busca textual/código e aliases documentados (code_aliases), sem alterar code. parent_id seleciona filhos diretos da hierarquia documental, sem inferir pré-requisitos. age_months filtra por interseção inclusiva dos limites documentados (0–1800 meses), sem inferir idade; include_unknown_positions inclui desconhecidos explicitamente. Paginação estável, limite máximo 100.',QuerySchema,q=>domain.searchLearnings(q),SearchResultSchema);
 register('consultar_aprendizagens','Consulta de 1 a 100 IDs canônicos. Resultado individual found/not_found/invalid; um código isolado não é ID global.',BatchSchema,({ids,...q})=>domain.batchLearnings(ids,q),BatchResultSchema);
 register('consultar_correspondencias','Relações por origem, tipo e revisão; interpretação não é equivalência oficial. IDs podem participar em grupos muitos-para-muitos.',QuerySchema,q=>domain.listRelations(q),RelationsResultSchema);
 register('consultar_panorama_bncc','Panorama das 27 UFs para ID canônico de item nacional. Dados insuficientes são distintos de nenhuma correspondência localizada.',QuerySchema.extend({id:IdSchema}),({id,...q})=>domain.panorama(id,q),PanoramaResultSchema);
 register('comparar_curriculos','Compara duas ou três UFs distintas no mesmo snapshot e recorte. Referência BNCC comum não comprova equivalência.',CompareSchema,q=>domain.compare(q),ComparisonResultSchema);
 register('consultar_analises','Indicadores descritivos com critérios e denominadores da mesma publicação; sem ranking de qualidade curricular.',QuerySchema,q=>domain.analyses(q));
 register('consultar_fontes','Lista fontes ou consulta source_id, preservando edições, localizadores, obtenção e condições de reutilização.',CatalogQuerySchema.extend({id:IdSchema.optional()}),({id,...q})=>id?domain.getSource(id,q):domain.listSources(q),ResultSchema.extend({data:z.union([SourcesResultSchema.shape.data,SourceResultSchema.shape.data])}));
 register('consultar_cobertura','Consulta disponibilidade e completude editorial por UF/etapa/componente; extração e reconciliação são distintas.',QuerySchema,q=>domain.coverage(q));
 register('consultar_publicacoes','Descobre publicações imutáveis, schema, extração e revisão dos vínculos. Use o ID de publicação para fixar consultas.',CatalogQuerySchema,q=>domain.listPublications(q));
 return server;
}
