// Pure synthetic fail-closed tests: no real process, network or SDK required.
import test from 'node:test';
import assert from 'node:assert/strict';
import {parseD1Snapshot, assertNoResidual, requireQualifiedRun} from './windows-mxc-d1-lifecycle-proof.mjs';

const snapshot = [
  {pid:412, startTicks:'638975000000000000', name:'medorigin-desktop-d1-preview.exe'},
  {pid:414, startTicks:'638975000000000010', name:'msedgewebview2.exe'},
];
const stdout = 'MXC_D1_PROCESS_SNAPSHOT_JSON='+JSON.stringify(snapshot)+'\n'+
  'MXC_D1_REAL_APP_UIA_4_OF_4_PASS_NONPUBLISHING_NETWORK_STILL_NO_GO\n';

test('accepts a distinct real D1 root and WebView2 child with timestamps',()=>{
  assert.deepEqual(parseD1Snapshot(stdout),snapshot);
});
test('rejects missing snapshot, bad JSON, and empty inventory',()=>{
  for(const s of ['', 'MXC_D1_PROCESS_SNAPSHOT_JSON={oops}', 'MXC_D1_PROCESS_SNAPSHOT_JSON=[]']){
    assert.throws(()=>parseD1Snapshot(s));
  }
});
test('rejects duplicate PIDs, missing WebView2, or bad timestamps',()=>{
  const cases = [
    [snapshot[0],{...snapshot[1],pid:412}],
    [snapshot[0]],
    [{...snapshot[0],startTicks:'not-a-time'},snapshot[1]],
    [{...snapshot[0],pid:0},snapshot[1]],
    [{...snapshot[0],name:'other.exe'},snapshot[1]],
  ];
  for(const items of cases) assert.throws(()=>parseD1Snapshot('MXC_D1_PROCESS_SNAPSHOT_JSON='+JSON.stringify(items)));
});
test('rejects runner success markers without actual exit zero',()=>{
  assert.throws(()=>requireQualifiedRun({status:1,stdout}));
  assert.throws(()=>requireQualifiedRun({status:0,stdout:'MXC_D1_PROCESS_SNAPSHOT_JSON='+JSON.stringify(snapshot)}));
  assert.doesNotThrow(()=>requireQualifiedRun({status:0,stdout:stdout+'D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO\nMXC_D1_TIME_WINDOWED_TCP_SAMPLER_PASS samples=12\n'}));
});
test('detects exact lingering process identity but ignores reused PID',()=>{
  assert.throws(()=>assertNoResidual(snapshot,[snapshot[1]]));
  assert.doesNotThrow(()=>assertNoResidual(snapshot,[{...snapshot[1],startTicks:'638975000000000011'}]));
  assert.doesNotThrow(()=>assertNoResidual(snapshot,[]));
});
test('rejects duplicate/invalid live process identities instead of treating them as absent',()=>{
  assert.throws(()=>assertNoResidual(snapshot,[{pid:414,startTicks:'bad'}]));
  assert.throws(()=>assertNoResidual(snapshot,[snapshot[1],snapshot[1]]));
});
