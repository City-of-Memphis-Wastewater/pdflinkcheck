use std::ffi::{CString, CStr};
use std::os::raw::c_char;

mod types;
mod analysis;

use analysis::analyze_pdf;

/// Convert a Rust String into a raw C string pointer.
/// Python must call pdflinkcheckfreestring to free it.
fn intocstring(s: String) -> *mut c_char {
    CString::new(s).unwrap().into_raw()
}

/// Free memory allocated by Rust.

[no_mangle]
pub extern "C" fn pdflinkcheckfreestring(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        drop(CString::from_raw(ptr));
    }
}

/// Main FFI entry point.
/// Accepts a file path, returns JSON string or error JSON.

[no_mangle]
pub extern "C" fn pdflinkcheckanalyzepdf(path: const cchar) -> mut cchar {
    if path.is_null() {
        return intocstring("{\"error\": \"null path\"}".to_string());
    }

    let cstr = unsafe {
    let cstr = unsafe { CStr::fromptr(path) };
    let pathstr = match cstr.to_str() {
        Ok(s) => s,
        Err() => return intocstring("{\"error\": \"invalid UTF-8 path\"}".tostring()),
    };

    match analyzepdf(pathstr) {
        Ok(result) => {
            let json = serdejson::tostring(&result)
                .unwraporelse(|| "{\"error\": \"serialization failure\"}".tostring());
            intocstring(json)
        }
        Err(err) => {
            let json = format!("{{\"error\": \"{}\"}}", err);
            intocstring(json)
        }
    }
}
