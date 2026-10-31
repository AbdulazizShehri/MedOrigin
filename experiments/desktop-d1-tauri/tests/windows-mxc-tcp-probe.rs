// Synthetic native Windows TCP boundary probe for nonpublishing MedOrigin MXC.
// ONLY ephemeral 127.0.0.1 and RFC5737 reserved TEST-NET-2, no PHI.
use std::net::{Ipv4Addr, SocketAddr, TcpStream};
use std::time::Duration;
fn test(ip: Ipv4Addr, port: u16) -> String {
    let address = SocketAddr::new(ip.into(), port);
    match TcpStream::connect_timeout(&address, Duration::from_millis(1800)) {
        Ok(stream) => {
            drop(stream);
            "CONNECTED".into()
        }
        Err(e) => format!("WSA{}", e.raw_os_error().unwrap_or(0)),
    }
}
fn main() {
    let arg = std::env::args().nth(1).unwrap_or_default();
    let Ok(port) = arg.parse::<u16>() else {
        eprintln!("INVALID_LOCALHOST_PORT");
        std::process::exit(20)
    };
    if port < 1025 {
        eprintln!("INVALID_LOCALHOST_PORT");
        std::process::exit(21)
    }
    let local = test(Ipv4Addr::LOCALHOST, port);
    let reserved = test(Ipv4Addr::new(198, 51, 100, 7), 443);
    println!("D1_MXC_SYNTHETIC_LOCALHOST={local}");
    println!("D1_MXC_SYNTHETIC_TEST_NET_2={reserved}");
    // Require the explicit Windows WSAEACCES kernel refusal. A timeout,
    // routing error, missing localhost listener or connection-refused result
    // must NOT be mistaken for an OS-enforced network isolation PASS.
    if local == "WSA10013" && reserved == "WSA10013" {
        println!("D1_MXC_NATIVE_OS_SOCKET_DENIAL_PASS");
    } else {
        std::process::exit(11);
    }
}
