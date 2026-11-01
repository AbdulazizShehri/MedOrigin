// Author-side EGM living-document source checks, NOT Goldfish/packet review.
// Synthetic-only, nonpublishing. Zero dependencies, no network or PHI.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const designPath=resolve(root,'docs/designs/D1_NETWORK_CONFINEMENT_EGM.md');
const briefPath=resolve(root,'docs/designs/D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md');
const packetPath=resolve(root,'docs/designs/D1_EGM_COLD_REVIEW_PACKET.md');
const indexPath=resolve(root,'docs/designs/SITEMAP.md');
const skillPath=resolve(root,'.agents/skills/medorigin-elephant/SKILL.md');
function read(path){assert.ok(existsSync(path),'Missing source: '+path);return readFileSync(path,'utf8')}
const design=read(designPath),brief=read(briefPath),packet=read(packetPath),index=read(indexPath),skill=read(skillPath);

test('EGM design index refers to complete real author-side artifacts',()=>{
  for(const name of ['D1_NETWORK_CONFINEMENT_EGM.md','D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md','D1_EGM_COLD_REVIEW_PACKET.md']){
    assert.ok(index.includes(name),'Index missing '+name);
    assert.ok(existsSync(resolve(dirname(indexPath),name)),'Indexed file not present');
  }
  assert.match(index,/DRAFT/);
  assert.match(index,/Goldfish NOT RUN/);
  assert.match(index,/NO-GO/);
});

test('design has mandatory alternatives, critical boundaries and testable OS controls',()=>{
  for(const title of [
    'Problem, scope, and source of truth','Goals and explicit non-goals','Threat model and trust boundaries',
    'Alternatives and decision boundary','Proposed proof architecture','Test matrix and acceptance criteria',
    'Execution stages and file boundaries','Open questions and required reviewers'
  ])assert.ok(design.includes(title),'Design missing '+title);
  for(const term of ['MXC ProcessContainer','WebView2','WFP','DNS','TCP','UDP',
    'IPv4','IPv6','hostLoopback','kernel-level','broker','positive control',
    'permissive','NO-GO','DRAFT / NOT APPROVED','Goldfish review: NOT RUN',
    '#662','#603','#574','#622','disposable','four synthetic']) {
     assert.ok(design.includes(term),'Missing control/boundary: '+term);
  }
  for(const rejected of ['A: MXC ProcessContainer','B: Disposable Windows VM',
      'C: CSP','D: Machine-wide','Prohibited','Rejected as release evidence']){
    assert.ok(design.includes(rejected),'Missing alternative: '+rejected);
  }
  assert.match(design,/zero in one snapshot cannot qualify zero egress|sampled endpoint zeros do \*\*not\*\*/i);
  assert.match(design,/genuinely fresh Goldfish/);
});

test('cold review packet rejects simulated review and requires independent evidence',()=>{
  for(const term of ['Review state: NOT RUN','Approval: NONE','STOP the Goldfish review',
    'fresh-context','read receipts','five-stage','NO-GO','WFP','signed',
    'independently','actual','#662']){
     assert.ok(packet.includes(term),'Missing fresh-context review contract: '+term);
  }
  assert.match(brief,/No fresh Goldfish review conducted/);
  assert.match(skill,/Goldfish review: NOT RUN/);
  assert.match(skill,/not a copy, fork or installation/i);
});

test('design and cold packet local Markdown links resolve to checked-in source',()=>{
  for(const path of [designPath,briefPath,packetPath,indexPath]){
    const md=read(path);
    const re=/\[[^\]]+\]\(([^)]+)\)/g;
    for(const match of md.matchAll(re)){
      const target=match[1];
      if(/^https?:\/\//.test(target)||target.startsWith('#'))continue;
      const dest=resolve(dirname(path),decodeURIComponent(target.split('#')[0]));
      assert.ok(existsSync(dest),'Broken link in '+path+': '+target);
    }
  }
});

test('no production gate, PHI, release status or reviewer completion can be inferred from doc lint',()=>{
  assert.match(design,/\*\*not\*\* authenticated kernel confinement evidence/);
  assert.match(design,/\*\*No-GO\*\* if just one necessary step lacks evidence/);
  assert.match(design,/human security reviewer have \*\*not\*\* reviewed/);
  assert.match(packet,/not a review receipt/);
  assert.match(packet,/Owner authorization for privileged WFP work:\*\* none/);
  assert.match(index,/Issue.*#662|\[#662\]/i);
});
