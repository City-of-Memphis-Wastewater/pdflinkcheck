// Instead of 'use rust_pdflinkcheck...', 
// we use the package name directly.
use rust_pdflinkcheck::analyze_pdf;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <pdf_path>", args[0]);
        std::process::exit(1);
    }

    match analyze_pdf(&args[1]) {
        Ok(result) => {
            if let Ok(json) = serde_json::to_string_pretty(&result) {
                println!("{}", json);
            }
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}
