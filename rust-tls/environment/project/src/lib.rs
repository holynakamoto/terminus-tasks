// Minimal library that uses bindgen-generated bindings
include!(concat!(env!("OUT_DIR"), "/bindings.rs"));

pub fn get_process_id() -> i32 {
    unsafe { getpid() }
}

