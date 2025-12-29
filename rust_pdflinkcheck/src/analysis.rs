use pdfium_render::prelude::*;
use crate::types::{AnalysisResult, LinkRecord, TocEntry};

pub fn analyze_pdf(path: &str) -> Result<AnalysisResult, String> {
    let bindings = Pdfium::bind_to_system_library().map_err(|e| format!("{:?}", e))?;
    let pdfium = Pdfium::new(bindings);

    let doc = pdfium.load_pdf_from_file(path, None)
        .map_err(|e| format!("Failed to open PDF: {:?}", e))?;

    let mut links = Vec::new();
    let mut toc = Vec::new();

    // TOC
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
            // 1. Get the bounding box safely
            let rect = match annot.bounds() {
                Ok(r) => r,
                Err(_) => continue,
            };

            if let PdfPageAnnotation::Link(link_annot) = annot {
                let mut record = LinkRecord {
                    page: page_num,
                    rect: Some((rect.left.value, rect.bottom.value, rect.right.value, rect.top.value)),
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

                // 2. Access action via the link annotation
                if let Some(action) = link_annot.action() {
                    match action.action_type() {
                        PdfActionType::Uri => {
                            record.url = action.uri();
                            record.action_kind = Some("URI".to_string());
                        }
                        _ => {
                            if let Some(dest) = action.destination() {
                                if let Ok(idx) = dest.page_index() {
                                    record.destination_page = Some(idx as i32);
                                }
                                record.action_kind = Some("GoTo".to_string());
                            }
                        }
                    }
                }

                // 3. Extract text specifically for this annotation
                if let Some(ref tp) = text_page {
                    // pdfium-render 0.8.x uses for_annotation
                    record.link_text = tp.for_annotation(&link_annot).trim().to_string();
                }

                links.push(record);
            }
        }
    }

    Ok(AnalysisResult { links, toc })
}
