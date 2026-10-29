// Verification-only bounded projection: never assemble cache pages/full JSON.
import {createReadStream} from 'node:fs';
import {once} from 'node:events';
import parserStream from 'stream-json';
import FlexAssembler,{arrayRule} from 'stream-json/utils/flex-assembler.js';
const path=process.argv[2];
if(!path)throw new Error('Cache path required.');
let pending=[];
const assembler=new FlexAssembler({maxDepth:100,arrayRules:[arrayRule({filter:p=>p.length===1&&['items','pages'].includes(p[0]),create:p=>({type:p[0],count:0}),add:(counter,item)=>{counter.count++;if(counter.type==='items')pending.push(item);},finalize:counter=>({count:counter.count})})]});
const parser=createReadStream(path).pipe(parserStream({packValues:true,streamValues:false}));
for await(const token of parser){assembler.consume(token);for(const value of pending){if(!process.stdout.write(JSON.stringify(value)+'\n'))await once(process.stdout,'drain');}pending=[];}
if(!assembler.done)throw new Error('Incomplete cache JSON.');
const meta=assembler.current;
if(!process.stdout.write(JSON.stringify({audit_meta:{source_id:meta.source_id,sha256:meta.sha256,extraction_revision:meta.extraction_revision,page_count:meta.page_count,document_page_count:meta.document_page_count,items:meta.items.count,pages:meta.pages.count,quality:meta.quality,parser_fingerprint:meta.parser_fingerprint?.sha256}})+'\n'))await once(process.stdout,'drain');
