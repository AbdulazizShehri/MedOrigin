// Nonpublishing author-side plan/lineage checks, not Goldfish review,
// native MXC execution, packet/WFP/DNS capture or release certification.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const designs=resolve(root,'docs/designs');
const names={
  plan:'D1_EGM_EXECUTION_PLAN_V2.md',
  concept:'D1_NETWORK_CONFINEMENT_EGM.md',
  packet:'D1_EGM_COLD_REVIEW_PACKET.md',
  index:'SITEMAP.md'
};
const load=name=>readFileSync(resolve(designs,names[name]),'utf8');
const d=Object.fromEntries(Object.keys(names).map(k=>[k,load(k)]));
const source807='03498d7856cf15e32e3a5f627a778000365a08cc';
const source808='a7cdbdf4d498f1a75017333a20f6ae1db4a476b1';
const nativeSha='ed4a30167c4a8a6bb8b4af30ce86dee0607f3494ee6e5d84eeed13f7da2a9381';
const upstream='403d8881d62022490637d740657b33f01e321ea8';
const hasAll=(s,terms)=>terms.forEach(term=>assert.ok(s.includes(term),'Missing: '+term));
function requireFailClosedPlan(plan){
 hasAll(plan,[
  'DRAFT / NOT APPROVED','Goldfish review: NOT RUN',
  'Implementation readiness: PARTIAL','Release: NO-GO',
  '#662','E_NOTIMPL','SENT23',upstream,
  source807,source808,nativeSha,
  'G0 Source and build identity','G1 Real app function',
  'G2 Runtime admission and lifecycle',
  'G3 Independent observer sensitivity',
  'G4 Ownership and broker attribution',
  'G5 Protocol and policy completeness',
  'G6 Crash/restart/upgrade regression',
  'G7 Independent review and release',
  'T0 — Evidence reconciliation','T1 — Observer capability inventory',
  'T2 — Offline evidence-schema/adversarial verdict',
  'T3 — Independent Goldfish and owner architecture decision',
  'T4 — Approved disposable-host packet/OS experiment',
  'T5 — Verified policy bound to mandatory launcher',
  'T6 — Cross-platform and release governance',
  'NOT implementation-ready','HOLD-A','HOLD-B',
  'positive control','blocked-control','dropped',
  'broker','DNS','UDP','IPv6','Source drift triggers',
  'T0–T2 may proceed','T3–T6 remain'
 ]);
 assert.match(plan,/native #807 success[^\n]*older/i);
 assert.match(plan,/#808 remains G1\/G2 \*\*NOT_RUN\*\*/);
 assert.match(plan,/Goldfish review: NOT RUN/);
 assert.match(plan,/one NOT_RUN or BLOCKED release-critical gate keeps \*\*RELEASE NO-GO\*\*/);
 assert.match(plan,/No observer can declare a pass unless it demonstrates visibility/);
 assert.match(plan,/not\*\* populate observational fields/i);
}
test('v2 source-bound plan explicitly retains NO-GO, immutable lineage and stage split',()=>{
 assert.doesNotThrow(()=>requireFailClosedPlan(d.plan));
});
test('review and implementation stages cannot pretend missing approvals are green',()=>{
 hasAll(d.plan,['human sign-off','independent','signed decision','nonprivileged read-only',
   'No system settings changed','No uncontained fallback','not a G3–G7 pass']);
 hasAll(d.packet,['Review state: NOT RUN','Approval: NONE',
   'STOP the Goldfish review','D1_EGM_EXECUTION_PLAN_V2.md',
   'no independent native Windows replay','implementation-readiness standard']);
 hasAll(d.index,['D1_EGM_EXECUTION_PLAN_V2.md','DRAFT','Goldfish NOT RUN','NO-GO']);
 hasAll(d.concept,['## 10. 2026-11-01 execution-plan v2',
   'D1_EGM_EXECUTION_PLAN_V2.md','NOT RUN','OPEN / NO-GO']);
});
test('alternative A and B remain undecided, C rejected and global firewall prohibited',()=>{
 hasAll(d.plan,['A.','B.','C.','D.','UNDECIDED',
   'REJECTED as security proof','PROHIBITED']);
 assert.match(d.plan,/Owner\/security decision record required before implementation/);
 assert.match(d.plan,/Any engineer asked to choose an identity/);
});
test('source only tasks name exact future paths and adversarial tests',()=>{
 hasAll(d.plan,[
  'windows-d1-observer-capability-inventory.mjs',
  'windows-d1-observer-capability-inventory.test.mjs',
  'windows-d1-egm-evidence-verdict.mjs',
  'windows-d1-egm-evidence-verdict.test.mjs',
  'missing/duplicate fields','forged capability','stale SHA',
  'missing/mismatched SHA','unknown broker','RELEASE_GO'
 ]);
});
test('all local Markdown targets in v2 plan and edited context files resolve',()=>{
 for(const [name,body] of Object.entries(d)){
  const file=resolve(designs,names[name]);
  for(const match of body.matchAll(/\[[^\]]+\]\(([^)]+)\)/g)){
   const link=match[1];
   if(/^https?:\/\//.test(link)||link.startsWith('#'))continue;
   const local=resolve(dirname(file),decodeURIComponent(link.split('#')[0]));
   assert.ok(existsSync(local),name+': broken link '+link);
  }
 }
});
test('reject plan mutations that erase the fail-closed decision and evidence boundaries',()=>{
 for(const changed of [
  d.plan.replace('Goldfish review: NOT RUN','Goldfish review: PASS'),
  d.plan.replace('Release: NO-GO','Release: GO'),
  d.plan.replace(source808,'8'.repeat(40)),
  d.plan.replace(source807,'7'.repeat(40)),
  d.plan.replace('G3 Independent observer sensitivity','G3 No observer needed'),
  d.plan.replace('T3–T6 remain','T3–T6 are completed'),
  d.plan.replace('HOLD-A','READY-A'),
  d.plan.replace('E_NOTIMPL','CAPTURE_PASSED')
 ])assert.throws(()=>requireFailClosedPlan(changed));
});
test('documentation cannot be mistaken for actual Goldfish or independent OS proof',()=>{
 assert.match(d.plan,/This document improves the plan, not the security status/);
 assert.match(d.plan,/not an EGM\s*independent review receipt or proof/i);
 assert.match(d.concept,/Both documents remain \*\*DRAFT \/ NOT APPROVED\*\*/);
 assert.match(d.packet,/No source lint, self-review or historical unrelated report grants approval/);
});
