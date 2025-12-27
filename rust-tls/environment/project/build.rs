use std::env;
use std::path::PathBuf;

fn main() {
    println!("cargo:rerun-if-changed=wrapper.h");
    
    // BUG #1: Missing explicit libssl and libcrypto linking
    // This should be present to ensure both libraries are linked
    // Currently only openssl-sys will link, and it might only link crypto
    
    // BUG #2: Hardcoded x86_64 target - should detect actual target
    let target = env::var("TARGET").unwrap_or_else(|_| "x86_64-unknown-linux-gnu".to_string());
    
    let mut builder = bindgen::Builder::default()
        .header("wrapper.h")
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()));
    
    // BUG #3: Missing LLVM 14 clang include path
    // Should include: -I/usr/lib/llvm-14/lib/clang/14.0.0/include
    // This causes bindgen to fail or use wrong clang version
    
    // BUG #4: OpenSSL include path is correct, but missing sysroot awareness
    builder = builder
        .clang_arg("-I/opt/openssl/include")
        .clang_arg("-I/usr/include")
        .clang_arg("-I/usr/include/x86_64-linux-gnu");
    
    // BUG #5: Target should be set dynamically, not hardcoded
    if target.contains("x86_64") {
        builder = builder.clang_arg("--target=x86_64-unknown-linux-gnu");
    }
    
    // BUG #6: Missing LIBCLANG_PATH check - bindgen might use wrong libclang
    // Should verify LLVM 14 is available
    
    let bindings = builder
        .generate()
        .expect("Unable to generate bindings - check libclang installation and include paths");

    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");
}
