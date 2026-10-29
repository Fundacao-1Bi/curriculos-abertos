import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp,writeFile,rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { loadBundleFile } from '../src/domain/bundle-file';
const digest=(v:Buffer)=>createHash('sha256').update(v).digest('hex');
test('compressed bundle verifies compressed and decoded checksums with bounded decompression',async()=>{
 const root=await mkdtemp(join(tmpdir(),'ca-bundle-test-'));
 try {
  const decoded=Buffer.from(JSON.stringify({id:'synthetic-loader-test',items:[]})),compressed=gzipSync(decoded);
  const path=join(root,'fixture.json.gz');await writeFile(path,compressed);await writeFile(path+'.sha256',digest(compressed));await writeFile(join(root,'fixture.json.sha256'),digest(decoded));
  const loaded=await loadBundleFile(path,{root,expected:{sha256:digest(compressed),decoded_sha256:digest(decoded),bytes:compressed.length,decoded_bytes:decoded.length}});
  assert.equal(loaded.bundle.id,'synthetic-loader-test');assert.equal(loaded.compressed,true);assert.equal(loaded.decoded_bytes,decoded.length);
  await assert.rejects(()=>loadBundleFile(path,{root,expected:{decoded_sha256:'0'.repeat(64)}}),/Checksum/);
  await assert.rejects(()=>loadBundleFile(path,{root,maxDecodedBytes:10}));
  await writeFile(path+'.sha256','f'.repeat(64));await assert.rejects(()=>loadBundleFile(path,{root}),/Checksum do arquivo/);
 }finally{await rm(root,{recursive:true,force:true});}
});
test('uncompressed bundle requires a matching artifact hash and rejects root traversal',async()=>{
 const root=await mkdtemp(join(tmpdir(),'ca-bundle-test-'));
 try {
  const decoded=Buffer.from('{"id":"uncompressed-test"}'),path=join(root,'fixture.json');await writeFile(path,decoded);await writeFile(path+'.sha256',digest(decoded));
  const loaded=await loadBundleFile(path,{root});assert.equal(loaded.compressed,false);assert.equal(loaded.file_sha256,digest(decoded));
  await assert.rejects(()=>loadBundleFile(path,{root:join(root,'nonexistent')}));
  await assert.rejects(()=>loadBundleFile(path,{root,maxDecodedBytes:5}),/tamanho/);
 }finally{await rm(root,{recursive:true,force:true});}
});
