-- Auxiliary search form only: canonical item text and payload remain immutable.
-- Join PDF line-break hyphens between letters. A compound without whitespace
-- (guarda-chuva) or a spaced marker (a - b) retains its original spelling.
CREATE OR REPLACE FUNCTION public.curriculum_join_pdf_hyphens(input text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
SET search_path = pg_catalog AS $$
 SELECT pg_catalog.regexp_replace(input,
   '(?<=[[:alpha:]])-[[:space:]]+(?=[[:alpha:]])', '', 'g')
$$;

-- Index only affected rows; do not duplicate search indexes for the whole corpus.
-- Queries must include this exact partial predicate alongside the expression.
CREATE INDEX IF NOT EXISTS items_pdf_joined_text_trgm_idx
 ON public.items USING gin (public.curriculum_join_pdf_hyphens(normalized_text) public.gin_trgm_ops)
 WHERE normalized_text ~ '[[:alpha:]]-[[:space:]]+[[:alpha:]]';
CREATE INDEX IF NOT EXISTS items_pdf_joined_text_fts_idx
 ON public.items USING gin (pg_catalog.to_tsvector('pg_catalog.portuguese'::pg_catalog.regconfig,
   public.curriculum_join_pdf_hyphens(normalized_text)))
 WHERE normalized_text ~ '[[:alpha:]]-[[:space:]]+[[:alpha:]]';
