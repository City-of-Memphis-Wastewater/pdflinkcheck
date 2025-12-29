mod types;
mod analysis;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        println!("Usage: cargo run -- <path_to_pdf>");
        return;
    }

    match analysis::analyze_pdf(&args[1]) {
        Ok(result) => println!("{}", serde_json::to_string_pretty(&result).unwrap()),
        Err(e) => eprintln!("Error: {}", e),
    }
}
