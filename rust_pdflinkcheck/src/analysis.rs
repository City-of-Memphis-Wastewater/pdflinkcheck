use pdf::file::File as PdfFile;
use pdf::object::*;
use pdf::error::PdfError;

use crate::types::{AnalysisResult, LinkRecord, TocEntry};

pub fn analyze_pdf(path: &str) -> Result<AnalysisResult, String> {
    let file = PdfFile::<Vec<u8>, Vec<u8>, Vec<u8>>::open(path)
        .map_err(|e| format!("Failed to open PDF: {:?}", e))?;

    let mut links = Vec::new();
    let mut toc = Vec::new();

    // -------------------------------
    // Extract TOC (Outlines)
    // -------------------------------
    if let Ok(outlines) = file.get_root().and_then(|root| root.outlines(&file)) {
        for item in outlines.items.iter() {
            let title = item.title.clone().unwrap_or_default();
            let level = item.level as i32;

            let target_page = match &item.dest {
                Some(Destination::Page { page, .. }) => {
                    serde_json::json!(page.get_page_number(&file).unwrap_or(0))
                }
                _ => serde_json::json!(null),
            };

            toc.push(TocEntry {
                level,
                title,
                target_page,
            });
        }
    }

    // -------------------------------
    // Extract Link Annotations
    // -------------------------------
    for (page_num, page) in file.pages().enumerate() {
        let page = page.map_err(|e| format!("Page error: {:?}", e))?;
        let annots = match page.annotations(&file) {
            Ok(a) => a,
            Err(_) => continue,
        };

        for annot in annots {
            if let Ok(annot) = annot {
                if let Some(action) = annot.action {
                    let mut record = LinkRecord {
                        page: page_num as i32,
                        rect: annot.rect.map(|r| (r.left, r.bottom, r.right, r.top)),
                        link_text: "".to_string(),
                        r#type: "link".to_string(),

                        url: None,
                        destination_page: None,
                        destination_view: None,
                        remote_file: None,
                        action_kind: None,
                        source_kind: None,
                        xref: None,
                    };

                    match action {
                        Action::Uri { uri } => {
                            record.url = Some(uri.clone());
                            record.action_kind = Some("URI".to_string());
                        }
                        Action::Goto { dest } => {
                            record.action_kind = Some("Goto".to_string());
                            if let Destination::Page { page, .. } = dest {
                                record.destination_page =
                                    Some(page.get_page_number(&file).unwrap_or(0) as i32);
                            }
                        }
                        Action::RemoteGoto { file: f, dest } => {
                            record.action_kind = Some("RemoteGoto".to_string());
                            record.remote_file = Some(f.clone());
                            if let Destination::Page { page, .. } = dest {
                                record.destination_page =
                                    Some(page.get_page_number(&file).unwrap_or(0) as i32);
                            }
                        }
                        _ => {
                            record.action_kind = Some("Other".to_string());
                        }
                    }

                    links.push(record);
                }
            }
        }
    }

    Ok(AnalysisResult { links, toc })
}
