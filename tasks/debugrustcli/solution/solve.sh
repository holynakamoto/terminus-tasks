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
        // Read file and handle errors properly (including invalid UTF-8)
        fs::read_to_string(&args[1])
            .map_err(|e| {
                // Check if it's a UTF-8 error
                if e.kind() == io::ErrorKind::InvalidData {
                    ParseError::new("Invalid UTF-8 in input")
                } else {
                    ParseError::new(&format!("Failed to read file '{}': {}", args[1], e))
                }
            })
    } else {
        // Read from stdin and handle errors properly (including invalid UTF-8)
        let mut buffer = String::new();
        io::stdin()
            .read_to_string(&mut buffer)
            .map_err(|e| {
                // Check if it's a UTF-8 error
                if e.kind() == io::ErrorKind::InvalidData {
                    ParseError::new("Invalid UTF-8 in input")
                } else {
                    ParseError::new(&format!("Failed to read from stdin: {}", e))
                }
            })?;
        Ok(buffer)
    }
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

    // Get JSON source with proper error handling (including UTF-8 validation)
    let json_input = match get_json_source(&args) {
        Ok(input) => input,
        Err(e) => {
            print_error(e);
            std::process::exit(1);
        }
    };

    // Parse and format with proper error handling
    match parse_and_format(&json_input) {
        Ok(formatted) => println!("{}", formatted),
        Err(e) => {
            print_error(e);
            std::process::exit(1);
        }
    }
}
EOF

echo "=== Cleaning previous build artifacts ==="
cargo clean

echo "=== Building the fixed code ==="
cargo build --release

echo "=== Solution applied successfully ==="
echo "Binary built at: /app/target/release/json-parser"
