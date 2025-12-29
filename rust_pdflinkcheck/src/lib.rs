use std::ffi::{CString, CStr};
use std::os::raw::c_char;

mod types;
/// mod analysis;
mod analysis_lopdf;  

///use analysis::analyze_pdf;
use analysis_lopdf::{extract_pdf_data, LinkInfo, TocEntry};

/// Convert a Rust String into a raw C string pointer.
/// Python must call `pdflinkcheck_free_string` to free it.
fn into_c_string(s: String) -> *mut c_char {
    CString::new(s).unwrap().into_raw()
}

/// Free memory allocated by Rust.
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
/// Accepts a file path, returns JSON string or error JSON.
#[no_mangle]
pub extern "C" fn pdflinkcheck_analyze_pdf(path: *const c_char) -> *mut c_char {
    if path.is_null() {
        return into_c_string("{\"error\": \"null path\"}".to_string());
    }

    // Convert C string to Rust string
    let cstr = unsafe { CStr::from_ptr(path) };
    let path_str = match cstr.to_str() {
        Ok(s) => s,
        Err(_) => {
            return into_c_string("{\"error\": \"invalid UTF-8 path\"}".to_string());
        }
    };

    // Run analysis
    let result = analyze_pdf(path_str);

    // Convert to JSON
    let json = match result {
        Ok(val) => serde_json::to_string(&val)
            .unwrap_or_else(|_| "{\"error\": \"serialization failure\"}".to_string()),
        Err(err) => format!("{{\"error\": \"{}\"}}", err),
    };

    into_c_string(json)
}
