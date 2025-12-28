from pdflinkcheck import ffi

print("Rust available:", ffi.rust_available())

try:
    result = ffi.analyze_pdf_rust("temOM.pdf")
    print("Rust result:", result)
except Exception as e:
    print("Rust error:", e)
