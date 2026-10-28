/** Source metadata fixtures only; no missing document is fabricated or added to the corpus. */
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {SourceSchema} from '../src/mcp/contracts';
import {validateBundle} from '../src/domain/publication';
import type {Bundle,Source} from '../src/shared/contracts';

const source:Source={id:'isolated-unknown-artifact',uf:'BR',title:'Isolated source contract fixture',issuer:'Synthetic test only',official_url:'https://example.invalid/catalog',artifact_url:null,stages:['EF'],components:[],edition:null,document_date:null,homologation_date:null,application_period:null,document_type:'test_fixture',normative_parts:['Unknown mandatory document'],redistribution:'Test only',collected_at:null,sha256:null,local_path:null,status:'research_pending'};
const schemaPin=(version:string)=>({schema_version:version,schema_path:`data/schema/${version}.json`,schema_sha256:createHash('sha256').update(readFileSync(`data/schema/${version}.json`)).digest('hex')});
const snapshot=(row:Source):Bundle=>({id:'isolated-source-contract',...schemaPin('1.1.0'),created_at:'2026-10-28T00:00:00Z',extraction_revision:'test',mapping_revision:'test',sources:[row],items:[],relations:[],coverage:[],changelog:[]});

test('unknown artifact address remains explicit null in transport and immutable import validation',()=>{
 const result=SourceSchema.parse(source);assert.equal(result.artifact_url,null);assert.equal(result.official_url,source.official_url);assert.equal(result.sha256,null);assert.equal(result.status,'research_pending');
 assert.doesNotThrow(()=>validateBundle(snapshot(result as Source)));
 assert.throws(()=>validateBundle({...snapshot(result as Source),...schemaPin('1.0.0')}),/(histórico|schema)/i);
 const known={...source,artifact_url:'https://example.invalid/document.pdf'};assert.doesNotThrow(()=>validateBundle(snapshot(known)));assert.equal(SourceSchema.parse(known).artifact_url,known.artifact_url);
});

test('unknown URL does not authorize omitting the field or using executable/non-HTTP addresses',()=>{
 const absent={...source};Reflect.deleteProperty(absent,'artifact_url');assert.equal(SourceSchema.safeParse(absent).success,false);assert.throws(()=>validateBundle(snapshot(absent)),/artifact_url/);
 for(const artifact_url of ['', 'javascript:alert(1)','file:///private/document.pdf','ftp://example.invalid/document.pdf'])assert.throws(()=>validateBundle(snapshot({...source,artifact_url})),/URL|schema|pattern/i);
 assert.throws(()=>validateBundle(snapshot({...source,official_url:''})),/URL|schema|pattern/i);
});
