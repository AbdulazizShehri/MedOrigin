// Nonpublishing synthetic-only child-process proof of MXC import ordering.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdtempSync,writeFileSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

test('unsupported Windows Node is rejected before native SDK module evaluation', {skip:process.platform!=='win32'},()=>{
  const temp=mkdtempSync(join(tmpdir(),'medorigin-mxc-admission-'));
  try {
    const fixture=join(temp,'synthetic-no-patient-data.exe');
    writeFileSync(fixture,Buffer.from('synthetic qualification fixture only'));
    const sha=createHash('sha256').update(readFileSync(fixture)).digest('hex');
    const sdk=join(temp,'sdk-marker.mjs');
    writeFileSync(sdk,"throw Error('SDK_WAS_LOADED_BEFORE_ADMISSION');\n");
    const original=readFileSync(new URL('./windows-mxc-d1-real-app-qualification.mjs',import.meta.url),'utf8');
    // Use a file URL directly, avoiding Windows path/URL ambiguity.
    const gateUrl=new URL('./windows-mxc-d1-runtime-node-qualification.mjs',import.meta.url).href;
    const sdkUrl=pathToFileURL(sdk).href;
    assert.ok(original.includes("await import('@microsoft/mxc-sdk/v1')"));
    assert.ok(original.includes("from './windows-mxc-d1-runtime-node-qualification.mjs'"));
    const base=original
      .replace("from './windows-mxc-d1-runtime-node-qualification.mjs'", "from '"+gateUrl+"'")
      .replace("await import('@microsoft/mxc-sdk/v1')", "await import('"+sdkUrl+"')");
    assert.notEqual(base,original);
    for (const [label,version,expectSdk] of [
      ['unsupported','24.19.0',false],
      ['supported','26.12.1',true],
    ]) {
      const file=join(temp,label+'.mjs');
      const modified=base.replace(
        'requireSupportedWindowsMxcNode(process.versions.node,process.platform);',
        "requireSupportedWindowsMxcNode('"+version+"',process.platform);"
      );
      assert.notEqual(modified,base);
      writeFileSync(file,modified);
      const result=spawnSync(process.execPath,[file,fixture,sha],{encoding:'utf8',timeout:12000});
      const output=(result.stdout||'')+'\n'+(result.stderr||'');
      assert.notEqual(result.status,0,label+' unexpectedly succeeded');
      assert.equal(output.includes('SDK_WAS_LOADED_BEFORE_ADMISSION'),expectSdk,label+' SDK evaluation order');
      if(!expectSdk)assert.match(output,/D1_MXC_NODE_RUNTIME_NO_GO/);
    }
  } finally {
    rmSync(temp,{recursive:true,force:true});
  }
});

test('actual unsupported Windows host Node rejects before SDK resolution', {skip:process.platform!=='win32'||!/^v24\\.(?:[0-9]|1[0-9]|20)\\./.test(process.version)},()=>{
  const temp=mkdtempSync(join(tmpdir(),'medorigin-mxc-host-'));
  try {
    const fixture=join(temp,'synthetic-fixture.exe');
    writeFileSync(fixture,Buffer.from('not an executable: synthetic hash preflight'));
    const sha=createHash('sha256').update(readFileSync(fixture)).digest('hex');
    const original=readFileSync(new URL('./windows-mxc-d1-real-app-qualification.mjs',import.meta.url),'utf8');
    const gateUrl=new URL('./windows-mxc-d1-runtime-node-qualification.mjs',import.meta.url).href;
    const modified=original.replace("from './windows-mxc-d1-runtime-node-qualification.mjs'","from '"+gateUrl+"'");
    assert.notEqual(modified,original);
    const isolated=join(temp,'actual-host-runtime.mjs');
    writeFileSync(isolated,modified);
    const result=spawnSync(process.execPath,[isolated,fixture,sha],{encoding:'utf8',timeout:12000});
    const output=(result.stdout||'')+'\\n'+(result.stderr||'');
    assert.notEqual(result.status,0);
    assert.match(output,/D1_MXC_NODE_RUNTIME_NO_GO/);
    assert.doesNotMatch(output,/ERR_MODULE_NOT_FOUND|Cannot find package '@microsoft\\/mxc-sdk'/);
  } finally {
    rmSync(temp,{recursive:true,force:true});
  }
});
