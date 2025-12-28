fn main() -> anyhow::Result<()> {
    let pdf_path = std::env::args().nth(1).expect("Provide PDF path");
    let (links, toc) = analysis_lopdf::extract_pdf_data(std::path::Path::new(&pdf_path))?;

    println!("Found {} links:", links.len());
    for link in links {
        println!("Page {} | {} | {} | {}", link.page, link.link_type, link.target, link.link_text);
    }

    println!("\nTOC:");
    for entry in toc {
        println!("{} - {} (Page {:?})", entry.level, entry.title, entry.target_page);
    }

    Ok(())
}
