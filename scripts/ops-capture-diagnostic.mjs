/** Private immutable context capture; never copies live secrets, caches or raw PDFs. */
import assert from 'node:assert/strict';
import {createHash,randomBytes} from 'node:crypto';
import {constants,createReadStream,existsSync} from 'node:fs';
import {copyFile,mkdir,readdir,lstat,readFile,writeFile,symlink} from 'node:fs/promises';
import {resolve,relative,dirname,join} from 'node:path';
import {sourceTreeHash} from './release-check.ts';
const root=process.cwd(),publication=process.argv[2],expected=process.argv[3];
assert.match(publication||'',/^ca-[a-f0-9]{20}$/);assert.match(expected||'',/^[a-f0-9]{64}$/);
const token=new Date().toISOString().replace(/\D/g,'').slice(0,14)+'-'+randomBytes(3).toString('hex');
const target=resolve('var/diagnostic-context-'+token),receiptPath=resolve('var/diagnostic-context-'+token+'.json');
const report={schema_version:1,started_at:new Date().toISOString(),publication,diagnostic_only:true,target,receipt_path:receiptPath,passed:false,files:0,logical_bytes:0,exclusions:['.env and private configuration','node_modules copy (host symlink ignored by Docker)','raw','extracted','var','Git','other publications'],secrets_copied:false};
const hash=async p=>{const h=createHash('sha256');for await(const c of createReadStream(p))h.update(c);return h.digest('hex');};
const ignored=n=>n==='__pycache__'||n.endsWith('.pyc')||n==='.DS_Store';
async function files(path){const out=[];for(const e of await readdir(path,{withFileTypes:true})){if(ignored(e.name))continue;const p=join(path,e.name);assert(!e.isSymbolicLink(),'Symlink in capture input: '+relative(root,p));if(e.isDirectory())out.push(...await files(p));else if(e.isFile())out.push(p);}return out;}
async function treeHash(path){const h=createHash('sha256');for(const p of(await files(path)).sort())h.update(relative(path,p)).update('\0').update(await hash(p)).update('\0');return h.digest('hex');}
async function copy(p){const rel=relative(root,p);assert(rel&&!rel.startsWith('..')&&!resolve(p).includes('/.env/'));const dest=join(target,rel);const s=await lstat(p);assert(s.isFile()&&!s.isSymbolicLink());await mkdir(dirname(dest),{recursive:true});await copyFile(p,dest,constants.COPYFILE_FICLONE);report.files++;report.logical_bytes+=s.size;return dest;}
try{
 report.source_tree_before=sourceTreeHash(root);report.docs_tree_before=await treeHash(join(root,'docs'));
 await mkdir(target,{recursive:true,mode:0o700});
 for(const dir of ['src','scripts','pipeline','tests','public','docs','LICENSES','data/manifests','data/schema'])if(existsSync(dir))for(const p of await files(resolve(dir)))await copy(p);
 for(const p of ['package.json','package-lock.json','tsconfig.json','next.config.ts','next-env.d.ts','eslint.config.mjs','playwright.config.ts','Dockerfile','compose.yaml','Makefile','.env.example','.gitignore','.dockerignore','README.md','LICENSE','DATA-RIGHTS.md','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md','AGENTS.md','data/coverage-manifest.json'])if(existsSync(p))await copy(resolve(p));
 const manifestPath=resolve('data/bundles/'+publication+'.manifest.json');assert.equal(await hash(manifestPath),expected);const manifest=JSON.parse(await readFile(manifestPath,'utf8'));assert.equal(manifest.id,publication);assert.equal(manifest.national_release_ready,false,'Diagnostic capture must preserve the incomplete BASE label');
 await copy(manifestPath);if(existsSync(manifestPath+'.sha256'))await copy(manifestPath+'.sha256');
 for(const part of manifest.parts){const p=resolve(part.path);assert(relative(root,p).startsWith('data/bundles/'));assert.equal(await hash(p),part.sha256);const dest=await copy(p);assert.equal(await hash(dest),part.sha256);if(existsSync(p+'.sha256'))await copy(p+'.sha256');}
 await writeFile(join(target,'data/bundles/latest.json'),JSON.stringify({id:publication,path:relative(root,manifestPath),format:manifest.format,sha256:expected,item_count:manifest.item_count,relation_count:manifest.relation_count,national_release_ready:false})+'\n');
 await mkdir(join(target,'data/raw'),{recursive:true});await mkdir(join(target,'data/extracted'),{recursive:true});await mkdir(join(target,'var'),{recursive:true,mode:0o700});
 assert(!existsSync(join(target,'.env')),'Live .env must not enter the snapshot');await symlink(join(root,'node_modules'),join(target,'node_modules'),'dir');
 report.source_tree_copy=sourceTreeHash(target);report.source_tree_after=sourceTreeHash(root);report.docs_tree_copy=await treeHash(join(target,'docs'));report.docs_tree_after=await treeHash(join(root,'docs'));
 assert.equal(report.source_tree_copy,report.source_tree_before,'Copied fingerprint mismatch');assert.equal(report.source_tree_after,report.source_tree_before,'Tracked files changed during capture');assert.equal(report.docs_tree_copy,report.docs_tree_before,'Copied documentation/proofs mismatch');assert.equal(report.docs_tree_after,report.docs_tree_before,'Documentation changed during capture');
 assert.equal(await hash(join(target,relative(root,manifestPath))),expected);report.manifest_sha256=expected;report.parts_verified=manifest.parts.length;report.passed=true;
}catch(error){report.error=error.message;process.exitCode=1;}
finally{report.completed_at=new Date().toISOString();await writeFile(receiptPath,JSON.stringify(report,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(report));}
