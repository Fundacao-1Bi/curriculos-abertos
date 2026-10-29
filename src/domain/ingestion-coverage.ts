import type pg from 'pg';
import type { Source } from '../shared/contracts';
import { DomainError } from './errors';

type Row=Record<string,unknown>;
const PART_KEYS=['expected_parts','processed_parts','reconciled_parts'] as const;
const reconciliationPending='Atualização de fonte exige nova reconciliação documental deste recorte.';
const fail=(message:string):never=>{throw new DomainError(422,'INGESTION_COVERAGE_AMBIGUOUS',message);};
const ids=(row:Row):string[]=>Array.isArray(row.source_ids)?row.source_ids.filter((id):id is string=>typeof id==='string'):[];
const stable=(value:unknown):string=>JSON.stringify(value,(_key,input)=>input&&typeof input==='object'&&!Array.isArray(input)?Object.fromEntries(Object.entries(input).sort(([a],[b])=>a.localeCompare(b))):input);
function unique<T>(values:T[]):T[]{const seen=new Set<string>();return values.filter(value=>{const key=stable(value);if(seen.has(key))return false;seen.add(key);return true;});}
function scope(row:Row):string {
 return JSON.stringify([row.uf??null,row.stage??null,row.component??null]);
}

/** Preserve attributed entries, replacing only the requested sources. */
export function mergeSourceAttributedCoverageValues(baseRows:Row[],rawRows:Row[],key:string,targetSourceIds:string[]):unknown[]{
 const targets=new Set(targetSourceIds),parts=PART_KEYS.includes(key as typeof PART_KEYS[number]);
 const select=(row:Row,raw:boolean):unknown[]=>{
  const rowIds=ids(row),hasTarget=rowIds.some(id=>targets.has(id)),hasOther=rowIds.some(id=>!targets.has(id));
  const input=row[key],count=row[key+'_count'];
  if(input===undefined||input===null){if(parts&&typeof count==='number'&&count>0&&!(hasTarget&&!hasOther&&!raw))return fail(`Inventário ${key} possui contagem sem partes atribuídas por fonte.`);return [];}
  if(typeof input==='number'){
   if(!Number.isSafeInteger(input)||input<0)return fail(`Inventário ${key} possui agregado inválido.`);
   if(input===0||!raw&&hasTarget&&!hasOther)return [];
   return fail(`Inventário legado ${key} não pode ser decomposto por fonte sem perder partes.`);
  }
  if(!Array.isArray(input))return fail(`Campo ${key} exige uma lista atribuível por fonte.`);
  if(parts&&count!==undefined&&count!==input.length)return fail(`Contagem ${key} diverge das partes documentadas.`);
  return input.filter(entry=>{
   const sourceId=entry&&typeof entry==='object'&&!Array.isArray(entry)?(entry as Row).source_id:undefined;
   if(typeof sourceId==='string')return raw?targets.has(sourceId):!targets.has(sourceId);
   if(hasTarget&&hasOther||!rowIds.length)return fail(`Entrada ${key} sem source_id em recorte misto; atualização recusada.`);
   if(parts&&raw&&hasTarget)return fail(`Parte ${key} recebida sem source_id explícito.`);
   return raw?hasTarget:!hasTarget;
  });
 };
 return unique([...baseRows.flatMap(row=>select(row,false)),...rawRows.flatMap(row=>select(row,true))]);
}

const COUNTS_SQL=`
WITH scoped_items AS (
 SELECT DISTINCT i.id,i.kind,i.evidence FROM ingestion_items i
 WHERE i.source_id=ANY($1::text[]) AND (($2::text IS NULL AND $3::text IS NULL) OR EXISTS (
  SELECT 1 FROM jsonb_array_elements(i.positions) p
  WHERE ($2::text IS NULL OR p->>'stage'=$2::text)
    AND ($3::text IS NULL OR p->>'component'=$3::text OR p->>'area'=$3::text)
 ))
), scoped_relations AS (
 SELECT DISTINCT r.id,r.payload FROM ingestion_relations r
 JOIN ingestion_members m ON m.relation_id=r.id JOIN scoped_items i ON i.id=m.item_id
)
SELECT (SELECT count(*)::int FROM scoped_items) AS item_count,
 (SELECT count(*)::int FROM scoped_items WHERE jsonb_array_length(evidence)>0) AS items_with_evidence,
 (SELECT count(*)::int FROM scoped_relations) AS relation_count,
 COALESCE((SELECT jsonb_object_agg(kind,n) FROM (SELECT kind,count(*)::int n FROM scoped_items GROUP BY kind) x),'{}'::jsonb) AS learning_types,
 COALESCE((SELECT jsonb_object_agg(value,n) FROM (SELECT payload->>'origin' value,count(*)::int n FROM scoped_relations WHERE payload->>'origin' IS NOT NULL GROUP BY payload->>'origin') x),'{}'::jsonb) AS relations,
 COALESCE((SELECT jsonb_object_agg(value,n) FROM (SELECT payload->>'relation_type' value,count(*)::int n FROM scoped_relations WHERE payload->>'relation_type' IS NOT NULL GROUP BY payload->>'relation_type') x),'{}'::jsonb) AS relation_types,
 COALESCE((SELECT jsonb_object_agg(value,n) FROM (SELECT payload->>'pedagogical_review_status' value,count(*)::int n FROM scoped_relations WHERE payload->>'pedagogical_review_status' IS NOT NULL GROUP BY payload->>'pedagogical_review_status') x),'{}'::jsonb) AS review_statuses,
 COALESCE((SELECT jsonb_object_agg(value,n) FROM (SELECT payload->>'technical_validation_status' value,count(*)::int n FROM scoped_relations WHERE payload->>'technical_validation_status' IS NOT NULL GROUP BY payload->>'technical_validation_status') x),'{}'::jsonb) AS technical_review_statuses,
 COALESCE((SELECT jsonb_object_agg(value,n) FROM (SELECT payload->>'publication_status' value,count(*)::int n FROM scoped_relations WHERE payload->>'publication_status' IS NOT NULL GROUP BY payload->>'publication_status') x),'{}'::jsonb) AS publication_statuses`;

/** Recompute affected scope summaries over the already merged temporary ingestion views. */
export async function mergeIngestionCoverage(client:pg.PoolClient,baseRows:Row[],rawRows:Row[],targetSourceIds:string[],sources:Source[]):Promise<Row[]>{
 const targets=new Set(targetSourceIds),sourceMap=new Map(sources.map(source=>[source.id,source]));
 for(const id of targets)if(!sourceMap.has(id))fail('Fonte alvo ausente do inventário final.');
 const rawByScope=new Map<string,Row[]>();
 for(const row of rawRows){if(!ids(row).some(id=>targets.has(id)))continue;const key=scope(row);rawByScope.set(key,[...(rawByScope.get(key)??[]),row]);}
 const affected=new Set(rawByScope.keys());
 for(const row of baseRows)if(ids(row).some(id=>targets.has(id)))affected.add(scope(row));
 const baseByScope=new Map<string,Row[]>();
 for(const row of baseRows){const key=scope(row);if(affected.has(key))baseByScope.set(key,[...(baseByScope.get(key)??[]),row]);}
 const replacements=new Map<string,Row>();
 for(const key of affected){
  const previous=baseByScope.get(key)??[],incoming=rawByScope.get(key)??[];
  if(previous.length>1)fail('Cobertura base contém recorte afetado duplicado.');
  const sourceIds=unique([...previous.flatMap(ids).filter(id=>!targets.has(id)),...incoming.flatMap(ids).filter(id=>targets.has(id))]);
  for(const id of sourceIds)if(!sourceMap.has(id))fail('Fonte da cobertura ausente do inventário final.');
  const first=previous[0]??incoming[0];const row:Row={...first};
  if(typeof row.uf!=='string'||row.stage!==undefined&&row.stage!==null&&typeof row.stage!=='string'||row.component!==undefined&&row.component!==null&&typeof row.component!=='string')fail('Recorte afetado sem UF, etapa ou componente válido.');
  for(const partKey of PART_KEYS){const entries=mergeSourceAttributedCoverageValues(previous,incoming,partKey,targetSourceIds);row[partKey]=entries;row[partKey+'_count']=entries.length;}
  row.critical_errors=mergeSourceAttributedCoverageValues(previous,incoming,'critical_errors',targetSourceIds);
  const counts=await client.query(COUNTS_SQL,[sourceIds,row.stage,row.component??null]);
  if(!counts.rows[0])fail('Consulta de cobertura não retornou resumos.');
  Object.assign(row,counts.rows[0]);
  row.source_ids=sourceIds;
  row.editions=unique(sourceIds.map(id=>sourceMap.get(id)?.edition??'edição não confirmada'));
  row.ready=false;row.reconciled=false;row.national_release_ready=false;
  for(const field of Object.keys(row))if(field.startsWith('national_')&&typeof row[field]==='boolean')row[field]=false;
  row.editorial_completeness='pending_revalidation';
  row.technical_verification=Number(row.processed_parts_count)>0?'partial':'not_processed';
  row.mapping_coverage='pending_revalidation_after_source_update';
  row.pending=unique([...previous,...incoming].flatMap(value=>Array.isArray(value.pending)?value.pending:[]).concat(reconciliationPending));
  row.source_update={operation:'source_replacement',target_source_ids:[...targets],scope:{uf:row.uf,stage:row.stage,component:row.component??null},reconciliation_required:true};
  replacements.set(key,row);
 }
 const result=baseRows.map(row=>replacements.get(scope(row))??row);
 for(const [key] of rawByScope)if(!baseByScope.has(key))result.push(replacements.get(key)!);
 return result;
}
