/** Remove only completed, byte-proven temporary exports created by this isolated QA run. */
import assert from 'node:assert/strict';
import {realpath,rm,writeFile,mkdir,readdir,lstat} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {currentQaRun} from './qa-executor';
import {compose,type CleanState} from './qa-production';
import {hashArtifactFile} from './audit-artifact';
export interface QaFileReceipt {path:string;bytes:number;sha256:string;}
export interface QaDownloadReceipt {path:string;bytes:number;sha256:string;job_id:string;created_by_this_run:boolean;}
export async function cleanupVerifiedReimport(state:CleanState,root:string,receipts:QaDownloadReceipt[],expectedFiles:QaFileReceipt[]=receipts){
 const qa=currentQaRun();
 assert.match(state.project,/^curriculos-abertos-clean-[a-z0-9-]+$/);
 const absolute=resolve(root);assert.match(absolute.slice(resolve('var/qa-reimport').length),/^\/[a-f0-9]{12}$/);assert.ok(absolute.startsWith(resolve('var/qa-reimport')+'/'));
 assert.equal(await realpath(absolute),absolute,'QA workdir cannot be a symlink');
 for(const receipt of receipts){assert.ok(resolve(receipt.path).startsWith(absolute+'/'));assert.equal(await hashArtifactFile(receipt.path),receipt.sha256);assert.match(receipt.job_id,/^[a-f0-9-]{36}$/);}
 const own=receipts.filter(receipt=>receipt.created_by_this_run).map(({job_id,bytes,sha256})=>({id:job_id,bytes,sha256}));
 // The expected list comes from download/conversion/task outputs, never a blind
 // inventory of the directory being deleted. Unknown files/directories block cleanup.
 const expected=new Map<string,QaFileReceipt>();const allowedDirectories=new Set<string>([absolute]);
 for(const file of expectedFiles){const path=resolve(file.path);assert.equal(await realpath(path),path,'QA file must not redirect through symlinks');assert.ok(path.startsWith(absolute+'/'));assert.ok(!expected.has(path),'Duplicate cleanup manifest path');assert.match(file.sha256,/^[a-f0-9]{64}$/);assert.ok(Number.isSafeInteger(file.bytes)&&file.bytes>=0);expected.set(path,file);for(let directory=dirname(path);directory!==absolute;directory=dirname(directory)){assert.ok(directory.startsWith(absolute+'/'));allowedDirectories.add(directory);}}
 async function verifyFiles(){const actual=new Set<string>();async function walk(directory:string){assert.ok(allowedDirectories.has(directory),'Unknown directory in QA workdir');for(const entry of await readdir(directory,{withFileTypes:true})){const path=resolve(directory,entry.name);assert.ok(!entry.isSymbolicLink(),'Symlinks block QA cleanup');if(entry.isDirectory())await walk(path);else{assert.ok(entry.isFile(),'Only regular QA files may be removed');const proof=expected.get(path);assert.ok(proof,'Unregistered file in QA workdir');assert.equal((await lstat(path)).size,proof.bytes);assert.equal(await hashArtifactFile(path),proof.sha256);actual.add(path);}}}await walk(absolute);assert.equal(actual.size,expected.size,'Missing manifest file');}
 await verifyFiles();
 return qa.guardCleanup([absolute,...own.map(job=>job.id)],async()=>{
 await verifyFiles();
 const intent={schema_version:1,actor_type:'automated',project:state.project,publication:state.publication,workdir:absolute,receipts,created_at:new Date().toISOString(),scope:'Only files and jobs of this isolated run, after completed download/import/SQL proof',files:[...expected.values()]};
 qa.recordReport('reimport-cleanup-intent',intent);await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/reimport-cleanup-intent.json',JSON.stringify(intent,null,2)+'\n');
 const script=String.raw`const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict'),{Client}=require('pg');
 (async()=>{const input=JSON.parse(process.argv[1]),db=new Client({connectionString:process.env.DATABASE_URL});await db.connect();const cleaned=[];try{assert.equal((await db.query('SELECT current_database() AS name')).rows[0].name,'curriculos_qa');const exportsRoot=fs.realpathSync('/app/var/exports');
 for(const proof of input.jobs){const job=(await db.query('SELECT id,type,status,payload,result FROM jobs WHERE id=$1',[proof.id])).rows[0];assert(job);assert.equal(job.type,'export');assert.equal(job.status,'succeeded');assert.equal(job.payload.query.publication,input.publication);assert.equal(job.result.publication,input.publication);assert.equal(job.result.sha256,proof.sha256);assert.equal(job.result.size,proof.bytes);
 const key=job.result.storage_key;assert(new RegExp('^exports/'+proof.id+'/[0-9]{1,4}-[a-f0-9-]{36}\\.json$').test(key));const file=path.resolve('/app/var',key);assert(fs.realpathSync(file).startsWith(exportsRoot+'/'+proof.id+'/'));assert(!fs.lstatSync(file).isSymbolicLink());assert.equal(fs.statSync(file).size,proof.bytes);const hash=crypto.createHash('sha256');for await(const chunk of fs.createReadStream(file))hash.update(chunk);assert.equal(hash.digest('hex'),proof.sha256);
 const receiptDir='/app/var/qa-cleanup-receipts';fs.mkdirSync(receiptDir,{recursive:true,mode:0o700});const receiptPath=path.join(receiptDir,proof.id+'.json'),receipt={id:proof.id,publication:input.publication,storage_key:key,bytes:proof.bytes,sha256:proof.sha256,verified_at:new Date().toISOString(),phase:'verified'};const persist=()=>fs.writeFileSync(receiptPath,JSON.stringify(receipt)+'\n',{mode:0o600,flush:true});persist();assert.equal((await db.query("DELETE FROM jobs WHERE id=$1 AND type='export' AND status='succeeded' RETURNING id",[proof.id])).rowCount,1);receipt.phase='owned_job_removed';persist();fs.unlinkSync(file);try{fs.rmdirSync(path.dirname(file))}catch(error){if(!['ENOTEMPTY','ENOENT'].includes(error.code))throw error;}receipt.phase='owned_file_removed';persist();cleaned.push({...receipt,receipt_path:receiptPath,removed_at:new Date().toISOString()});}
 console.log(JSON.stringify({cleaned,foreign_or_preexisting_jobs_removed:false}));}finally{await db.end();}})().catch(error=>{console.error(error.message);process.exit(1)});`;
 const server=own.length?JSON.parse(String(compose(state,['exec','-T','worker','node','-e',script,JSON.stringify({publication:state.publication,jobs:own})]))):{cleaned:[],foreign_or_preexisting_jobs_removed:false};
 // This directory was generated under a random private QA token. All canonical originals
 // remain in data/bundles; record/download hashes were proved before this removal.
 await verifyFiles();await rm(absolute,{recursive:true});
 return{...server,workdir_removed:absolute,client_files_sha256_rechecked:true,cleanup_intent:'docs/evidence/reimport-cleanup-intent.json',canonical_artifacts_and_volumes_preserved:true};
 });
}
