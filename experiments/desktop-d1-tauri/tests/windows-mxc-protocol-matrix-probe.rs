// NONPUBLISHING synthetic-only Windows network-boundary experiment.
// Same native bytes in unrestricted localhost control and denied-mode MXC.
// Per-run TCP nonce/challenge only binds a bounded LOCAL positive control;
// it does not authenticate a PID or prove WFP/ETW/packet egress.
use std::io::{Read, Write};
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr, TcpStream, UdpSocket};
use std::time::Duration;

fn tcp(address: SocketAddr, proof_nonce: Option<&[u8]>) -> String {
    match TcpStream::connect_timeout(&address, Duration::from_millis(1500)) {
        Ok(mut stream) => {
            if let Some(nonce) = proof_nonce {
                let _ = stream.set_read_timeout(Some(Duration::from_millis(2000)));
                let _ = stream.set_write_timeout(Some(Duration::from_millis(2000)));
                let mut challenge = [0u8; 32];
                if stream.read_exact(&mut challenge).is_err()
                    || stream.write_all(nonce).is_err()
                    || stream.write_all(&challenge).is_err()
                {
                    return "HANDSHAKE_FAILED".to_string();
                }
            }
            drop(stream);
            "CONNECTED".to_string()
        }
        Err(error) => format!("WSA{}", error.raw_os_error().unwrap_or(0)),
    }
}

fn udp(address: SocketAddr) -> String {
    let bind: SocketAddr = match address {
        SocketAddr::V4(_) => "0.0.0.0:0".parse().unwrap(),
        SocketAddr::V6(_) => "[::]:0".parse().unwrap(),
    };
    match UdpSocket::bind(bind) {
        Ok(socket) => match socket.send_to(b"synthetic-mxc-udp-probe", address) {
            Ok(n) => format!("SENT{n}"),
            Err(error) => format!("WSA{}", error.raw_os_error().unwrap_or(0)),
        },
        Err(error) => format!("WSA{}", error.raw_os_error().unwrap_or(0)),
    }
}

fn report(label: &str, result: String, denied: &mut bool) {
    println!("D1_MXC_{label}={result}");
    if result != "WSA10013" {
        *denied = false;
    }
}

fn parse_nonce(value: Option<String>) -> Option<Vec<u8>> {
    let bytes = value?.into_bytes();
    if bytes.len() != 64 || !bytes.iter().all(u8::is_ascii_hexdigit) {
        return None;
    }
    Some(bytes)
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
    let (nonce4, nonce6) = if mode == "control" {
        let Some(n4) = parse_nonce(args.next()) else {
            eprintln!("D1_MXC_MISSING_CONTROL_NONCE4");
            std::process::exit(22)
        };
        let Some(n6) = parse_nonce(args.next()) else {
            eprintln!("D1_MXC_MISSING_CONTROL_NONCE6");
            std::process::exit(23)
        };
        if n4 == n6 || args.next().is_some() {
            eprintln!("D1_MXC_INVALID_CONTROL_NONCES");
            std::process::exit(24)
        }
        (Some(n4), Some(n6))
    } else {
        if args.next().is_some() {
            eprintln!("D1_MXC_DENIED_MODE_REJECTS_NONCE");
            std::process::exit(25)
        }
        (None, None)
    };
    let mut all_denied = true;
    let local4 = SocketAddr::new(IpAddr::V4(Ipv4Addr::LOCALHOST), port4);
    let local6 = SocketAddr::new(IpAddr::V6(Ipv6Addr::LOCALHOST), port6);
    report(
        "TCP4_LOOPBACK",
        tcp(local4, nonce4.as_deref()),
        &mut all_denied,
    );
    report(
        "TCP6_LOOPBACK",
        tcp(local6, nonce6.as_deref()),
        &mut all_denied,
    );
    report("UDP4_LOOPBACK", udp(local4), &mut all_denied);
    report("UDP6_LOOPBACK", udp(local6), &mut all_denied);
    // Reserved documentation targets never attempted in unrestricted control.
    if mode == "denied" {
        let remote4 = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(198, 51, 100, 7)), 443);
        let remote6 = SocketAddr::new(IpAddr::V6("2001:db8::7".parse().unwrap()), 443);
        report("TCP4_TEST_NET", tcp(remote4, None), &mut all_denied);
        report("TCP6_DOC_NET", tcp(remote6, None), &mut all_denied);
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
