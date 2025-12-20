// CANARY: openssl_tls_build_debug_2024_12_17
use openssl::ssl::{SslConnector, SslMethod};
use std::io::{Read, Write};
use std::net::TcpStream;

fn main() {
    // Connect to rust-lang.org on port 443
    // This requires actual network connectivity and OpenSSL to be properly configured
    let stream = TcpStream::connect("www.rust-lang.org:443")
        .expect("Failed to connect to server");
    
    // Create SSL connector - this will fail if OpenSSL is not properly linked
    let connector = SslConnector::builder(SslMethod::tls())
        .expect("Failed to create SSL connector - OpenSSL may not be properly configured")
        .build();
    
    // Establish TLS connection - this performs actual TLS handshake
    let mut stream = connector.connect("www.rust-lang.org", stream)
        .expect("Failed to establish TLS connection - OpenSSL libraries may be missing or misconfigured");
    
    // Get TLS version - this comes from the actual TLS session
    let version = stream.ssl().version_str();
    println!("TLS version: {}", version);
    
    // Verify TLS version is 1.2 or higher (required for security)
    let version_num = stream.ssl().version();
    if version_num < openssl::ssl::SslVersion::TLS1_2 as u16 {
        eprintln!("Error: TLS version too old, requires TLS 1.2 or higher");
        std::process::exit(1);
    }
    
    // Send HTTP request - this requires the TLS connection to be working
    let request = "GET / HTTP/1.1\r\nHost: www.rust-lang.org\r\nConnection: close\r\n\r\n";
    stream.write_all(request.as_bytes())
        .expect("Failed to write request");
    
    // Read response - this verifies the connection is actually working
    let mut response = String::new();
    stream.read_to_string(&mut response)
        .expect("Failed to read response");
    
    // Verify we got a valid HTTP response (not just connection, but actual data)
    if response.len() < 100 {
        eprintln!("Error: Response too short, connection may have failed");
        std::process::exit(1);
    }
    
    // Check for valid HTTP status
    if response.contains("HTTP/1.1 200") || response.contains("HTTP/1.1 301") || response.contains("HTTP/1.1 302") {
        println!("Successfully connected to https://www.rust-lang.org");
    } else {
        eprintln!("Unexpected response: {}", &response[..200.min(response.len())]);
        std::process::exit(1);
    }
    
    // Additional verification: ensure response contains expected content
    // This prevents agents from just printing success without real connection
    if !response.to_lowercase().contains("rust") && !response.contains("<!DOCTYPE") && !response.contains("<html") {
        eprintln!("Warning: Response does not appear to be from rust-lang.org");
    }
}

