-- Immutable code normalizer with an explicit Portuguese transliteration map.
-- Does not depend on mutable unaccent dictionaries, enabling deterministic functional indexes.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE OR REPLACE FUNCTION curriculum_search_code(input text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT lower(translate(regexp_replace(trim(coalesce(input,'')), '\s+', ' ', 'g'),
 'ÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÄËÏÖÜÇáéíóúàèìòùâêîôûãõäëïöüç',
 'AEIOUAEIOUAEIOUAOAEIOUCaeiouaeiouaeiouaoaeiouc'))
$$;
CREATE INDEX IF NOT EXISTS items_code_normalized_idx ON items(publication_id,curriculum_search_code(code));
CREATE INDEX IF NOT EXISTS items_code_trgm_idx ON items USING gin(curriculum_search_code(code) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS items_text_trgm_idx ON items USING gin(normalized_text gin_trgm_ops);
