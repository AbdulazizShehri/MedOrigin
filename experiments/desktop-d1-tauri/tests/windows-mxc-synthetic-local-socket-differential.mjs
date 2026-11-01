// NONPUBLISHING synthetic-only MXC-vs-host differential loopback test.
// Provides NO packet-level proof, DNS qualification or release approval.
// Requires supported Windows Node; host and MXC run the same sha-pinned native probe.
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';
import {createHash} from 'node:crypto';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join,dirname,resolve} from 'node:path';
import net from 'node:net';
import dgram from 'node:dgram';
import {spawn} from 'node:child_process';
import {setTimeout as pause} from 'node:timers/promises';

const exe=resolve(process.argv[2]||'');
const expected=process.argv[3]||'';
function admit(condition,reason){if(!condition)throw Error('D1_MXC_SYNTHETIC_LOOPBACK_NO_GO: '+reason)}
admit(process.platform==='win32','Windows required');
admit(/^[0-9a-fA-F]{64}$/.test(expected),'pinned probe SHA-256 required');
admit(createHash('sha256').update(readFileSync(exe)).digest('hex')===expected.toLowerCase(),'probe SHA-256 mismatch');
requireSupportedWindowsMxcNode(process.versions.node,process.platform);
const {getPlatformSupport,run}=await import('@microsoft/mxc-sdk/v1');
const support=getPlatformSupport();
admit(support.isSupported&&support.availableMethods?.includes('processcontainer'),'native MXC ProcessContainer unavailable');

async function bindTcp(host) {
 const server=net.createServer();
 await new Promise((ok,bad)=>{server.once('error',bad);server.listen(0,host,ok)});
 return server;
}
async function bindUdp(host) {
 const sock=dgram.createSocket(host.includes(':')?'udp6':'udp4');
 await new Promise((ok,bad)=>{sock.once('error',bad);sock.bind(0,host,ok)});
 return sock;
}
async function spawnProbe(host,tcpPort,udpPort) {
 return await new Promise((resolvePromise,reject)=>{
   const child=spawn(exe,[host,String(tcpPort),String(udpPort),'D1_SYNTHETIC_NO_PHI'],{windowsHide:true,stdio:['ignore','pipe','pipe']});
   let stdout='',stderr='';
   child.stdout.on('data',c=>stdout+=c);
   child.stderr.on('data',c=>stderr+=c);
   child.on('error',reject);
   child.on('close',code=>resolvePromise({code,stdout,stderr}));
 });
}
async function check(family,host) {
 let tcp,udp;
 const tmp=mkdtempSync(join(dirname(exe),'mxc-d1-loopback-'));
 try {
   tcp=await bindTcp(host);
   udp=await bindUdp(host);
   let tcpCount=0,udpCount=0;
   tcp.on('connection',socket=>{tcpCount++;socket.resume();});
   udp.on('message',()=>udpCount++);
   const tcpPort=tcp.address().port,udpPort=udp.address().port;
   const positive=await spawnProbe(host,tcpPort,udpPort);
   await pause(450);
   admit(positive.code===0&&positive.stdout.includes('D1_TCP_CONNECTED')&&
         positive.stdout.includes('D1_UDP_SEND_RETURNED')&&tcpCount>0&&udpCount>0,
         family+' host positive control did not demonstrably reach TCP and UDP listeners');
   console.log('D1_HOST_POSITIVE_CONTROL_PASS',family,'TCP='+tcpCount,'UDP='+udpCount);
   tcpCount=0;udpCount=0;
   const req={
     command:'"'+exe+'" '+host+' '+tcpPort+' '+udpPort+' D1_SYNTHETIC_NO_PHI',
     containment:{type:'process'},
     network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
     ui:{disable:true},
     filesystem:{readonlyPaths:[exe],readwritePaths:[tmp]},
     workingDirectory:tmp,
     environment:{SystemRoot:process.env.SystemRoot,LOCALAPPDATA:tmp,APPDATA:tmp,TEMP:tmp,TMP:tmp},
     timeoutMs:14000
   };
   const result=await run(req);
   await pause(450);
   console.log('D1_MXC_SYNTHETIC_RESULT',family,JSON.stringify(result));
   admit(result.exitCode===0&&!result.timedOut&&(result.warnings||[]).length===0&&
      result.stdout.includes('D1_SYNTHETIC_PROBE_STARTED')&&
      result.stdout.includes('D1_TCP_CONNECT_DENIED_OR_FAILED')&&
      result.stdout.includes('D1_TCP_WSAEACCES_10013')&&
      result.stdout.includes('D1_SYNTHETIC_PROBE_FINISHED'),
      family+' MXC probe execution or TCP differential failed');
   admit(tcpCount===0&&udpCount===0,family+' host TCP/UDP listener observed a contained connection');
   console.log('D1_MXC_SYNTHETIC_LOOPBACK_DIFFERENTIAL_PASS',family,'TCP=0 UDP=0');
 } finally {
   try {tcp?.close()} catch {}
   try {udp?.close()} catch {}
   rmSync(tmp,{force:true,recursive:true,maxRetries:10,retryDelay:100});
 }
}
await check('IPv4','127.0.0.1');
await check('IPv6','::1');
console.log('D1_MXC_IPV4_IPV6_TCP_UDP_LOCAL_DIFFERENTIAL_PASS_NO_PACKET_OR_DNS_PROOF');
