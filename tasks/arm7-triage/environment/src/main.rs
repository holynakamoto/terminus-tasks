use std::env;
use flate2::Compression;
use flate2::write::GzEncoder;
use std::io::Write;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() != 2 {
        eprintln!("Usage: {} <number>", args[0]);
        std::process::exit(1);
    }

    let input: i32 = match args[1].parse() {
        Ok(n) => n,
        Err(_) => {
            eprintln!("Error: '{}' is not a valid integer", args[1]);
            std::process::exit(1);
        }
    };

    let result = input * 2;

    // Use zlib compression to ensure the binary links against libz.so.1
    // This is required for the cross-compilation test to verify pkg-config setup
    let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
    let _ = encoder.write_all(b"zlib-test");
    let _ = encoder.finish();

    println!("Result: {}", result);
}

