#!/bin/bash
set -euo pipefail

echo "=== Fixing Rust JSON Parser Compilation Errors ==="

cd /app

# Create the fixed version of main.rs
cat > src/main.rs << 'EOF'
use std::env;
use std::fs;
use std::io::{self, Read};
use std::fmt;

// Custom error type with proper trait implementations
#[derive(Debug)]
struct ParseError {
    message: String,
}

impl ParseError {
    fn new(msg: &str) -> Self {
        ParseError {
            message: msg.to_string(),
        }
    }
}

// Implement Display trait for ParseError
impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

// Implement std::error::Error trait for ParseError
impl std::error::Error for ParseError {}

// Function that returns owned String instead of reference
// Fixed: Returns String instead of &str to avoid lifetime issues
fn get_json_source(args: &Vec<String>) -> Result<String, ParseError> {
    if args.len() > 1 {
        // Read file and handle errors properly
        fs::read_to_string(&args[1])
            .map_err(|e| ParseError::new(&format!("Failed to read file '{}': {}", args[1], e)))
    } else {
        // Read from stdin and handle errors properly
        let mut buffer = String::new();
        io::stdin()
            .read_to_string(&mut buffer)
            .map_err(|e| ParseError::new(&format!("Failed to read from stdin: {}", e)))?;
        Ok(buffer)
    }
}

// Function that handles UTF-8 errors gracefully
fn validate_utf8(data: &[u8]) -> Result<String, ParseError> {
    std::str::from_utf8(data)
        .map(|s| s.to_string())
        .map_err(|_| ParseError::new("Invalid UTF-8 in input"))
}

// Function with proper trait bound (Display)
fn print_error<T: fmt::Display>(err: T) {
    eprintln!("Error: {}", err);
}

fn parse_and_format(json_str: &str) -> Result<String, ParseError> {
    match serde_json::from_str::<serde_json::Value>(json_str) {
        Ok(value) => {
            match serde_json::to_string_pretty(&value) {
                Ok(formatted) => Ok(formatted),
                Err(e) => Err(ParseError::new(&format!("Failed to format JSON: {}", e))),
            }
        }
        Err(e) => Err(ParseError::new(&format!("Invalid JSON: {}", e))),
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();

    // Get JSON source with proper error handling
    let json_input = match get_json_source(&args) {
        Ok(input) => input,
        Err(e) => {
            print_error(e);
            std::process::exit(1);
        }
    };

    // Validate UTF-8 with proper error handling (though String is already UTF-8)
    // This is redundant for String but shows the concept
    let json_bytes = json_input.as_bytes();
    let json_str = match validate_utf8(json_bytes) {
        Ok(s) => s,
        Err(e) => {
            print_error(e);
            std::process::exit(1);
        }
    };

    // Parse and format with proper error handling
    match parse_and_format(&json_str) {
        Ok(formatted) => println!("{}", formatted),
        Err(e) => {
            print_error(e);
            std::process::exit(1);
        }
    }
}
EOF

echo "=== Building the fixed code ==="
cargo build --release

echo "=== Testing the fix ==="

# Test 1: Valid JSON from stdin
echo "Test 1: Valid JSON from stdin"
echo '{"name":"Alice","age":30}' | ./target/release/json-parser

# Test 2: Invalid JSON
echo "Test 2: Invalid JSON (should show error)"
echo '{invalid}' | ./target/release/json-parser || echo "Correctly handled error"

# Test 3: File input
echo "Test 3: File input"
echo '{"test":true}' > /tmp/test.json
./target/release/json-parser /tmp/test.json

# Test 4: Invalid UTF-8 (simulate by creating a file with invalid UTF-8)
echo "Test 4: Invalid UTF-8 in file (should handle gracefully)"
printf '\xff\xfe{"test":true}' > /tmp/bad_utf8.json
./target/release/json-parser /tmp/bad_utf8.json || echo "Correctly handled UTF-8 error"

echo "=== All fixes applied and tested successfully ==="
