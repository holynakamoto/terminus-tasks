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

    // Send HTTP request - this requires the TLS connection to be working
    // Include realistic headers to avoid some CDNs closing the connection early.
    let request = concat!(
        "GET / HTTP/1.1\r\n",
        "Host: www.rust-lang.org\r\n",
        "User-Agent: tls-example/0.1 (openssl)\r\n",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n",
        "Accept-Language: en-US,en;q=0.5\r\n",
        "Connection: close\r\n",
        "\r\n"
    );

    eprintln!("DEBUG: Sending HTTP request...");
    stream
        .write_all(request.as_bytes())
        .expect("Failed to write request");
    stream.flush().expect("Failed to flush request");
    eprintln!("DEBUG: Request sent, waiting for response...");

    // Read response as raw bytes to handle arbitrary payloads and avoid UTF-8 assumptions.
    // Some servers may close early or send bytes that aren't valid UTF-8.
    let mut response_bytes: Vec<u8> = Vec::new();
    stream
        .read_to_end(&mut response_bytes)
        .expect("Failed to read response");
    eprintln!("DEBUG: Response received, {} bytes", response_bytes.len());

    // Verify we got a response (not just a handshake).
    if response_bytes.is_empty() {
        eprintln!("Error: Response too short, connection may have failed");
        std::process::exit(1);
    }

    // Decode lossily for inspection/printing.
    let response = String::from_utf8_lossy(&response_bytes);

    // Check for valid HTTP status
    if response.contains("HTTP/1.1 200")
        || response.contains("HTTP/1.1 301")
        || response.contains("HTTP/1.1 302")
    {
        println!("Successfully connected to https://www.rust-lang.org");
    } else {
        let preview = &response[..200.min(response.len())];
        eprintln!("Unexpected response: {}", preview);
        std::process::exit(1);
    }

    // Additional verification: ensure response contains expected content
    // This prevents agents from just printing success without real connection
    if !response.to_lowercase().contains("rust") && !response.contains("<!DOCTYPE") && !response.contains("<html") {
        eprintln!("Warning: Response does not appear to be from rust-lang.org");
    }

    // Print the response (tests require this to verify real connection)
    println!("\n{}", response);
}
