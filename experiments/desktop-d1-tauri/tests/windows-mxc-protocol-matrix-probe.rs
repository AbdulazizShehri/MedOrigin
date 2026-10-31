// NONPUBLISHING synthetic-only Windows network-boundary experiment.
// Same native binary must prove an unrestricted local positive control and
// explicit WSA10013 OS denial for each TCP/UDP IPv4+IPv6 attempt in MXC.
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr, TcpStream, UdpSocket};
use std::time::Duration;

fn tcp(address: SocketAddr) -> String {
    match TcpStream::connect_timeout(&address, Duration::from_millis(1500)) {
        Ok(s) => {
            drop(s);
            "CONNECTED".to_string()
        }
        Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
    }
}

fn udp(address: SocketAddr) -> String {
    let bind: SocketAddr = match address {
        SocketAddr::V4(_) => "0.0.0.0:0".parse().unwrap(),
        SocketAddr::V6(_) => "[::]:0".parse().unwrap(),
    };
    match UdpSocket::bind(bind) {
        Ok(s) => match s.send_to(b"synthetic-mxc-udp-probe", address) {
            Ok(n) => format!("SENT{n}"),
            Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
        },
        Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
    }
}

fn report(label: &str, result: String, denied: &mut bool) {
    println!("D1_MXC_{label}={result}");
    if result != "WSA10013" {
        *denied = false;
    }
}

fn main() {
    let mut args = std::env::args().skip(1);
    let port4 = args
        .next()
        .and_then(|x| x.parse::<u16>().ok())
        .filter(|x| *x >= 1025);
    let port6 = args
        .next()
        .and_then(|x| x.parse::<u16>().ok())
        .filter(|x| *x >= 1025);
    let mode = args.next().unwrap_or_default();
    let (Some(port4), Some(port6)) = (port4, port6) else {
        eprintln!("D1_MXC_INVALID_LOCALHOST_PORTS");
        std::process::exit(20)
    };
    if mode != "control" && mode != "denied" {
        eprintln!("D1_MXC_INVALID_MODE");
        std::process::exit(21)
    }
    let mut all_denied = true;
    let local4 = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port4);
    let local6 = SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), port6);
    report("TCP4_LOOPBACK", tcp(local4), &mut all_denied);
    report("TCP6_LOOPBACK", tcp(local6), &mut all_denied);
    report("UDP4_LOOPBACK", udp(local4), &mut all_denied);
    report("UDP6_LOOPBACK", udp(local6), &mut all_denied);
    // Reserved documentation targets are never attempted in control mode,
    // so unrestricted execution cannot produce real outbound traffic.
    if mode == "denied" {
        let remote4 = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(198, 51, 100, 7)), 443);
        let remote6 = SocketAddr::new(IpAddr::V6("2001:db8::7".parse().unwrap()), 443);
        report("TCP4_TEST_NET", tcp(remote4), &mut all_denied);
        report("TCP6_DOC_NET", tcp(remote6), &mut all_denied);
        report("UDP4_TEST_NET", udp(remote4), &mut all_denied);
        report("UDP6_DOC_NET", udp(remote6), &mut all_denied);
        if all_denied {
            println!("D1_MXC_ALL_8_NATIVE_SOCKETS_WSA10013_PASS");
        } else {
            eprintln!("D1_MXC_PROTOCOL_MATRIX_NO_GO");
            std::process::exit(11)
        }
    }
}
