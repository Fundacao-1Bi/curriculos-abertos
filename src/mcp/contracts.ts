import { z } from 'zod';
import { UFS, type UF } from '../shared/contracts';
const UfSchema=z.enum(Object.keys(UFS) as [UF,...UF[]]);

export const queryShape = {
  publication: z.string().min(1).max(160).optional().describe('Publicação imutável; reutilize a retornada ao paginar.'),
  uf: z.string().regex(/^(BR|AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)$/).optional(),
  q: z.string().max(500).optional().describe('Código, trecho ou tema; busca textual sem modelo pago.'),
  stage: z.enum(['EI','EF','EM']).optional(),
  component: z.string().max(200).optional(),
  area: z.string().max(200).optional(),
  year: z.string().regex(/^\d{1,2}(-\d{1,2})?$/).optional().describe('Ano ou intervalo com interseção dos blocos documentados.'),
  age_group: z.string().max(120).optional(),
  kind: z.string().max(100).optional(),
  curriculum: z.string().max(200).optional(),
  edition: z.string().max(200).optional(),
  relation_type: z.string().max(100).optional(),
  origin: z.string().max(100).optional(),
  technical_validation_status: z.string().max(100).optional(),
  pedagogical_review_status: z.string().max(100).optional(),
  publication_status: z.string().max(100).optional(),
  item_id: z.string().max(300).optional(),
  parent_id: z.string().min(1).max(500).optional().describe('Filhos diretos de um nó da estrutura documental, na mesma publicação.'),
  include_unpositioned: z.boolean().optional(),
  include_unknown_positions: z.boolean().optional(),
  national_id: z.string().max(500).optional(),
  source_id: z.string().max(300).optional(),
  period: z.string().max(200).optional(),
  page: z.number().int().min(1).max(100000).optional().describe('Página das listas paginadas de aprendizagens, relações, panorama, comparação e matriz.'),
  limit: z.number().int().min(1).max(100).optional().describe('Tamanho da página nas listas paginadas; catálogos completos não são cortados.'),
};
export const QuerySchema = z.object(queryShape).strict();
export const CatalogQuerySchema=QuerySchema.omit({page:true,limit:true});
export const IdSchema = z.string().min(1).max(500);
export const BatchSchema = QuerySchema.extend({ids:z.array(z.unknown()).min(1).max(100)});
export const CompareSchema = QuerySchema.extend({ufs:z.array(UfSchema).min(2).max(3),curricula:z.partialRecord(UfSchema,z.string().min(1).max(300)).optional(),editions:z.partialRecord(UfSchema,z.string().min(1).max(200)).optional()}).refine(v=>new Set(v.ufs).size===v.ufs.length,{message:'Escolha duas ou três UFs distintas.',path:['ufs']});
export const ExportSchema = QuerySchema.extend({format:z.enum(['json','csv']).default('json'),view:z.enum(['search','panorama','comparison','analyses']).optional(),ufs:z.union([z.array(UfSchema).min(2).max(3),z.string().regex(/^[A-Z]{2}(,[A-Z]{2}){1,2}$/).refine(v=>v.split(',').every(uf=>uf in UFS),'Escolha UFs brasileiras válidas.')]).optional(),curricula:z.partialRecord(UfSchema,z.string().min(1).max(300)).optional(),editions:z.partialRecord(UfSchema,z.string().min(1).max(200)).optional()}).superRefine((v,ctx)=>{
 if(v.view==='panorama'&&!v.item_id)ctx.addIssue({code:'custom',path:['item_id'],message:'Exportar panorama exige item_id nacional.'});
 if(v.view==='comparison'&&!v.ufs)ctx.addIssue({code:'custom',path:['ufs'],message:'Exportar comparação exige duas ou três UFs.'});
 const ufs=Array.isArray(v.ufs)?v.ufs:typeof v.ufs==='string'?v.ufs.split(','):[];
 if(new Set(ufs).size!==ufs.length)ctx.addIssue({code:'custom',path:['ufs'],message:'Escolha UFs distintas.'});
});
export const ContributionSchema = z.object({kind:z.enum(['error','source','relation']).default('error'),record_url:z.string().max(1000).refine(v=>v.startsWith('/')&&!v.startsWith('//')||/^https?:\/\//i.test(v),'Use uma URL http(s) ou caminho relativo /').optional(),record_id:IdSchema.optional(),description:z.string().trim().min(10).max(5000),evidence_url:z.string().url().max(2000).refine(v=>/^https?:\/\//i.test(v),'Use uma URL http(s)').optional(),honeypot:z.string().max(100).optional()}).strict();
export const ResultSchema = z.object({publication:z.string(),data:z.unknown(),total:z.number().nonnegative().optional(),page:z.number().int().positive().optional(),limit:z.number().int().positive().optional(),next:z.string().nullable().optional()}).passthrough();
export const ErrorSchema = z.object({error:z.object({code:z.string(),message:z.string(),request_id:z.string(),details:z.unknown().optional()})});
export function parseQuery(params:URLSearchParams) {
 const raw:Record<string,unknown>={};
 const aliases:Record<string,string>={publicacao:'publication',etapa:'stage',componente:'component',ano:'year',tipo:'kind',curriculo:'curriculum',edicao:'edition',pagina:'page',limite:'limit',codigo:'q',busca:'q'};
 for(const [key,value] of params){ const k=aliases[key]??key; if(k==='format'||k==='formato')continue; if(k==='page'||k==='limit'){raw[k]=Number(value);}else if(k==='include_unpositioned'||k==='include_unknown_positions'){ if(!['true','false'].includes(value)) throw Object.assign(new Error('include_unpositioned deve ser true ou false.'),{status:400,code:'INVALID_INPUT'});raw[k]=value==='true';}else{raw[k]=value;} }
 if(raw.include_unpositioned!==undefined){raw.include_unknown_positions=raw.include_unpositioned;delete raw.include_unpositioned;}
 return QuerySchema.parse(raw);
}

export const EvidenceSchema=z.object({source_id:IdSchema,page:z.number().int().positive().nullable(),printed_page:z.string().nullable(),section:z.string().nullable(),excerpt:z.string()}).passthrough();
export const PositionSchema=z.object({stage:z.enum(['EI','EF','EM']),component:z.string().nullable(),area:z.string().nullable(),years:z.array(z.number().int()).nullable(),year_label:z.string().nullable(),age_group:z.string().nullable(),period:z.string().nullable()}).passthrough();
export const LearningSchema=z.object({id:IdSchema,curriculum_id:IdSchema,source_id:IdSchema,uf:queryShape.uf.unwrap(),code:z.string().nullable(),code_aliases:z.array(z.string().min(1).max(500)).max(100).optional().describe('Aliases documentados para busca. O campo code preserva a grafia canônica da fonte; alias não estabelece equivalência curricular.'),text:z.string(),normalized_text:z.string(),editorial_note:z.string().nullable(),kind:z.string(),parent_id:IdSchema.nullable(),positions:z.array(PositionSchema),evidence:z.array(EvidenceSchema),extraction_revision:z.string()}).passthrough();
export const SourceSchema=z.object({id:IdSchema,uf:queryShape.uf.unwrap(),title:z.string(),issuer:z.string(),official_url:z.string(),artifact_url:z.string(),stages:z.array(z.enum(['EI','EF','EM'])),components:z.array(z.string()),edition:z.string().nullable(),document_date:z.string().nullable(),homologation_date:z.string().nullable(),application_period:z.string().nullable(),document_type:z.string(),normative_parts:z.array(z.string()),redistribution:z.string(),collected_at:z.string().nullable(),sha256:z.string().nullable(),local_path:z.string().nullable(),status:z.string()}).passthrough();
export const RelationSchema=z.object({id:IdSchema,members:z.array(z.object({item_id:IdSchema,role:z.enum(['source','target']),scope:z.string()}).passthrough()),relation_type:z.string(),origin:z.string(),technical_validation_status:z.string(),pedagogical_review_status:z.string(),publication_status:z.string(),method:z.string(),evidence:z.array(EvidenceSchema)}).passthrough();
export const SearchResultSchema=ResultSchema.extend({data:z.array(LearningSchema)});
export const LearningResultSchema=ResultSchema.extend({data:LearningSchema});
export const SourcesResultSchema=ResultSchema.extend({data:z.array(SourceSchema)});
export const SourceResultSchema=ResultSchema.extend({data:SourceSchema});
export const RelationsResultSchema=ResultSchema.extend({data:z.array(RelationSchema)});
export const BatchResultSchema=ResultSchema.extend({data:z.array(z.object({id:z.unknown(),status:z.enum(['found','not_found','invalid']),item:LearningSchema.nullable()}).passthrough())});
export const PanoramaResultSchema=ResultSchema.extend({data:z.object({national_item:LearningSchema,ufs:z.array(z.object({uf:UfSchema,name:z.string(),status:z.string(),items:z.array(LearningSchema),relations:z.array(RelationSchema),total:z.number().int().nonnegative(),page:z.number().int().positive(),limit:z.number().int().positive(),has_more:z.boolean(),source_ids:z.array(IdSchema)}).passthrough()).length(27)}).passthrough()});
export const ComparisonResultSchema=ResultSchema.extend({data:z.object({ufs:z.array(UfSchema).min(2).max(3),columns:z.array(z.object({uf:UfSchema,name:z.string(),items:z.array(LearningSchema),sources:z.array(SourceSchema),total:z.number().int().nonnegative()}).passthrough()).min(2).max(3),shared_references:z.array(z.object({item_id:IdSchema,ufs:z.array(UfSchema),equivalence_established:z.literal(false)}).passthrough()),relations:z.array(RelationSchema),comparable:z.boolean(),reason:z.string().nullable()}).passthrough()});

export function canonicalQuery<T extends Record<string,unknown>>(input:T):T {
 const value:Record<string,unknown>={...input};
 if(value.include_unpositioned!==undefined){value.include_unknown_positions=value.include_unpositioned;delete value.include_unpositioned;}
 return value as T;
}

export const StructureNodeSchema=z.object({id:IdSchema,parent_id:IdSchema.nullable(),code:z.string().nullable(),text:z.string(),kind:z.string(),source_id:IdSchema,source_number:z.union([z.number(),z.string(),z.null()]).optional(),source_order:z.union([z.number(),z.string(),z.null()]).optional(),document_order:z.union([z.number(),z.string(),z.null()]).optional(),positions:z.array(PositionSchema),evidence:z.array(EvidenceSchema),child_count:z.number().int().nonnegative(),learning_child_count:z.number().int().nonnegative()}).passthrough().superRefine((node,ctx)=>{
 if(node.learning_child_count>node.child_count)ctx.addIssue({code:'custom',path:['learning_child_count'],message:'Filhos de aprendizagem não podem exceder o total de filhos diretos.'});
 if(node.parent_id===node.id)ctx.addIssue({code:'custom',path:['parent_id'],message:'Um nó não pode ser seu próprio pai.'});
});
export const StructureGroupSchema=z.object({stage:z.enum(['EI','EF','EM']).nullable(),component:z.string().nullable(),area:z.string().nullable(),item_count:z.number().int().nonnegative(),kinds:z.array(z.string()),year_labels:z.array(z.string()),age_groups:z.array(z.string())}).passthrough();
export const HierarchySchema=z.object({nodes:z.array(StructureNodeSchema),total:z.number().int().nonnegative(),origin:z.string(),methodology:z.string(),pending_reason:z.string().nullable().optional()}).passthrough().superRefine((hierarchy,ctx)=>{
 if(hierarchy.total!==hierarchy.nodes.length)ctx.addIssue({code:'custom',path:['total'],message:'Total deve corresponder aos nós retornados, sem contar aprendizagens leaf omitidas.'});
 if(new Set(hierarchy.nodes.map(node=>node.id)).size!==hierarchy.nodes.length)ctx.addIssue({code:'custom',path:['nodes'],message:'IDs de nós duplicados na estrutura.'});
});
export const StructureResultSchema=ResultSchema.extend({data:z.array(StructureGroupSchema),hierarchy:HierarchySchema,curriculum:z.object({id:IdSchema}).passthrough()});
