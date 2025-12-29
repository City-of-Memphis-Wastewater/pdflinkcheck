// src/lib.rs

use std::ffi::{CString, CStr};
use std::os::raw::c_char;

mod types;
mod analysis_lopdf;

use analysis_lopdf::{extract_pdf_data, LinkInfo, TocEntry};

/// Convert a Rust String into a raw C string pointer.
/// Python must call `pdflinkcheck_free_string` to free it.
fn into_c_string(s: String) -> *mut c_char {
    // We unwrap here because paths and JSON should always be valid UTF-8
    // If not, the caller will get an error anyway
    CString::new(s).unwrap().into_raw()
}

/// Free memory allocated by Rust (for Python to call).
#[no_mangle]
pub extern "C" fn pdflinkcheck_free_string(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        drop(CString::from_raw(ptr));
    }
}

/// Main FFI entry point.
/// Accepts a file path as C string, returns JSON string (must be freed by caller).
#[no_mangle]
pub extern "C" fn pdflinkcheck_analyze_pdf(path: *const c_char) -> *mut c_char {
    if path.is_null() {
        return into_c_string(r#"{"status":"error","error":"null path"}"#.to_string());
    }

    // Convert C string to Rust string
    let cstr = unsafe { CStr::from_ptr(path) };
    let path_str = match cstr.to_str() {
        Ok(s) => s,
        Err(_) => {
            return into_c_string(r#"{"status":"error","error":"invalid UTF-8 path"}"#.to_string());
        }
    };

    // Run the pure-Rust analysis
    let result = extract_pdf_data(std::path::Path::new(path_str));

    // Build JSON response
    let json = match result {
        Ok((links, toc)) => serde_json::json!({
            "status": "success",
            "links": links,
            "toc": toc
        })
        .to_string(),
        Err(e) => serde_json::json!({
            "status": "error",
            "error": e.to_string()
        })
        .to_string(),
    };

    into_c_string(json)
}
