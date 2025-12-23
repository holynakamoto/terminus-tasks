// Minimal library that uses bindgen-generated bindings.
//
// `bindgen` output commonly triggers Rust style lints (e.g. non_camel_case_types,
// non_upper_case_globals). We keep those warnings scoped to the generated module
// so your crate can still be lint-clean elsewhere.
#[allow(non_camel_case_types, non_snake_case, non_upper_case_globals)]
mod bindings {
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
}

// Re-export the generated symbols at the crate root so downstream code/tests
// keep working without changes.
pub use bindings::*;

pub fn get_process_id() -> i32 {
    unsafe { getpid() }
}
