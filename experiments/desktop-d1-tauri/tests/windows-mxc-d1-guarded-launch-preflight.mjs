// Candidate source-only path and SHA admission for a NONPUBLISHING Windows
// D1 MXC entrypoint. A same-user attacker can still race path replacement;
// this is NOT an immutable file-handle, signature or production trust anchor.
import {createHash} from 'node:crypto';
import {lstatSync,readFileSync,realpathSync} from 'node:fs';
import {basename,dirname,isAbsolute,parse,relative,resolve,sep} from 'node:path';

const fail=(reason)=>{throw Error('D1_MXC_GUARDED_LAUNCH_NO_GO: '+reason)};
export function requirePinnedD1Executable(rawPath,rawSha) {
 if(typeof rawPath!=='string'||!isAbsolute(rawPath)||
    rawPath!==resolve(rawPath)||rawPath.includes('"')||
    /[\r\n\0]/.test(rawPath)||rawPath.startsWith('\\\\?\\')) {
   fail('canonical absolute executable path required');
 }
 if(typeof rawSha!=='string'||!/^[0-9a-fA-F]{64}$/.test(rawSha)) {
   fail('exact SHA-256 is required');
 }
 if(basename(rawPath).toLowerCase()!=='medorigin-desktop-d1-preview.exe'){
   fail('synthetic D1 preview executable filename required');
 }
 const base=parse(rawPath).root;
 let component=base;
 const parts=relative(base,rawPath).split(sep);
 if(parts.length===0||parts.some(v=>!v||v==='.'||v==='..'))fail('invalid path components');
 try {
   for(const part of parts){
     component=resolve(component,part);
     if(lstatSync(component).isSymbolicLink())fail('reparse or symlink path component');
   }
   const canonical=realpathSync.native(rawPath);
   if(canonical.toLowerCase()!==rawPath.toLowerCase())fail('resolved path changed');
   const st=lstatSync(rawPath);
   if(!st.isFile()||st.size===0)fail('not a regular nonempty executable');
   const actual=createHash('sha256').update(readFileSync(rawPath)).digest('hex');
   if(actual!==rawSha.toLowerCase())fail('executable bytes do not match pinned SHA-256');
   return Object.freeze({path:rawPath,sha256:actual,bytes:st.size});
 } catch(e) {
   if(e.message?.startsWith('D1_MXC_GUARDED_LAUNCH_NO_GO:'))throw e;
   fail('executable admission could not be completed');
 }
}
