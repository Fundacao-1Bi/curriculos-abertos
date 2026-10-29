-- Search normalization only: preserve the official code in canonical payloads.
-- Whitespace in PDF cells is not a distinction users must reproduce to locate a code.
CREATE OR REPLACE FUNCTION public.curriculum_search_code(input text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT lower(translate(regexp_replace(translate(coalesce(input,''),
 U&'\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000\FEFF',''), '\s+', '', 'g'),
 'ÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÄËÏÖÜÇáéíóúàèìòùâêîôûãõäëïöüç',
 'AEIOUAEIOUAEIOUAOAEIOUCaeiouaeiouaeiouaoaeiouc'))
$$;
-- Function semantics changed; rebuild every index whose stored keys depend on it.
REINDEX INDEX public.items_code_normalized_idx;
REINDEX INDEX public.items_code_trgm_idx;
REINDEX INDEX public.items_code_aliases_gin_idx;
