use pdfium_render::prelude::*;
use crate::types::{AnalysisResult, LinkRecord, TocEntry};

pub fn analyze_pdf(path: &str) -> Result<AnalysisResult, String> {
    // Configure PDFium (in Windows Store packaging you'll ship the dll)
    let bindings = Pdfium::bind_to_system_library().map_err(|e| format!("{:?}", e))?;
    let pdfium = Pdfium::new(bindings);

    let doc = pdfium.load_pdf_from_file(path, None)
        .map_err(|e| format!("Failed to open PDF: {:?}", e))?;

    let mut links = Vec::new();
    let mut toc = Vec::new();

    // -------------------------------
    // TOC (bookmarks)
    // -------------------------------
    if let Ok(bookmarks) = doc.bookmarks() {
        for b in bookmarks.list() {
            let level = b.level() as i32;
            let title = b.title().unwrap_or_default();
            let target_page = b
                .destination()
                .and_then(|d| d.page_index())
                .unwrap_or(0) as i32;

            toc.push(TocEntry {
                level,
                title,
                target_page: serde_json::json!(target_page),
            });
        }
    }

    // -------------------------------
    // Links per page
    // -------------------------------
    for (page_index, page) in doc.pages().iter().enumerate() {
        let page_num = page_index as i32;
        let width = page.width();
        let height = page.height();

        // Render a text page for link text extraction
        let text_page = page.text().ok();

        if let Ok(annots) = page.annotations() {
            for annot in annots {
                if annot.subtype() != PdfPageAnnotationType::Link {
                    continue;
                }

                let rect = annot.rect().unwrap_or(PdfRect::new(0.0, 0.0, 0.0, 0.0));

                let mut record = LinkRecord {
                    page: page_num,
                    rect: Some((rect.left as f32, rect.bottom as f32,
                                rect.right as f32, rect.top as f32)),
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

                // Action: URL / GoTo / GoToR
                if let Some(action) = annot.action() {
                    match action.action_type() {
                        PdfActionType::Uri => {
                            record.url = action.uri().map(|u| u.to_string());
                            record.action_kind = Some("URI".to_string());
                        }
                        PdfActionType::GoTo => {
                            if let Some(dest) = action.destination() {
                                if let Some(idx) = dest.page_index() {
                                    record.destination_page = Some(idx as i32);
                                }
                                record.action_kind = Some("GoTo".to_string());
                            }
                        }
                        PdfActionType::GoToRemote => {
                            if let Some(file) = action.remote_file() {
                                record.remote_file = Some(file.clone());
                            }
                            if let Some(dest) = action.destination() {
                                if let Some(idx) = dest.page_index() {
                                    record.destination_page = Some(idx as i32);
                                }
                            }
                            record.action_kind = Some("GoToR".to_string());
                        }
                        _ => {
                            record.action_kind = Some("Other".to_string());
                        }
                    }
                }

                // Extract text inside the link rectangle
                if let Some(text_page) = &text_page {
                    if let Ok(text) = text_page.text_in_rect(
                        rect.left,
                        rect.bottom,
                        rect.right,
                        rect.top,
                    ) {
                        record.link_text = text.trim().to_string();
                    }
                }

                links.push(record);
            }
        }
    }

    Ok(AnalysisResult { links, toc })
}
