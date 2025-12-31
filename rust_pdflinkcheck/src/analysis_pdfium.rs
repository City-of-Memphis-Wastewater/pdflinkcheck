// analysis_pdfium.rs
use pdfium_render::prelude::*;
use crate::types::{AnalysisResult, LinkRecord, TocEntry};

pub fn analyze_pdf(path: &str) -> Result<AnalysisResult, String> {
    //let bindings = Pdfium::bind_to_system_library().map_err(|e| format!("{:?}", e))?;
    //let pdfium = Pdfium::new(bindings);

    // This consolidated logic handles the binding in one go
    let pdfium = Pdfium::new(
        Pdfium::bind_to_library(Pdfium::pdfium_platform_library_name_at_path("./"))
            .or_else(|_| Pdfium::bind_to_system_library())
            .map_err(|e| format!("Could not find libpdfium.so in ./ or system: {:?}", e))?
    );

    let doc = pdfium.load_pdf_from_file(path, None)
        .map_err(|e| format!("Failed to open PDF: {:?}", e))?;

    let mut links = Vec::new();
    let mut toc = Vec::new();

    // 1. TOC Extraction
    for b in doc.bookmarks().iter() {
        walk_bookmarks(&b, 1, &mut toc); // Levels usually start at 1
    }

    for (page_index, page) in doc.pages().iter().enumerate() {
        let page_num = page_index as i32;
        let text_page = page.text().ok();

        for annot in page.annotations().iter() {
            let rect = match annot.bounds() {
                Ok(r) => r,
                Err(_) => continue,
            };

            // FIX: Added 'ref' to avoid moving out of the annotation iterator
            if let PdfPageAnnotation::Link(ref link_annot) = annot {
                let mut record = LinkRecord {
                    page: page_num,
                    rect: Some((rect.left().value, rect.bottom().value, rect.right().value, rect.top().value)),
                    link_text: String::new(),
                    r#type: "link".to_string(),
                    url: None,
                    destination_page: None,
                    destination_view: None,
                    remote_file: None,
                    action_kind: None,
                    source_kind: Some("pdfium".to_string()),
                    xref: None,
                };

                if let Ok(link) = link_annot.link() {
                    if let Some(action) = link.action() {
                        match action {
                            PdfAction::Uri(uri_action) => {
                                record.url = uri_action.uri().ok();
                                record.action_kind = Some("URI".to_string());
                            }
                            PdfAction::LocalDestination(nav_action) => {
                                if let Ok(dest) = nav_action.destination() {
                                    if let Ok(idx) = dest.page_index() {
                                        record.destination_page = Some(idx as i32);
                                    }
                                }
                                record.action_kind = Some("GoTo".to_string());
                            }
                            _ => {
                                record.action_kind = Some("Other".to_string());
                            }
                        }
                    }
                }

                // 2. Text Extraction
                if let Some(ref tp) = text_page {
                    if let Ok(extracted_text) = tp.for_annotation(&annot) {
                        record.link_text = extracted_text.trim().to_string();
                    }
                }

                links.push(record);
            }
        }
    }

    Ok(AnalysisResult { links, toc })
}


// Helper for recursive TOC extraction
fn walk_bookmarks(bookmark: &PdfBookmark, level: i32, toc: &mut Vec<TocEntry>) {
    let title = bookmark.title().unwrap_or_default();
    let target_page = bookmark.destination()
        .and_then(|d| d.page_index().ok())
        .unwrap_or(0) as i32;

    toc.push(TocEntry {
        level,
        title,
        target_page: serde_json::json!(target_page),
    });

    // Handle children via first_child() and next_sibling()
    if let Some(mut current_child) = bookmark.first_child() {
        walk_bookmarks(&current_child, level + 1, toc);

        // Traverse siblings
        while let Some(sibling) = current_child.next_sibling() {
            walk_bookmarks(&sibling, level + 1, toc);
            current_child = sibling;
        }
    }
}
