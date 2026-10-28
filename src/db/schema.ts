import { pgTable, text, integer, boolean, jsonb, timestamp, primaryKey } from 'drizzle-orm/pg-core';
import type { Bundle,Learning,Source,Relation } from '../shared/contracts';
/** The canonical migrations are src/db/migrations/*.sql. Typed read model for PostgreSQL snapshots. */
export const publications=pgTable('publications',{
 id:text('id').primaryKey(),schemaVersion:text('schema_version').notNull(),createdAt:timestamp('created_at',{withTimezone:true}).notNull(),
 extractionRevision:text('extraction_revision').notNull(),mappingRevision:text('mapping_revision').notNull(),sha256:text('sha256').notNull(),
 itemCount:integer('item_count').notNull(),sourceCount:integer('source_count').notNull(),relationCount:integer('relation_count').notNull(),
 payload:jsonb('payload').$type<Bundle>().notNull(),importedAt:timestamp('imported_at',{withTimezone:true}).notNull(),
});
export const currentPublication=pgTable('current_publication',{singleton:boolean('singleton').primaryKey(),publicationId:text('publication_id').notNull().references(()=>publications.id)});
export const sources=pgTable('sources',{publicationId:text('publication_id').notNull().references(()=>publications.id),id:text('id').notNull(),uf:text('uf').notNull(),payload:jsonb('payload').$type<Source>().notNull()},t=>[primaryKey({columns:[t.publicationId,t.id]})]);
export const items=pgTable('items',{publicationId:text('publication_id').notNull().references(()=>publications.id),id:text('id').notNull(),uf:text('uf').notNull(),curriculumId:text('curriculum_id').notNull(),sourceId:text('source_id').notNull(),code:text('code'),text:text('text').notNull(),normalizedText:text('normalized_text').notNull(),kind:text('kind').notNull(),positions:jsonb('positions').$type<Learning['positions']>().notNull(),evidence:jsonb('evidence').$type<Learning['evidence']>().notNull(),payload:jsonb('payload').$type<Learning>().notNull()},t=>[primaryKey({columns:[t.publicationId,t.id]})]);
export const relations=pgTable('relations',{publicationId:text('publication_id').notNull().references(()=>publications.id),id:text('id').notNull(),relationType:text('relation_type').notNull(),origin:text('origin').notNull(),technicalValidationStatus:text('technical_validation_status').notNull(),pedagogicalReviewStatus:text('pedagogical_review_status').notNull(),publicationStatus:text('publication_status').notNull(),payload:jsonb('payload').$type<Relation>().notNull()},t=>[primaryKey({columns:[t.publicationId,t.id]})]);

export const publicationMetadata=pgTable('publication_metadata',{publicationId:text('publication_id').primaryKey().references(()=>publications.id),changelog:jsonb('changelog').$type<unknown[]>().notNull(),payload:jsonb('payload').notNull()});
export const publicationCoverage=pgTable('publication_coverage',{publicationId:text('publication_id').notNull().references(()=>publications.id),rowIndex:integer('row_index').notNull(),uf:text('uf'),stage:text('stage'),component:text('component'),payload:jsonb('payload').notNull()},t=>[primaryKey({columns:[t.publicationId,t.rowIndex]})]);
