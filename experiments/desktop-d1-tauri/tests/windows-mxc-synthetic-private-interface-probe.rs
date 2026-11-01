// Nonpublishing synthetic private-interface-only MXC connection probe.
// Rejects loopback and public/reserved IPs. No DNS or user/clinical data.
// Pair with host harness that verifies the target IP belongs to this host.
use std::env;
use std::io::Write;
use std::net::{IpAddr, SocketAddr, TcpStream, UdpSocket};
use std::str::FromStr;
use std::time::Duration;
fn main() {
    println!("D1_PRIVATE_INTERFACE_PROBE_STARTED");
    let args:Vec<String>=env::args().collect();
    if args.len()!=5 { eprintln!("D1_PRIVATE_INTERFACE_INVALID_ARGS");std::process::exit(2); }
    let ip=match IpAddr::from_str(&args[1]) {
        Ok(IpAddr::V4(ip)) if ip.is_private() && !ip.is_loopback() =>
            IpAddr::V4(ip),
        _ => {eprintln!("D1_PRIVATE_INTERFACE_NONPRIVATE_REFUSED");std::process::exit(2);}
    };
    let tcp_port=args[2].parse::<u16>().unwrap_or(0);
    let udp_port=args[3].parse::<u16>().unwrap_or(0);
    if tcp_port==0 || udp_port==0 || args[4]!="D1_SYNTHETIC_NO_PHI" {
        eprintln!("D1_PRIVATE_INTERFACE_INVALID_TOKEN");std::process::exit(2);
    }
    let address=SocketAddr::new(ip,tcp_port);
    match TcpStream::connect_timeout(&address,Duration::from_millis(1300)) {
        Ok(mut stream)=>{
            let _=stream.set_write_timeout(Some(Duration::from_millis(1000)));
            let _=stream.write_all(b"D1_PRIVATE_TCP_SYNTHETIC");
            println!("D1_PRIVATE_TCP_CONNECTED");
        }
        Err(_)=>println!("D1_PRIVATE_TCP_DENIED_OR_FAILED"),
    }
    match UdpSocket::bind("0.0.0.0:0") {
        Ok(socket)=>{
            let _=socket.set_write_timeout(Some(Duration::from_millis(1000)));
            match socket.send_to(b"D1_PRIVATE_UDP_SYNTHETIC",SocketAddr::new(ip,udp_port)){
                Ok(_)=>println!("D1_PRIVATE_UDP_SEND_RETURNED"),
                Err(_)=>println!("D1_PRIVATE_UDP_SEND_DENIED_OR_FAILED"),
            }
        }
        Err(_)=>println!("D1_PRIVATE_UDP_BIND_DENIED_OR_FAILED"),
    }
    println!("D1_PRIVATE_INTERFACE_PROBE_FINISHED");
}
