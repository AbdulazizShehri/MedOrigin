// Backend-neutral SOURCE-ONLY receipt identity contract (EGM T2, unpublished).
// No native observer, WFP, packet, clinical, signing or release verdict here.
const reject=(reason)=>{throw Error('D1_EGM_SOURCE_RECEIPT_NO_GO: '+reason)};
const sourcePattern=/^[0-9a-f]{40}$/;
const digestPattern=/^[0-9a-f]{64}$/;
const receiptKeys=['schemaVersion','status','scope','sourceSha','exeSha256','receiptId'];
const expectedKeys=['sourceSha','exeSha256'];

function exactPlainValues(value,keys,kind){
 if(value===null||typeof value!=='object'||Array.isArray(value))reject(kind+' is not a plain JSON object');
 const proto=Object.getPrototypeOf(value);
 if(proto!==Object.prototype&&proto!==null)reject(kind+' has a nonplain prototype');
 const names=Reflect.ownKeys(value);
 if(names.length!==keys.length||names.some(k=>typeof k!=='string'||!keys.includes(k)))
  reject(kind+' has missing, unknown or symbol keys');
 const descriptors=Object.getOwnPropertyDescriptors(value);
 const out=Object.create(null);
 for(const key of keys){
  const d=descriptors[key];
  if(!d||!Object.hasOwn(d,'value')||!d.enumerable)reject(kind+' has missing or accessor keys');
  const v=d.value;
  if(v!==null&&typeof v==='object')reject(kind+' has nested noncanonical values');
  out[key]=v;
 }
 return out;
}

function assessCanonicalReceipt(receipt,expected,seenIds){
 const r=exactPlainValues(receipt,receiptKeys,'receipt');
 const e=exactPlainValues(expected,expectedKeys,'expected identity');
 if(!(seenIds instanceof Set)||Object.getPrototypeOf(seenIds)!==Set.prototype)
  reject('history must be a plain caller-owned Set');
 if(r.schemaVersion!==1||r.status!=='SOURCE_ONLY'||r.scope!=='synthetic-source-only')
  reject('unsupported schema, status or scope; no security/release PASS is accepted');
 if(typeof r.sourceSha!=='string'||!sourcePattern.test(r.sourceSha)||
    typeof r.exeSha256!=='string'||!digestPattern.test(r.exeSha256)||
    typeof r.receiptId!=='string'||!digestPattern.test(r.receiptId)||
    typeof e.sourceSha!=='string'||!sourcePattern.test(e.sourceSha)||
    typeof e.exeSha256!=='string'||!digestPattern.test(e.exeSha256))
  reject('noncanonical source, binary or receipt identity');
 if(r.sourceSha!==e.sourceSha||r.exeSha256!==e.exeSha256)
  reject('receipt identity does not match pinned expected source and binary');
 // The accepted wire shape is tiny. Explicitly bound UTF-8 length before
 // returning; never serialize unknown fields, executable output or host data.
 let bytes;
 try{bytes=Buffer.byteLength(JSON.stringify(r),'utf8')}
 catch{reject('unserializable receipt')}
 if(bytes>32*1024)reject('oversized receipt');
 if(Set.prototype.has.call(seenIds,r.receiptId))reject('replayed receipt identifier');
 // The caller owns append-only persistence; no mutation or signing is implied.
 return Object.freeze({verdict:'SOURCE_SCHEMA_VALID_ONLY',sourceSha:r.sourceSha,
   exeSha256:r.exeSha256,receiptId:r.receiptId});
}

// Normalize hostile Proxy/revoked-object failures to the same fail-closed
// classification; caller-supplied objects are never an approval authority.
export function assessSourceOnlyReceipt(receipt,expected,seenIds){
 try{return assessCanonicalReceipt(receipt,expected,seenIds)}
 catch(error){
  if(error instanceof Error&&error.message.startsWith('D1_EGM_SOURCE_RECEIPT_NO_GO:'))throw error;
  reject('malformed or unsupported input object');
 }
}
