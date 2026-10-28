/** Synthetic fixtures in this file are isolated to a disposable *_test database. Never a published corpus. */
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { migrate } from '../scripts/migrate';
import { pool } from '../src/db/client';
import { importBundle,setDefaultPublication,validateBundle } from '../src/domain/publication';
import { searchLearnings,getLearning,batchLearnings,listUfs,listCurricula,getStructure,listSources,getSource,listPublications,coverage,listRelations,panorama,compare,analyses,exportData } from '../src/domain/service';
import { csvCell } from '../src/domain/normalize';
import { testDatabaseName } from './domain-safety';
import type { Bundle,Learning,Source } from '../src/shared/contracts';
const allowed=process.env.DOMAIN_INTEGRATION_TEST==='1';
const source=(uf:'BR'|'SP'|'RJ'):Source=>({id:'test-source-'+uf,uf,title:'TEST FIXTURE '+uf,issuer:'Synthetic isolated test',official_url:'https://example.org/test',artifact_url:'https://example.org/test.pdf',stages:['EF'],components:['Matemática'],edition:'test-1',document_date:null,homologation_date:null,application_period:null,document_type:'test_fixture',normative_parts:['test'],redistribution:'Test only',collected_at:null,sha256:null,local_path:null,status:'test'});
const item=(id:string,uf:'BR'|'SP'|'RJ',code:string,years:number[]|null,text:string):Learning=>({id,curriculum_id:'test-source-'+uf,source_id:'test-source-'+uf,uf,code,text,normalized_text:'',editorial_note:null,kind:'habilidade',parent_id:null,positions:[{stage:'EF',component:'Matemática',area:null,years,year_label:years?'6º ao 9º':null,age_group:null,period:null}],evidence:[{source_id:'test-source-'+uf,page:1,printed_page:null,section:null,excerpt:text}],extraction_revision:'test'});
const bundle:Bundle={id:'test-publication-1',schema_version:'1',created_at:'2026-10-28T00:00:00Z',extraction_revision:'test-1',mapping_revision:'test-1',sources:[source('BR'),source('SP'),source('RJ')],items:[item('br-a','BR','EF69MA01',[6,7,8,9],'Relações de proporção e números.'),item('sp-a','SP','EF69MA01-A',[6,7,8,9],'Relações de proporção na alimentação.'),item('sp-b','SP','SP69MA01*',[6,7,8,9],'Analisar frações e operações.'),item('rj-a','RJ','EF69MA01',null,'Estudar relações e proporções.')],relations:[{id:'r1',members:[{item_id:'sp-a',role:'source',scope:'part'},{item_id:'sp-b',role:'source',scope:'part'},{item_id:'br-a',role:'target',scope:'reference'}],relation_type:'desdobramento',origin:'source_declaration',technical_validation_status:'verified',pedagogical_review_status:'not_reviewed',publication_status:'published',method:'TEST',evidence:[]},{id:'r2',members:[{item_id:'rj-a',role:'source',scope:'part'},{item_id:'br-a',role:'target',scope:'reference'}],relation_type:'referencia_nacional',origin:'source_declaration',technical_validation_status:'verified',pedagogical_review_status:'not_reviewed',publication_status:'published',method:'TEST',evidence:[]}],coverage:[{uf:'SP',stage:'EF',ready:false,reconciled:false,expected_parts:2,processed_parts:1}],changelog:[]};
before(async()=>{if(!allowed)return;const name=testDatabaseName(process.env.DATABASE_URL);const current=await pool.query('SELECT current_database() AS name');if(current.rows[0]?.name!==name)throw Error('Connected database differs from owned test target.');await pool.query('DROP SCHEMA public CASCADE');await pool.query('CREATE SCHEMA public');await migrate();await importBundle(bundle,{makeDefault:true});});
after(async()=>{await pool.end();});
test('bundle validation rejects duplicate IDs, dangling sources and missing localizers',()=>{validateBundle(bundle);assert.throws(()=>validateBundle({...bundle,items:[...bundle.items,bundle.items[0]]}),/duplicado/);assert.throws(()=>validateBundle({...bundle,items:[{...bundle.items[0],uf:'SP'}]}),/UF divergente/);assert.throws(()=>validateBundle({...bundle,items:[{...bundle.items[0],positions:[{...bundle.items[0].positions[0],stage:'EM'}]}]}),/Etapa divergente/);assert.throws(()=>validateBundle({...bundle,items:[{...bundle.items[0],pedagogical_review_status:'human_reviewed'}]}),/sem evento humano/);assert.throws(()=>validateBundle({...bundle,items:[{...bundle.items[0],source_id:'missing'}]}),/não encontrada/);assert.throws(()=>validateBundle({...bundle,items:[{...bundle.items[0],evidence:[{source_id:'test-source-BR',page:null,printed_page:null,section:null,excerpt:'test'}]}]}),/Localizador/);});
test('CSV neutralizes executable formulas and quotes without altering canonical JSON',()=>{assert.equal(csvCell('=SUM(1,2)'),`"'=SUM(1,2)"`);assert.equal(csvCell('a"b'),`"a""b"`);assert.equal(bundle.items[0].text,'Relações de proporção e números.');});
test('real PostgreSQL contracts and filters',{skip:!allowed},async()=>{
 const exact=await searchLearnings({q:'EF69MA01',limit:1});assert.equal(exact.data[0].code,'EF69MA01');assert.equal(exact.total,3);assert.match(String(exact.next),/publication=test-publication-1/);
 const accent=await searchLearnings({q:'proporcao'});assert.equal(accent.total,2);
 const year=await searchLearnings({year:'7',uf:'SP'});assert.equal(year.total,2);assert.deepEqual(year.data[0].positions[0].years,[6,7,8,9]);
 assert.equal((await searchLearnings({year:'7',uf:'RJ'})).total,0);assert.equal((await searchLearnings({year:'7',uf:'RJ',include_unknown_positions:true})).total,1);
 const suffix=await searchLearnings({q:'SP69MA01*'});assert.equal(suffix.data[0].code,'SP69MA01*');
 assert.equal((await getLearning('sp-a')).data.text,bundle.items[1].text);
 const batch=await batchLearnings(['sp-a','missing',3]);assert.deepEqual(batch.data.map(x=>x.status),['found','not_found','invalid']);
 await assert.rejects(()=>searchLearnings({limit:101}),/limite/);await assert.rejects(()=>getLearning('missing'),/inexistente/);
 const ufs=await listUfs();assert.equal(ufs.data.length,27);assert.equal(ufs.data.find(x=>x.uf==='SP')?.ready,false);assert.equal(ufs.data.find(x=>x.uf==='SP')?.source_count,1);
 assert.equal((await listCurricula()).data.length,3);assert.equal((await getStructure('test-source-SP')).data[0].item_count,2);
 assert.equal((await listSources()).total,3);assert.equal((await getSource('test-source-SP')).data.uf,'SP');assert.equal((await coverage()).total,1);
 assert.equal((await listRelations({item_id:'br-a'})).total,2);
 const pano=await panorama('br-a');assert.equal(pano.data.ufs.length,27);assert.equal(pano.data.ufs.find(x=>x.uf==='SP')?.total,2);assert.equal(pano.data.ufs.find(x=>x.uf==='AC')?.status,'dados_insuficientes');
 const cmp=await compare({ufs:['SP','RJ']});assert.equal(cmp.data.comparable,true);assert.equal(cmp.data.shared_references.length,1);await assert.rejects(()=>compare({ufs:['SP','SP']}),/distintas/);
 const stats=await analyses();assert.equal(stats.data.unique_items,4);assert.equal(stats.data.relations,2);assert.equal(stats.data.position_occurrences,4);
 const exp=await exportData();const exported=JSON.parse(exp.data.content);assert.equal((await importBundle(exported)).already_imported,true);assert.equal(exported.items.length,4);assert.equal(exported.relations.length,2);assert.equal(exported.sources.length,3);
 const cut=JSON.parse((await exportData({uf:'SP'})).data.content);assert.equal(cut.export_manifest.matched_item_count,2);assert.equal(cut.items.length,3);assert.equal(cut.relations.length,1);assert.deepEqual(cut.export_manifest.support_item_ids,['br-a']);validateBundle(cut);assert.notEqual(cut.id,bundle.id);assert.equal(cut.parent_publication,bundle.id);assert.equal((await importBundle(cut,{makeDefault:false})).item_count,3);
 const csv=await exportData({},'csv');assert.match(csv.data.content,/record_type,id,payload_json/);assert.match(csv.data.content,/source/);assert.match(csv.data.content,/positions/);
 assert.equal(stats.data.matrix.rows.length,1);assert.equal(stats.data.matrix.rows[0].ufs.length,27);assert.equal(stats.data.matrix.rows[0].ufs.find(x=>x.uf==='SP')?.item_count,2);
 const report=JSON.parse((await exportData({view:'comparison',ufs:'SP,RJ',limit:1})).data.content);assert.equal(report.data.columns[0].items.length,2);assert.equal(report.export_manifest.unpaginated,true);
 const panoExport=JSON.parse((await exportData({view:'panorama',item_id:'br-a',limit:1})).data.content);assert.equal(panoExport.data.ufs.find((x:{uf:string})=>x.uf==='SP').items.length,2);
 assert.equal((await searchLearnings({national_id:'br-a',uf:'SP'})).total,2);assert.equal((await listSources({q:'fixture'})).total,3);
});
test('immutable import, snapshot pinning and auditable rollback',{skip:!allowed},async()=>{
 assert.equal((await importBundle(bundle,{makeDefault:true})).already_imported,true);
 await assert.rejects(()=>importBundle({...bundle,created_at:'2026-10-28T01:00:00Z'}),/já existe/);
 await assert.rejects(()=>pool.query("UPDATE items SET text='corrupted' WHERE id='sp-a'"),/immutable/);
 const next={...bundle,id:'test-publication-2',created_at:'2026-10-28T02:00:00Z',items:bundle.items.map(i=>i.id==='sp-a'?{...i,text:'Revisão de transcrição.'}:i)};
 await importBundle(next,{makeDefault:true});assert.equal((await getLearning('sp-a')).data.text,'Revisão de transcrição.');assert.equal((await getLearning('sp-a',{publication:'test-publication-1'})).data.text,bundle.items[1].text);
 await setDefaultPublication('test-publication-1',{id:'test-runner',actor_type:'automated',reason:'Controlled rollback test'});assert.equal((await getLearning('sp-a')).publication,'test-publication-1');assert.equal((await listPublications()).total,3);
 const events=await pool.query("SELECT actor_type FROM publication_events WHERE actor_id='test-runner'");assert.equal(events.rows[0].actor_type,'automated');
 await migrate();
});

test('positionless items remain unknown and enter year filters only through explicit option and documented source context',{skip:!allowed},async()=>{
 const unknown={...item('sp-positionless','SP','UNCLASSIFIED',null,'Seção com posicionamento não identificado.'),code:null,positions:[],kind:'secao_normativa',position_unknown_reason:'Posicionamento não identificado na extração.'};
 const edition={...bundle,id:'test-unpositioned-publication',items:[...bundle.items,unknown]};await importBundle(edition,{makeDefault:false});
 const base={publication:edition.id,uf:'SP',year:'7'};
 assert.equal((await searchLearnings(base)).total,2);
 const included=await searchLearnings({...base,include_unknown_positions:true});assert.equal(included.total,3);assert.deepEqual(included.data.find(x=>x.id===unknown.id)?.positions,[]);
 assert.equal((await searchLearnings({...base,stage:'EF',include_unknown_positions:true})).total,3);
 assert.equal((await searchLearnings({...base,stage:'EM',include_unknown_positions:true})).total,0);
 assert.equal((await searchLearnings({...base,component:'Matemática',include_unknown_positions:true})).total,3);
 assert.equal((await searchLearnings({...base,area:'Linguagens',include_unknown_positions:true})).total,0);
});

test('destructive integration guard validates the database path rather than credentials/host substrings',()=>{assert.equal(testDatabaseName('postgresql://u:p@localhost/curriculum_test_012345abcdef'),'curriculum_test_012345abcdef');for(const url of ['postgresql://curriculum_test:p@localhost/production','postgresql://u:curriculum_test@localhost/production','postgresql://u:p@curriculum_test.example/production','postgresql://u:p@localhost/production?database=curriculum_test','postgresql://u:p@localhost/curriculum_test_other_team'])assert.throws(()=>testDatabaseName(url),/Refusing/);});

test('real sharded import verifies every part before atomic promotion and streams self-contained snapshots',{skip:!allowed},async()=>{
 const {mkdir,mkdtemp,writeFile,readFile,rm}=await import('node:fs/promises');const {resolve,relative}=await import('node:path');const {gzipSync}=await import('node:zlib');const {createHash}=await import('node:crypto');
 const {importShardedManifest,verifyShardedManifest}=await import('../src/domain/shards');const {streamExportToFile}=await import('../src/domain/stream-exports');
 await mkdir('var',{recursive:true});const root=await mkdtemp(resolve('var','domain-shard-test-'));const digest=(b:Buffer|string)=>createHash('sha256').update(b).digest('hex');
 try{
  const {items:fixtureItems,relations:fixtureRelations,...metadata}=bundle;
  const part=async(kind:'items'|'relations',values:unknown[],label:string)=>{const decoded=Buffer.from(values.map(v=>JSON.stringify(v)).join('\n')+'\n');const raw=gzipSync(decoded);const path=resolve(root,label+'.jsonl.gz');await writeFile(path,raw);return{kind,path:relative(process.cwd(),path),sha256:digest(raw),bytes:raw.length,decoded_sha256:digest(decoded),decoded_bytes:decoded.length,records:values.length};};
  const manifest={...metadata,id:'test-sharded-publication',format:'curriculos-abertos/sharded-v1' as const,item_count:fixtureItems.length,relation_count:fixtureRelations.length,parts:[await part('items',fixtureItems,'items'),await part('relations',fixtureRelations,'relations')]};
  assert.deepEqual(await verifyShardedManifest(manifest,root),{item_count:4,relation_count:2,source_count:3});
  const hash=digest(JSON.stringify(manifest));assert.equal((await importShardedManifest(manifest,hash,{root,makeDefault:false})).already_imported,false);assert.equal((await importShardedManifest(manifest,hash,{root})).already_imported,true);
  const stored=await pool.query("SELECT storage_format,payload ? 'items' AS embedded_items,item_count FROM publications WHERE id=$1",[manifest.id]);assert.equal(stored.rows[0].storage_format,'relational-v1');assert.equal(stored.rows[0].embedded_items,false);assert.equal(stored.rows[0].item_count,4);
  assert.equal((await getLearning('sp-a',{publication:manifest.id})).data.text,bundle.items[1].text);
  const exported=await streamExportToFile({publication:manifest.id},'json',resolve(root,'snapshot.json'));const bytes=await readFile(resolve(root,'snapshot.json'));assert.equal(exported.sha256,digest(bytes));assert.equal(exported.size,bytes.length);const decoded=JSON.parse(bytes.toString());validateBundle(decoded);assert.equal(decoded.items.length,4);assert.equal(decoded.relations.length,2);assert.equal((await importBundle(decoded)).already_imported,true);
  const csv=await streamExportToFile({publication:manifest.id,uf:'SP'},'csv',resolve(root,'snapshot.csv'));assert.equal(csv.record_count,2);assert.match(await readFile(resolve(root,'snapshot.csv'),'utf8'),/record_type,id,payload_json/);
  const broken={...manifest,id:'test-sharded-invalid',parts:[manifest.parts[0],await part('relations',[{...fixtureRelations[0],members:[{item_id:'absent',role:'source',scope:'test'},{item_id:'br-a',role:'target',scope:'test'}]},fixtureRelations[1]],'broken')]};
  await assert.rejects(()=>importShardedManifest(broken,digest(JSON.stringify(broken)),{root,makeDefault:true}),/Membro inválido/);assert.equal((await pool.query('SELECT count(*)::int count FROM publications WHERE id=$1',[broken.id])).rows[0].count,0);
  await writeFile(resolve(root,'items.jsonl.gz'),'tampered');await assert.rejects(()=>importShardedManifest(manifest,hash,{root}),/Tamanho|Checksum/);
 }finally{await rm(root,{recursive:true,force:true});}
});

test('curation clones relational snapshots without embedding collections or turning publication approval into pedagogy',{skip:!allowed},async()=>{
 const {validateRelationalRevision,prepareRelationalRevision}=await import('../src/domain/revisions');
 const meta={id:'test-relational-revision',created_at:'2026-10-28T05:00:00Z',extraction_revision:'test-curation',mapping_revision:'test-curation'};
 const changes=[{entity:'item' as const,record_id:'sp-a',text:'Transcrição corrigida para teste isolado.',reason:'Conferência técnica no teste isolado.',actor_id:'automated-test-runner',actor_type:'automated' as const,at:'2026-10-28T05:00:00Z'},{entity:'relation' as const,record_id:'r1',decision:'accept' as const,review_type:'publication' as const,reason:'Decisão de publicação automatizada de teste.',actor_id:'automated-test-runner',actor_type:'automated' as const,at:'2026-10-28T05:00:00Z'}];
 const validation=await validateRelationalRevision(bundle.id,changes,meta);const result=await prepareRelationalRevision(bundle.id,changes,meta,{sha256:validation.sha256});assert.equal(result.item_count,4);assert.equal((await getLearning('sp-a',{publication:meta.id})).data.text,changes[0].text);assert.equal((await getLearning('sp-a',{publication:bundle.id})).data.text,bundle.items[1].text);
 const relation=(await listRelations({publication:meta.id,item_id:'sp-a'})).data[0];assert.equal(relation.origin,'source_declaration');assert.equal(relation.pedagogical_review_status,'not_reviewed');assert.equal(relation.publication_status,'published');
 const record=(await pool.query("SELECT storage_format,payload ? 'items' AS embedded FROM publications WHERE id=$1",[meta.id])).rows[0];assert.equal(record.storage_format,'relational-v1');assert.equal(record.embedded,false);
 const exported=JSON.parse((await exportData({publication:meta.id})).data.content);assert.equal((await importBundle(exported)).already_imported,true);
});


test('documented code aliases preserve canonical glyphs and hierarchy supports direct child navigation',{skip:!allowed},async()=>{
 const node={...item('sp-node','SP','TECHNICAL-NODE',[6,7,8,9],'Unidade temática documentada.'),code:null,kind:'unidade_tematica'};
 const aliased={...item('sp-alias','SP','EF05CO011',[5],'Código com grafia original preservada.'),code_aliases:['EF05CO11']};
 const edition={...bundle,id:'test-hierarchy-and-aliases',items:[...bundle.items.map(i=>i.id==='sp-a'?{...i,parent_id:node.id}:i),node,aliased]};await importBundle(edition,{makeDefault:false});
 const found=await searchLearnings({publication:edition.id,q:'ef05co11'});assert.equal(found.total,1);assert.equal(found.data[0].code,'EF05CO011');assert.deepEqual(found.data[0].code_aliases,['EF05CO11']);
 const children=await searchLearnings({publication:edition.id,parent_id:node.id});assert.equal(children.total,1);assert.equal(children.data[0].id,'sp-a');
 const structure=await getStructure('test-source-SP',{publication:edition.id});const hierarchy=structure.hierarchy as {nodes:{id:string;child_count:number;learning_child_count:number}[]};assert.equal(hierarchy.nodes.find(n=>n.id===node.id)?.child_count,1);assert.equal(hierarchy.nodes.find(n=>n.id===node.id)?.learning_child_count,1);
 const cyclic={...bundle,items:bundle.items.map(i=>i.id==='sp-a'?{...i,parent_id:'sp-b'}:i.id==='sp-b'?{...i,parent_id:'sp-a'}:i)};assert.throws(()=>validateBundle(cyclic),/cíclica/);
});
