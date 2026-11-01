// NONPUBLISHING. Test identical native probe on private IPv4 host interface,
// then in MXC deny-all. No Internet, DNS, patient data or OS firewall changes.
// This is controlled host-interface differential evidence, NOT WFP packet proof.
import {requireSupportedWindowsMxcNode} from './windows-mxc-d1-runtime-node-qualification.mjs';
import {createHash} from 'node:crypto';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {networkInterfaces} from 'node:os';
import net from 'node:net';
import dgram from 'node:dgram';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';

function requireValid(condition,message){
 if(!condition)throw Error('D1_PRIVATE_MXC_NO_GO: '+message);
}
function isRfc1918V4(address){
 if(net.isIP(address)!==4)return false;
 const p=address.split('.').map(Number);
 return p[0]===10 || (p[0]===172&&p[1]>=16&&p[1]<=31) ||
        (p[0]===192&&p[1]===168);
}
const exe=resolve(process.argv[2]||'');
const hash=process.argv[3]||'';
requireValid(process.platform==='win32','requires native authorized Windows');
requireValid(/^[0-9a-fA-F]{64}$/.test(hash),'expected exact SHA-256 required');
requireValid(createHash('sha256').update(readFileSync(exe)).digest('hex')===hash.toLowerCase(),'binary SHA mismatch');
requireSupportedWindowsMxcNode(process.versions.node,process.platform);
const {getPlatformSupport,run}=await import('@microsoft/mxc-sdk/v1');
const support=getPlatformSupport();
requireValid(support.isSupported&&support.availableMethods?.includes('processcontainer'),'MXC native processcontainer unsupported');
requireValid((support.isolationWarnings||[]).length===0,'MXC backend isolation warning');

const privateInterfaces=[...new Set(Object.values(networkInterfaces()).flatMap(v=>v||[])
  .filter(v=>v.family==='IPv4'&&!v.internal&&isRfc1918V4(v.address))
  .map(v=>v.address))];
requireValid(privateInterfaces.length>0,'no host-owned private IPv4 interface; no test');

function tcpListener(host) {
 return new Promise((yes,no)=>{
  const server=net.createServer(sock=>{server.deliveries++;sock.resume();});
  server.deliveries=0;
  server.once('error',no);
  server.listen(0,host,()=>yes(server));
 });
}
function udpListener(host){
 return new Promise((yes,no)=>{
  const socket=dgram.createSocket('udp4');
  socket.deliveries=0;
  socket.on('message',()=>socket.deliveries++);
  socket.once('error',no);
  socket.bind(0,host,()=>yes(socket));
 });
}
function probeOnHost(ip,tcpPort,udpPort) {
 return new Promise((yes,no)=>{
  const child=spawn(exe,[ip,String(tcpPort),String(udpPort),'D1_SYNTHETIC_NO_PHI'],
    {windowsHide:true,stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='';
  child.stdout.on('data',v=>stdout+=v);
  child.stderr.on('data',v=>stderr+=v);
  child.once('error',no);
  child.once('close',code=>yes({code,stdout,stderr}));
 });
}
async function one(ip,index){
 let tcp,udp;
 const tmp=mkdtempSync(join(dirname(exe),'mxc-d1-private-test-'));
 try {
  tcp=await tcpListener(ip);
  udp=await udpListener(ip);
  const tPort=tcp.address().port,uPort=udp.address().port;
  const positive=await probeOnHost(ip,tPort,uPort);
  await delay(350);
  requireValid(positive.code===0&&positive.stdout.includes('D1_PRIVATE_TCP_CONNECTED') &&
       positive.stdout.includes('D1_PRIVATE_UDP_SEND_RETURNED') &&
       tcp.deliveries>0&&udp.deliveries>0,
       'host-owned-interface positive control failed for candidate '+index);
  console.log('D1_PRIVATE_HOST_POSITIVE_PASS','candidate='+index,
    'TCP='+tcp.deliveries,'UDP='+udp.deliveries);
  tcp.deliveries=0;udp.deliveries=0;
  const req={
   command:'"'+exe+'" '+ip+' '+tPort+' '+uPort+' D1_SYNTHETIC_NO_PHI',
   containment:{type:'process'},
   network:{egress:{default:'deny'},ingress:{default:'deny',hostLoopback:'deny'}},
   ui:{disable:true},
   filesystem:{readonlyPaths:[exe],readwritePaths:[tmp]},
   workingDirectory:tmp,
   environment:{SystemRoot:process.env.SystemRoot,LOCALAPPDATA:tmp,APPDATA:tmp,TEMP:tmp,TMP:tmp},
   timeoutMs:14000
  };
  const result=await run(req);
  await delay(400);
  console.log('D1_PRIVATE_MXC_RUN_RESULT','candidate='+index,
   'exitCode='+result.exitCode,'timedOut='+result.timedOut,
   'warnings='+JSON.stringify(result.warnings||[]),
   'tcpDenied='+result.stdout?.includes('D1_PRIVATE_TCP_DENIED_OR_FAILED'));
  requireValid(result.exitCode===0&&!result.timedOut &&
   (result.warnings||[]).length===0 &&
   result.stdout?.includes('D1_PRIVATE_INTERFACE_PROBE_STARTED') &&
   result.stdout?.includes('D1_PRIVATE_TCP_DENIED_OR_FAILED') &&
   result.stdout?.includes('D1_PRIVATE_INTERFACE_PROBE_FINISHED'),
   'MXC failed to deny TCP or launch native probe for candidate '+index);
  requireValid(tcp.deliveries===0&&udp.deliveries===0,
   'contained probe delivered TCP/UDP to the private host interface at candidate '+index);
  console.log('D1_MXC_PRIVATE_IPV4_TCP_UDP_DIFFERENTIAL_PASS','candidate='+index,
    'TCP=0 UDP=0');
 }finally{
  try{tcp?.close()}catch{}
  try{udp?.close()}catch{}
  rmSync(tmp,{recursive:true,force:true,maxRetries:10,retryDelay:100});
 }
}
for(let i=0;i<privateInterfaces.length;i++)await one(privateInterfaces[i],i+1);
console.log('D1_MXC_PRIVATE_INTERFACE_DIFFERENTIAL_PASS',
  'candidates='+privateInterfaces.length,'NO_DNS_NO_REMOTE_PACKET_ATTESTATION');
