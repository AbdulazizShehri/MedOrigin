// NONPUBLISHING SYNTHETIC-ONLY: standalone Windows MXC socket probe.
// It carries no patient data, no DNS lookup and no external network target.
// Compile from exact source with: rustc --edition 2024 -o synthetic-mxc-socket-probe.exe <this-file>
// Host-side harness provides only localhost and ephemeral TCP/UDP ports.
use std::env;
use std::io::Write;
use std::net::{IpAddr, SocketAddr, TcpStream, UdpSocket};
use std::str::FromStr;
use std::time::Duration;

fn main() {
    println!("D1_SYNTHETIC_PROBE_STARTED");
    let args: Vec<String> = env::args().collect();
    if args.len() != 5 {
        eprintln!("D1_PROBE_INVALID_ARGS");
        std::process::exit(2);
    }
    let ip = match IpAddr::from_str(&args[1]) {
        Ok(ip) if ip.is_loopback() => ip,
        _ => { eprintln!("D1_PROBE_NONLOOPBACK_REFUSED"); std::process::exit(2); }
    };
    let tcp_port = args[2].parse::<u16>().unwrap_or(0);
    let udp_port = args[3].parse::<u16>().unwrap_or(0);
    if tcp_port == 0 || udp_port == 0 || args[4] != "D1_SYNTHETIC_NO_PHI" {
        eprintln!("D1_PROBE_INVALID_SYNTHETIC_TOKEN");
        std::process::exit(2);
    }
    let tcp = SocketAddr::new(ip, tcp_port);
    match TcpStream::connect_timeout(&tcp, Duration::from_millis(1000)) {
        Ok(mut stream) => {
            let _ = stream.set_write_timeout(Some(Duration::from_millis(1000)));
            let _ = stream.write_all(b"D1_SYNTHETIC_TCP_PROBE");
            println!("D1_TCP_CONNECTED");
        }
        Err(error) => {
            println!("D1_TCP_CONNECT_DENIED_OR_FAILED");
            if error.raw_os_error() == Some(10013) {
                println!("D1_TCP_WSAEACCES_10013");
            } else {
                println!("D1_TCP_OTHER_ERROR_NOT_OS_DENIAL");
            }
        },
    }
    let bind = match ip { IpAddr::V4(_) => "0.0.0.0:0", IpAddr::V6(_) => "[::]:0" };
    match UdpSocket::bind(bind) {
        Ok(sock) => {
            let _ = sock.set_write_timeout(Some(Duration::from_millis(1000)));
            let target = SocketAddr::new(ip, udp_port);
            match sock.send_to(b"D1_SYNTHETIC_UDP_PROBE", target) {
                Ok(_) => println!("D1_UDP_SEND_RETURNED"),
                Err(_) => println!("D1_UDP_SEND_DENIED_OR_FAILED"),
            }
        }
        Err(_) => println!("D1_UDP_BIND_DENIED_OR_FAILED"),
    }
    println!("D1_SYNTHETIC_PROBE_FINISHED");
}
