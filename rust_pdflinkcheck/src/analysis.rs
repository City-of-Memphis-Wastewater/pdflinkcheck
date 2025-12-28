use crate::types::{AnalysisResult, LinkRecord, TocEntry};

/// MVP placeholder: returns empty results.
/// Step 2 will replace this with real PDF parsing using the pdf crate.
pub fn analyzepdf(path: &str) -> Result<AnalysisResult, String> {
    Ok(AnalysisResult {
        links: Vec::new(),
        toc: Vec::new(),
    })
}
