import { readFile, stat, realpath, readdir } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import type { Bundle } from '../shared/contracts';
export interface BundleFileExpected {sha256?:string;bytes?:number;decoded_sha256?:string;decoded_bytes?:number;}
export interface BundleFileOptions {root?:string;expected?:BundleFileExpected;maxFileBytes?:number;maxDecodedBytes?:number;schemaRoot?:string;}
function bound(value:number|undefined,fallback:number):number {const selected=value??fallback;if(!Number.isSafeInteger(selected)||selected<1||selected>2_147_483_647)throw Error('Limite de tamanho de bundle inválido.');return selected;}
const sha=(value:Buffer)=>createHash('sha256').update(value).digest('hex');
function hash(value:unknown):value is string{return typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);}
async function sidecar(path:string) {const expected=(await readFile(path+'.sha256','utf8')).trim().split(/\s/)[0];if(!hash(expected))throw Error('Sidecar SHA-256 inválido.');return expected;}
/** Verifies compressed bytes before bounded decompression, then verifies the decoded artifact independently. */
export async function loadBundleFile(filename:string,options:BundleFileOptions={}) {
 const root=await realpath(resolve(options.root??'data/bundles')),path=await realpath(resolve(filename));
 if(!path.startsWith(root+sep)||!/\.json(?:\.gz)?$/.test(path))throw Error('Bundle precisa ser .json ou .json.gz dentro de data/bundles.');
 const compressed=path.endsWith('.gz');
 const maxFileBytes=bound(options.maxFileBytes,Number(process.env.DATA_MAX_FILE_BYTES??268435456));
 const maxDecodedBytes=bound(options.maxDecodedBytes,Number(process.env.DATA_MAX_DECODED_BYTES??536870912));
 const info=await stat(path);if(!info.isFile()||info.size>(compressed?maxFileBytes:maxDecodedBytes))throw Error('Bundle excede limite de tamanho de arquivo.');
 if(options.expected?.bytes!==undefined&&info.size!==options.expected.bytes)throw Error('Tamanho do bundle difere do manifesto.');
 const expectedFileHash=await sidecar(path);
 if(options.expected?.sha256!==undefined&&options.expected.sha256!==expectedFileHash)throw Error('Checksum do manifesto diverge do sidecar.');
 const raw=await readFile(path);const fileHash=sha(raw);
 if(fileHash!==expectedFileHash)throw Error('Checksum do arquivo divergente.');
 // maxOutputLength rejects gzip bombs before unbounded allocation.
 const decoded=compressed?gunzipSync(raw,{maxOutputLength:maxDecodedBytes}):raw;
 if(decoded.length>maxDecodedBytes)throw Error('Bundle decodificado excede limite.');
 const decodedHash=compressed?sha(decoded):fileHash;
 if(compressed){const expectedDecoded=options.expected?.decoded_sha256??await sidecar(path.slice(0,-3));if(!hash(expectedDecoded)||expectedDecoded!==decodedHash)throw Error('Checksum do JSON decodificado divergente.');}
 if(options.expected?.decoded_sha256!==undefined&&options.expected.decoded_sha256!==decodedHash)throw Error('Checksum decodificado diverge do manifesto.');
 if(options.expected?.decoded_bytes!==undefined&&options.expected.decoded_bytes!==decoded.length)throw Error('Tamanho decodificado diverge do manifesto.');
 const bundle=JSON.parse(decoded.toString('utf8')) as Bundle;
 return{bundle,path,compressed,file_sha256:fileHash,decoded_sha256:decodedHash,bytes:raw.length,decoded_bytes:decoded.length};
}
export async function resolveBundleFile(explicit?:string,rootInput='data/bundles') {
 const root=resolve(rootInput);let latest:(BundleFileExpected&{path?:string})|undefined;
 if(!explicit){try{latest=JSON.parse(await readFile(resolve(root,'latest.json'),'utf8'));}catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw Error('Ponteiro latest.json inválido.');}}
 const fallback=explicit||latest?.path?undefined:(await readdir(root)).filter(x=>/\.json(?:\.gz)?$/.test(x)&&!/latest|manifest|schema|checksum/.test(x)).sort().at(-1);
 const filename=explicit??latest?.path??(fallback?resolve(root,fallback):undefined);
 if(!filename)throw Error('Nenhuma publicação entregue em data/bundles.');
 return{path:resolve(filename),expected:explicit?undefined:latest,root};
}
