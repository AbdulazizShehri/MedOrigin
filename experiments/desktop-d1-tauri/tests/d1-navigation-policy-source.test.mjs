// D1 source contract: view navigation and popup refusal do not prove OS packet isolation.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const source=()=>readFileSync(resolve(root,'src-tauri/src/lib.rs'),'utf8');
const config=()=>JSON.parse(readFileSync(resolve(root,'src-tauri/tauri.conf.json'),'utf8'));

test('webview is not auto-created before navigation / popup hooks are installed',()=>{
 const conf=config();
 assert.equal(conf.app.windows.length,1);
 assert.equal(conf.app.windows[0].create,false);
 const s=source();
 assert.match(s,/WebviewWindowBuilder::from_config/);
 assert.match(s,/\.on_navigation\(/);
 assert.match(s,/\.on_new_window\(/);
 assert.match(s,/NewWindowResponse::Deny/);
 assert.match(s,/\.build\(\)\?/);
});

test('only app-local origins accepted by source policy, not OS-level packet proof',()=>{
 const s=source();
 assert.match(s,/fn allow_preview_navigation\(/);
 assert.match(s,/tauri\.localhost/);
 assert.match(s,/url\.host_str\(\)/);
 assert.match(s,/url\.port\(\)/);
 assert.match(s,/url\.username\(\)/);
 assert.match(s,/url\.password\(\)/);
 assert.match(s,/webview_runtime_egress_qualified:\s*false/);
 assert.doesNotMatch(s,/webview_runtime_egress_qualified:\s*true/);
});
