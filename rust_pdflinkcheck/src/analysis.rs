use pdfium_render::prelude::*;
use crate::types::{AnalysisResult, LinkRecord, TocEntry};

pub fn analyze_pdf(path: &str) -> Result<AnalysisResult, String> {
    let bindings = Pdfium::bind_to_system_library().map_err(|e| format!("{:?}", e))?;
    let pdfium = Pdfium::new(bindings);

    let doc = pdfium.load_pdf_from_file(path, None)
        .map_err(|e| format!("Failed to open PDF: {:?}", e))?;

    let mut links = Vec::new();
    let mut toc = Vec::new();

    // 1. TOC Extraction
    for b in doc.bookmarks().iter() {
        let title = b.title().unwrap_or_default();
        let target_page = b.destination()
            .and_then(|d| d.page_index().ok())
            .unwrap_or(0) as i32;

        toc.push(TocEntry {
            level: 0, 
            title,
            target_page: serde_json::json!(target_page),
        });
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
