use std::env;
use std::fs;
use std::io::{self, Read};

// Custom error type with intentional missing trait implementations
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

// Function with lifetime issues - returns reference to local data
fn get_json_source<'a>(args: &Vec<String>) -> &'a str {
    if args.len() > 1 {
        let file_content = fs::read_to_string(&args[1])
            .expect("Failed to read file");
        &file_content  // ERROR: returns reference to local variable
    } else {
        let mut buffer = String::new();
        io::stdin().read_to_string(&mut buffer)
            .expect("Failed to read from stdin");
        &buffer  // ERROR: returns reference to local variable
    }
}

// Function that panics on invalid UTF-8 instead of handling errors
fn process_bytes(data: &[u8]) -> String {
    // This will panic if data is not valid UTF-8
    std::str::from_utf8(data).unwrap().to_string()
}

// Function with trait bound issues
fn print_error<T>(err: T) {
    // ERROR: T doesn't have Display trait bound
    println!("Error: {}", err);
}

fn parse_and_format(json_str: &str) -> Result<String, ParseError> {
    match serde_json::from_str::<serde_json::Value>(json_str) {
        Ok(value) => {
            match serde_json::to_string_pretty(&value) {
                Ok(formatted) => Ok(formatted),
                Err(_) => Err(ParseError::new("Failed to format JSON")),
            }
        }
        Err(_) => Err(ParseError::new("Invalid JSON syntax")),
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();

    // Get JSON source with lifetime issues
    let json_input = get_json_source(&args);

    // Process with potential UTF-8 panic
    let json_bytes = json_input.as_bytes();
    let json_str = process_bytes(json_bytes);

    // Parse and format
    match parse_and_format(&json_str) {
        Ok(formatted) => println!("{}", formatted),
        Err(e) => {
            // This won't compile due to missing Display trait
            print_error(e);
            std::process::exit(1);
        }
    }
}
