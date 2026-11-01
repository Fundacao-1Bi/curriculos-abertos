-- Every public search is pinned to one immutable publication. Keep the
-- publication key in the GIN indexes so retained snapshots do not compete
-- for text-search candidates as the database accumulates publications.
CREATE EXTENSION IF NOT EXISTS btree_gin;

CREATE INDEX IF NOT EXISTS items_publication_search_idx
 ON public.items USING gin (publication_id, search_vector);
CREATE INDEX IF NOT EXISTS items_publication_code_trgm_idx
 ON public.items USING gin (publication_id, public.curriculum_search_code(code) public.gin_trgm_ops);
CREATE INDEX IF NOT EXISTS items_publication_text_trgm_idx
 ON public.items USING gin (publication_id, normalized_text public.gin_trgm_ops);
CREATE INDEX IF NOT EXISTS items_publication_code_aliases_idx
 ON public.items USING gin (publication_id, public.curriculum_search_aliases(payload->'code_aliases') jsonb_path_ops);
CREATE INDEX IF NOT EXISTS items_publication_pdf_joined_text_trgm_idx
 ON public.items USING gin (publication_id, public.curriculum_join_pdf_hyphens(normalized_text) public.gin_trgm_ops)
 WHERE normalized_text ~ '[[:alpha:]]-[[:space:]]+[[:alpha:]]';
CREATE INDEX IF NOT EXISTS items_publication_pdf_joined_text_fts_idx
 ON public.items USING gin (publication_id, pg_catalog.to_tsvector('pg_catalog.portuguese'::pg_catalog.regconfig,
   public.curriculum_join_pdf_hyphens(normalized_text)))
 WHERE normalized_text ~ '[[:alpha:]]-[[:space:]]+[[:alpha:]]';

-- All callers constrain by publication_id; the publication-scoped indexes
-- replace their global equivalents and avoid retaining duplicate GIN data.
DROP INDEX IF EXISTS public.items_search_idx;
DROP INDEX IF EXISTS public.items_code_trgm_idx;
DROP INDEX IF EXISTS public.items_text_trgm_idx;
DROP INDEX IF EXISTS public.items_code_aliases_gin_idx;
DROP INDEX IF EXISTS public.items_pdf_joined_text_trgm_idx;
DROP INDEX IF EXISTS public.items_pdf_joined_text_fts_idx;
