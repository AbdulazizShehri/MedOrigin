// No network, GUI, release, or MXC subprocess. Pure supported-runtime contract.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';

const target=readFileSync(fileURLToPath(new URL('./windows-mxc-d1-real-app-qualification.mjs',import.meta.url)),'utf8');

test('must bind real D1 MXC interactive launcher to pre-launch minimum supported Node',()=>{
  assert.match(target,/import\s*\{requireSupportedWindowsMxcNode\}\s*from\s*['"]\.\/windows-mxc-d1-runtime-node-qualification\.mjs['"]/);
  assert.match(target,/requireSupportedWindowsMxcNode\(process\.versions\.node,process\.platform\)/);
  assert.ok(target.indexOf('requireSupportedWindowsMxcNode(process.versions.node,process.platform)') <
    target.indexOf('const support=getPlatformSupport()'));
});
test('allow only documented Windows Node 24.21+, 26.8+ release series',()=>{
  for(const version of ['24.21.0','24.21.7','24.50.0','26.8.0','26.12.1','26.99.0']){
    assert.doesNotThrow(()=>requireSupportedWindowsMxcNode(version,'win32'),version);
  }
});
test('reject tested earlier unsupported Node 24.19 as well as unqualified release lines',()=>{
  for(const version of ['24.19.0','24.20.99','24.0.0','26.7.99','22.99.9','23.99.0','25.99.0','27.0.0','0.0.0']){
    assert.throws(()=>requireSupportedWindowsMxcNode(version,'win32'),/D1_MXC_NODE_RUNTIME_NO_GO/,version);
  }
});
test('fail closed on malformed, prerelease, non-Windows or unexpected runtime',()=>{
  for(const version of ['24.21','v26.12.1','26.8.0-rc.1','26.8.0+custom','latest','',null,undefined,{},'026.8.0']){
    assert.throws(()=>requireSupportedWindowsMxcNode(version,'win32'),/D1_MXC_NODE_RUNTIME_NO_GO/);
  }
  assert.throws(()=>requireSupportedWindowsMxcNode('26.12.1','linux'),/D1_MXC_NODE_RUNTIME_NO_GO/);
});
