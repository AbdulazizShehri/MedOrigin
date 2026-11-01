// Actual Windows localhost-only *unrestricted* MXC probe positive-control test.
// This script never launches MXC, a WebView, or a remote network destination.
// No WFP/ETW/packet egress proof. Synthetic only, no PHI, no release.
import {spawnSync,execFile} from 'node:child_process';
import {createServer} from 'node:net';
import {createSocket} from 'node:dgram';
import {mkdtempSync,mkdirSync,rmSync,readFileSync} from 'node:fs';
import {createHash,randomBytes} from 'node:crypto';
import {tmpdir} from 'node:os';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {assessNativePositiveControl,assessTcpNonceBinding} from './windows-mxc-protocol-matrix-verdict.mjs';

const deny=why=>{throw Error('D1_MXC_LOCAL_ONLY_NO_GO: '+why)};
if(process.platform!=='win32')deny('native Windows only');
if(process.argv.length!==2)deny('no user-supplied network or executable arguments allowed');
const base=resolve(process.env.MEDORIGIN_MXC_TEST_TMP||tmpdir());
const scratch=mkdtempSync(join(base,'medorigin-mxc-loopback-only-'));
const rustSource=join(dirname(fileURLToPath(import.meta.url)),'windows-mxc-protocol-matrix-probe.rs');
const exe=join(scratch,'protocol-control.exe');
const tcp4Peers=[],tcp6Peers=[],udp4Packets=[],udp6Packets=[];

const nonce4=randomBytes(32).toString('hex');
const nonce6=randomBytes(32).toString('hex');
const challenge4=randomBytes(32),challenge6=randomBytes(32);
const tcp4Proofs=[],tcp6Proofs=[],proofClosures=[];
const bindProof=(socket,proofs,challenge)=>{
 const proof={reply:Buffer.alloc(0),completed:false,errored:false,overflow:false};
 proofs.push(proof);
 proofClosures.push(new Promise(done=>socket.once('close',()=>{
  proof.completed=proof.reply.length===96&&!proof.errored&&!proof.overflow;done();
 })));
 socket.on('data',chunk=>{
  if(proof.reply.length+chunk.length>96){proof.overflow=true;socket.destroy();return;}
  proof.reply=Buffer.concat([proof.reply,chunk]);
  if(proof.reply.length===96)socket.end();
 });
 socket.on('error',()=>{proof.errored=true;});
 socket.write(challenge);
};
const runControl=(exe,args)=>new Promise(resolve=>{
 execFile(exe,args,{encoding:'utf8',timeout:12000,maxBuffer:32768,windowsHide:true},
  (error,stdout,stderr)=>resolve({
   status:error?(Number.isInteger(error.code)?error.code:null):0,
   signal:error?.signal??null,
   error:error&&!Number.isInteger(error.code)?error:undefined,stdout,stderr
  }));
});
const awaitProofs=async()=>{
 let timer;
 try{await Promise.race([Promise.all(proofClosures),
  new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('TCP proof close timeout')),2500);})]);}
 finally{clearTimeout(timer);}
};

const peerOf=s=>({
 remoteAddress:s.remoteAddress,remoteFamily:s.remoteFamily,
 remotePort:s.remotePort,localAddress:s.localAddress,localPort:s.localPort
});
const packetOf=(m,rinfo)=>({
 payload:Buffer.from(m),address:rinfo.address,
 family:rinfo.family,size:rinfo.size,port:rinfo.port
});
const tcp4=createServer(s=>{tcp4Peers.push(peerOf(s));bindProof(s,tcp4Proofs,challenge4);});
const tcp6=createServer(s=>{tcp6Peers.push(peerOf(s));bindProof(s,tcp6Proofs,challenge6);});
const udp4=createSocket('udp4'),udp6=createSocket('udp6');
udp4.on('message',(m,rinfo)=>udp4Packets.push(packetOf(m,rinfo)));
udp6.on('message',(m,rinfo)=>udp6Packets.push(packetOf(m,rinfo)));
const bindTcp=(s,host)=>new Promise((ok,fail)=>{s.once('error',fail);s.listen(0,host,ok)});
const bindUdp=(s,host,port)=>new Promise((ok,fail)=>{s.once('error',fail);s.bind(port,host,ok)});
const closeTcp=s=>new Promise(done=>{try{s.close(done)}catch{done()}});
const closeUdp=s=>new Promise(done=>{try{s.close(done)}catch{done()}});
let opened=false;
try{
 const compile=spawnSync('rustc',['+1.97.1','-C','debuginfo=0','-C','opt-level=1',
  '-o',exe,rustSource],{encoding:'utf8',timeout:120000,maxBuffer:32768,windowsHide:true});
 if(!compile||compile.status!==0||compile.signal||compile.error||compile.stderr==null)
  deny('local synthetic Rust probe build failed');
 const digest=()=>createHash('sha256').update(readFileSync(exe)).digest('hex');
 const sha=digest();
 await bindTcp(tcp4,'127.0.0.1');
 await bindTcp(tcp6,'::1');
 const expectedTcp4Port=tcp4.address().port,expectedTcp6Port=tcp6.address().port;
 await bindUdp(udp4,'127.0.0.1',expectedTcp4Port);
 await bindUdp(udp6,'::1',expectedTcp6Port);
 opened=true;
 // The Rust probe's 'control' mode contains NO remote test-net attempts.
 const control=await runControl(exe,[String(expectedTcp4Port),String(expectedTcp6Port),'control',nonce4,nonce6]);
 await awaitProofs();
 if(sha!==digest())deny('native Rust probe bytes changed during local control');
 const assessment=assessNativePositiveControl({
  control,tcp4Accepts:tcp4Peers.length,tcp6Accepts:tcp6Peers.length,
  tcp4Peers,tcp6Peers,expectedTcp4Port,expectedTcp6Port,
  udp4Receipts:udp4Packets.length,udp6Receipts:udp6Packets.length,
  udp4Packets,udp6Packets
 });
 const proof=assessTcpNonceBinding({expectedNonce4:Buffer.from(nonce4,'ascii'),expectedNonce6:Buffer.from(nonce6,'ascii'),challenge4,challenge6,tcp4Proofs,tcp6Proofs});
 if(proof.classification!=='LOCAL_TCP_NONCE_ECHO_ONLY')deny('native nonce proof not qualified');
 if(assessment.classification!=='UNCONFINED_LOCAL_POSITIVE_CONTROL_ONLY')
  deny('unrestricted control cannot claim OS enforcement');
 console.log('D1_MXC_LOCAL_ONLY_UNRESTRICTED_TCP4_TCP6_UDP4_UDP6_CONTROL_PASS');
 console.log('D1_MXC_LOCAL_ONLY_PROBE_SHA256='+sha);
 console.log('D1_MXC_LOCAL_ONLY_TCP4_ACCEPTS='+tcp4Peers.length);
 console.log('D1_MXC_LOCAL_ONLY_TCP6_ACCEPTS='+tcp6Peers.length);
 console.log('D1_MXC_LOCAL_ONLY_UDP4_RECEIPTS='+udp4Packets.length);
 console.log('D1_MXC_LOCAL_ONLY_UDP6_RECEIPTS='+udp6Packets.length);
 console.log('D1_MXC_LOCAL_ONLY_NEVER_MXC_WFP_DNS_BROKER_OR_RELEASE_PROOF');
}catch(error){
 console.error('D1_MXC_LOCAL_ONLY_NO_GO',error?.message||String(error));
 process.exitCode=1;
}finally{
 await Promise.all([closeTcp(tcp4),closeTcp(tcp6),closeUdp(udp4),closeUdp(udp6)]);
 try{rmSync(scratch,{recursive:true,force:true})}
 catch{console.error('D1_MXC_LOCAL_ONLY_NO_GO: scratch cleanup failed');process.exitCode=1}
}
