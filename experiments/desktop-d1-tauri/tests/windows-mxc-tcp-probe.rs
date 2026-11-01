// Synthetic native Windows TCP/UDP boundary probe for nonpublishing MedOrigin MXC.
// ONLY ephemeral 127.0.0.1, ::1 and RFC5737 reserved TEST-NET-2. No PHI.
// Every positive control uses the exact same executable outside MXC.
use std::net::{Ipv4Addr, Ipv6Addr, SocketAddr, TcpStream, UdpSocket};
use std::time::Duration;

fn test_tcp(address: SocketAddr) -> String {
    match TcpStream::connect_timeout(&address, Duration::from_millis(1800)) {
        Ok(stream) => {
            drop(stream);
            "CONNECTED".into()
        }
        Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
    }
}

fn test_udp(bind: &str, address: SocketAddr) -> String {
    match UdpSocket::bind(bind) {
        Ok(socket) => match socket.send_to(b"medorigin-fictional-loopback", address) {
            Ok(_) => "SENT".into(),
            Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
        },
        Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
    }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 4 {
        eprintln!("EXPECTED_FOUR_EPHEMERAL_LOCAL_PORTS");
        std::process::exit(20);
    }
    let ports: Vec<u16> = args
        .iter()
        .map(|arg| arg.parse::<u16>().unwrap_or(0))
        .collect();
    if ports.iter().any(|port| *port < 1025) {
        eprintln!("INVALID_LOCALHOST_PORT");
        std::process::exit(21);
    }

    let local = test_tcp(SocketAddr::new(Ipv4Addr::LOCALHOST.into(), ports[0]));
    let reserved = test_tcp(SocketAddr::new(Ipv4Addr::new(198, 51, 100, 7).into(), 443));
    let ipv6 = test_tcp(SocketAddr::new(Ipv6Addr::LOCALHOST.into(), ports[1]));
    let udp4 = test_udp(
        "127.0.0.1:0",
        SocketAddr::new(Ipv4Addr::LOCALHOST.into(), ports[2]),
    );
    let udp6 = test_udp(
        "[::1]:0",
        SocketAddr::new(Ipv6Addr::LOCALHOST.into(), ports[3]),
    );

    println!("D1_MXC_SYNTHETIC_LOCALHOST={local}");
    println!("D1_MXC_SYNTHETIC_TEST_NET_2={reserved}");
    println!("D1_MXC_SYNTHETIC_IPV6_TCP={ipv6}");
    println!("D1_MXC_SYNTHETIC_IPV4_UDP={udp4}");
    println!("D1_MXC_SYNTHETIC_IPV6_UDP={udp6}");
    // Require WSAEACCES for all TCP connections. Windows UDP send_to may
    // return SENT despite a network-policy drop; only the independent host
    // receiver can observe bounded loopback delivery. SENT alone is NOT proof.
    if local == "WSA10013"
        && reserved == "WSA10013"
        && ipv6 == "WSA10013"
        && (udp4 == "WSA10013" || udp4 == "SENT")
        && (udp6 == "WSA10013" || udp6 == "SENT")
    {
        println!("D1_MXC_NATIVE_TCP_WSAEACCES_UDP_RESULT_CAPTURED");
    } else {
        std::process::exit(11);
    }
}
