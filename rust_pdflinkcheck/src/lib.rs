// lib.rs
use std::ffi::{CString, CStr};
use std::os::raw::c_char;

pub mod types;
pub mod analysis_pdfium;

// Re-export once for both internal and external use
pub use crate::analysis_pdfium::analyze_pdf;

fn into_c_string(s: String) -> *mut c_char {
    CString::new(s).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn pdflinkcheck_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe { drop(CString::from_raw(ptr)); }
    }
}

#[no_mangle]
pub extern "C" fn pdflinkcheck_analyze_pdf(path: *const c_char) -> *mut c_char {
    if path.is_null() {
        return into_c_string("{\"error\": \"null path\"}".to_string());
    }
    let cstr = unsafe { CStr::from_ptr(path) };
    let path_str = match cstr.to_str() {
        Ok(s) => s,
        Err(_) => return into_c_string("{\"error\": \"invalid UTF-8 path\"}".to_string()),
    };

    let result = analyze_pdf(path_str);
    let json = match result {
        Ok(val) => serde_json::to_string(&val).unwrap_or_default(),
        Err(err) => format!("{{\"error\": \"{}\"}}", err),
    };
    into_c_string(json)
}
