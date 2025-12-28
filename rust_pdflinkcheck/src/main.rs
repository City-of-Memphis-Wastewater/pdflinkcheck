mod analysis_lopdf;

fn main() -> anyhow::Result<()> {
    let path = std::env::args().nth(1).expect("PDF path");
    let (links, toc) = analysis_lopdf::extract_pdf_data(std::path::Path::new(&path))?;
    println!("Links: {:#?}", links);
    println!("TOC: {:#?}", toc);
    Ok(())
}
