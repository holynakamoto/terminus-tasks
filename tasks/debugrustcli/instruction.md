# Rust JSON Parser Debugging Challenge

## Overview

You are given a broken Rust CLI application that is supposed to parse and pretty-print JSON data. The application currently **fails to compile** due to multiple errors and would panic at runtime even if it compiled. Your task is to debug and fix all issues to make it work correctly.

## The Problem

The `json-parser` CLI tool is located in `/app` and is intended to:
1. Accept JSON input either from a file argument or from stdin
2. Parse the JSON and validate it
3. Pretty-print the formatted JSON to stdout
4. Handle errors gracefully with user-friendly messages

**Current State:**
- ❌ **Does not compile** - Multiple compilation errors including:
  - Lifetime errors (returning references to local data)
  - Missing trait bounds (Display trait not implemented)
- ❌ **Panics on invalid UTF-8** - Uses `unwrap()` instead of proper error handling
- ❌ **Poor error handling** - Missing proper error propagation and user-friendly messages

## Your Objectives

### 1. Fix All Compilation Errors

The code has several compilation errors that must be resolved:

**Lifetime Issues:**
- The `get_json_source` function attempts to return references to local variables
- This violates Rust's ownership rules and will not compile
- You need to return owned data instead of references

**Trait Bound Errors:**
- The `print_error` function is missing required trait bounds
- Custom error types need to implement necessary traits (Display, Debug)
- Generic functions must specify their requirements

### 2. Add Robust Error Handling

Replace all instances of `unwrap()` and `expect()` with proper error handling:

**IO Error Handling:**
- File reading may fail (file not found, permission denied, etc.)
- stdin reading may fail
- These should return clear error messages, not panic

**UTF-8 Validation:**
- Invalid UTF-8 sequences should be handled gracefully
- The current `process_bytes` function will panic on invalid UTF-8
- Replace with proper error handling that returns a user-friendly message

**JSON Parse Errors:**
- Invalid JSON syntax should produce helpful error messages
- Currently returns generic "Invalid JSON syntax" - should include details
- Use the error information from serde_json

### 3. Ensure Correct Behavior

After fixing the errors, the program must:

**For valid JSON input:**
```bash
$ echo '{"name":"Alice","age":30}' | /app/target/release/json-parser
{
  "age": 30,
  "name": "Alice"
}
```

**For invalid JSON:**
```bash
$ echo '{invalid}' | /app/target/release/json-parser
Error: Invalid JSON: expected value at line 1 column 2
$ echo $?
1
```

**For file input:**
```bash
$ /app/target/release/json-parser /tmp/test.json
{
  "formatted": "output"
}
```

**For invalid UTF-8:**
```bash
$ echo -n -e '\xff\xfe' | /app/target/release/json-parser
Error: Invalid UTF-8 in input
$ echo $?
1
```

**For missing file:**
```bash
$ /app/target/release/json-parser /nonexistent/file.json
Error: Failed to read file '/nonexistent/file.json': No such file or directory
$ echo $?
1
```

## Project Structure

- The Rust project is located in `/app`
- Source code: `/app/src/main.rs`
- Dependencies: `/app/Cargo.toml`
- Build the release binary with: `cargo build --release`
- Binary location: `/app/target/release/json-parser`

## Requirements

### Compilation
- ✅ Code must compile without errors or warnings
- ✅ Use `cargo build --release` to build
- ✅ No unsafe code or workarounds - fix the actual issues

### Error Handling
- ✅ No `unwrap()` or `expect()` in production code
- ✅ All errors must be handled with `Result` types
- ✅ Error messages must start with "Error: " followed by a descriptive message
- ✅ Program must exit with non-zero status on errors

### Functionality
- ✅ Accept JSON from stdin (no arguments) or from file (first argument)
- ✅ Pretty-print valid JSON with proper indentation
- ✅ Handle invalid JSON with clear error messages
- ✅ Handle invalid UTF-8 gracefully (no panics)
- ✅ Handle file IO errors gracefully (no panics)

### Code Quality
- ✅ Proper use of Rust ownership and borrowing
- ✅ Appropriate trait implementations (Display, Debug for error types)
- ✅ Clean, idiomatic Rust code

## Debugging Tips

### Understanding Compilation Errors

**Lifetime errors:**
```text
error[E0515]: cannot return reference to local variable `file_content`
```
This means you're trying to return a reference to data that will be dropped when the function returns. You need to return owned data instead.

**Trait bound errors:**
```text
error[E0277]: `ParseError` doesn't implement `std::fmt::Display`
```
Your custom error type needs to implement the Display trait to be printed.

### Testing Your Solution

1. **First, make it compile:**
   ```bash
   cd /app
   cargo build --release
   ```

2. **Test with valid JSON:**
   ```bash
   echo '{"key":"value"}' | ./target/release/json-parser
   ```

3. **Test with invalid JSON:**
   ```bash
   echo '{bad json}' | ./target/release/json-parser
   ```

4. **Test with invalid UTF-8:**
   ```bash
   printf '\xff\xfe' | ./target/release/json-parser
   ```

5. **Test with file input:**
   ```bash
   echo '{"test":true}' > /tmp/test.json
   ./target/release/json-parser /tmp/test.json
   ```

### Common Fixes Needed

1. **Return owned String instead of &str** in `get_json_source`
2. **Implement Display and Debug traits** for ParseError
3. **Use proper error types** - consider using a Result type alias
4. **Replace unwrap() calls** with proper error propagation using `?` operator
5. **Handle UTF-8 errors** using `from_utf8` that returns Result
6. **Include error context** in error messages (e.g., filename, JSON parse details)

## Success Criteria

Your solution is complete when:

- ✅ `cargo build --release` compiles successfully with no errors or warnings
- ✅ All provided tests pass
- ✅ Valid JSON is pretty-printed correctly
- ✅ Invalid JSON produces error messages starting with "Error: "
- ✅ Invalid UTF-8 is handled gracefully (no panics)
- ✅ File IO errors are handled gracefully (no panics)
- ✅ The program exits with status 1 on any error
- ✅ The program exits with status 0 on success

## Hints

<details>
<summary>Click to reveal hints</summary>

**Hint 1:** For the lifetime issue, instead of returning `&'a str`, return `String` (owned data).

**Hint 2:** Implement `std::fmt::Display` and `std::fmt::Debug` for `ParseError`:
```rust
impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}
```

**Hint 3:** For UTF-8 handling, use the `?` operator:
```rust
let json_str = std::str::from_utf8(data)
    .map_err(|_| ParseError::new("Invalid UTF-8 in input"))?;
```

**Hint 4:** Add trait bounds to generic functions:
```rust
fn print_error<T: std::fmt::Display>(err: T) {
    eprintln!("Error: {}", err);
}
```

**Hint 5:** Use `map_err` to add context to errors:
```rust
fs::read_to_string(&path)
    .map_err(|e| format!("Failed to read file '{}': {}", path, e))
```

</details>
