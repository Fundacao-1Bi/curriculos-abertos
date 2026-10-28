import Link from 'next/link';
import {date, format, row, string, url, type Row} from '@/components/view';

function publicUrl(value:unknown):string|null {
 if(typeof value!=='string')return null;
 try {return ['http:','https:'].includes(new URL(value).protocol)?value:null;} catch {return null;}
}

export function SourceLinks({source}:{source:Row}) {
 const links:[string,unknown][]=[
  ['Referência de origem',source.official_url],
  ['Página de procedência',source.catalogPage??source.catalog_page],
  ['Fonte indicada pelo catálogo',source.originalSource??source.original_source],
  [source.effective_url?'Recurso consultado na coleta':'Recurso referenciado',source.effective_url??source.artifact_url],
  ['Artefato de referência',source.artifact_url],
 ];
 const seen=new Set<string>();
 return <>{links.map(([title,value])=>{
  const href=publicUrl(value);if(!href||seen.has(href))return null;seen.add(href);
  return <a key={href} href={href} target="_blank" rel="noreferrer">{title} ↗</a>;
 })}</>;
}

export function SourceProvenance({source,publication}:{source:Row;publication:string}) {
 const validation=row(source.technicalvalidation??source.technical_validation);
 const edition=row(source.edition_vigencycheck??source.edition_vigency_check);
 const pages=source.document_pages??source.page_count??source.pdf_pages;
 const integrityPassed=validation.status==='passed';
 const pendingEdition=source.current_normative_application_confirmed===false||String(edition.status??'').startsWith('pending');
 const relationship=row(source.source_relationship);
 const alternative=source.include_in_corpus===false&&['alternative_binary_same_page_content','mirror_distribution_same_artifact'].includes(String(relationship.type));
 if(!source.author&&!pages&&!source.bytes&&!Object.keys(validation).length&&!pendingEdition&&!alternative)return null;
 return <details className="source-provenance"><summary>Procedência e verificação do arquivo</summary>
  <dl className="metadata-grid">
   {source.author?<div><dt>Instituição autora</dt><dd>{string(source.author)}</dd></div>:null}
   {source.catalog_publisher?<div><dt>Catálogo consultado</dt><dd>{string(source.catalog_publisher)}</dd></div>:null}
   {typeof pages==='number'?<div><dt>Páginas do arquivo</dt><dd>{format(pages)}</dd></div>:null}
   {typeof source.bytes==='number'?<div><dt>Tamanho do arquivo</dt><dd>{format(source.bytes)} bytes</dd></div>:null}
   {Object.keys(validation).length?<div><dt>Integridade técnica</dt><dd>{integrityPassed?'Validação técnica registrada':'Validação ainda não concluída'}</dd></div>:null}
   {source.capturedate&&source.capturedate!==source.collected_at?<div><dt>Obtenção deste arquivo</dt><dd>{date(source.capturedate)}</dd></div>:null}
  </dl>
  {pendingEdition?<p>A edição consultada e sua aplicação normativa exigem verificação documental adicional.</p>:null}
  {integrityPassed?<p>A integridade do PDF não comprova a extração completa de suas tabelas, aprendizagens e relações.</p>:null}
  {alternative?<p>Distribuição alternativa do mesmo conteúdo de páginas, sem duplicação de registros.
   {typeof relationship.related_source_id==='string'?<> <Link href={url('/buscar',{publication,source_id:relationship.related_source_id})}>Consultar os registros da fonte correspondente →</Link></>:null}
  </p>:null}
 </details>;
}
