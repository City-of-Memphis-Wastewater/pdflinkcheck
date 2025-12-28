use lopdf::{Document, Object, ObjectId};
use crate::types::{AnalysisResult, LinkRecord, TocEntry};

pub fn analyze_pdf(path: &str) -> Result<AnalysisResult, String> {
    let doc = Document::load(path)
        .map_err(|e| format!("Failed to open PDF: {:?}", e))?;

    let mut links = Vec::new();
    let mut toc = Vec::new();

    // -------------------------------
    // Extract TOC (Outlines)
    // -------------------------------
    if let Some(outlines) = extract_outlines(&doc) {
        toc = outlines;
    }

    // -------------------------------
    // Extract Link Annotations
    // -------------------------------
    for (page_num, page_id) in doc.get_pages().into_iter().enumerate() {
        if let Ok(page) = doc.get_object(page_id) {
            if let Some(annots) = page.as_dict().and_then(|d| d.get(b"Annots")) {
                if let Ok(annot_array) = annots.as_array() {
                    for annot_ref in annot_array {
                        if let Ok(annot_id) = annot_ref.as_reference() {
                            if let Ok(annot_obj) = doc.get_object(annot_id) {
                                if let Some(link) = parse_annotation(&doc, page_num as i32, annot_obj) {
                                    links.push(link);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(AnalysisResult { links, toc })
}

fn extract_outlines(doc: &Document) -> Option<Vec<TocEntry>> {
    let mut results = Vec::new();

    let catalog = doc.trailer.get(b"Root").ok()?.as_reference().ok()?;
    let catalog_dict = doc.get_object(catalog).ok()?.as_dict().ok()?;

    let outlines_ref = catalog_dict.get(b"Outlines")?.as_reference().ok()?;
    let outlines_dict = doc.get_object(outlines_ref).ok()?.as_dict().ok()?;

    let first = outlines_dict.get(b"First")?.as_reference().ok()?;
    let mut current = first;

    let mut level = 1;

    while let Ok(obj) = doc.get_object(current) {
        if let Some(dict) = obj.as_dict() {
            let title = dict.get(b"Title")
                .and_then(|t| t.as_str().ok())
                .unwrap_or("")
                .to_string();

            let dest_page = dict.get(b"Dest")
                .and_then(|d| d.as_array().ok())
                .and_then(|arr| arr.get(0))
                .and_then(|first| first.as_reference().ok())
                .and_then(|page_id| doc.get_page_number(page_id).ok())
                .unwrap_or(0);

            results.push(TocEntry {
                level,
                title,
                target_page: serde_json::json!(dest_page),
            });

            // Move to next outline item
            if let Some(next) = dict.get(b"Next").and_then(|n| n.as_reference().ok()) {
                current = next;
            } else {
                break;
            }
        } else {
            break;
        }
    }

    Some(results)
}

fn parse_annotation(doc: &Document, page_num: i32, annot_obj: &Object) -> Option<LinkRecord> {
    let dict = annot_obj.as_dict().ok()?;

    let subtype = dict.get(b"Subtype")?.as_name().ok()?;
    if subtype != b"Link" {
        return None;
    }

    let rect = dict.get(b"Rect")
        .and_then(|r| r.as_array().ok())
        .and_then(|arr| {
            if arr.len() == 4 {
                Some((
                    arr[0].as_f64().unwrap_or(0.0) as f32,
                    arr[1].as_f64().unwrap_or(0.0) as f32,
                    arr[2].as_f64().unwrap_or(0.0) as f32,
                    arr[3].as_f64().unwrap_or(0.0) as f32,
                ))
            } else {
                None
            }
        });

    let mut record = LinkRecord {
        page: page_num,
        rect,
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

    // Action dictionary
    if let Some(action) = dict.get(b"A").and_then(|a| a.as_dict().ok()) {
        if let Some(uri) = action.get(b"URI").and_then(|u| u.as_str().ok()) {
            record.url = Some(uri.to_string());
            record.action_kind = Some("URI".to_string());
        }

        if let Some(dest) = action.get(b"D").and_then(|d| d.as_array().ok()) {
            if let Some(page_ref) = dest.get(0).and_then(|o| o.as_reference().ok()) {
                if let Ok(page_num) = doc.get_page_number(page_ref) {
                    record.destination_page = Some(page_num as i32);
                    record.action_kind = Some("GoTo".to_string());
                }
            }
        }
    }

    Some(record)
}
