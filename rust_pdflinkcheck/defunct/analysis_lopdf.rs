// src/analysis_lopdf.rs

use anyhow::{Context, Result};
use lopdf::{Document, Object, ObjectId};
use pdf_extract::{output_doc, PagePlainTextOutput};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, serde::Serialize)]
pub struct LinkInfo {
    pub page: u32,              // 1-based
    pub rect: Vec<f64>,
    pub link_text: String,
    pub link_type: String,
    pub target: String,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct TocEntry {
    pub level: usize,
    pub title: String,
    pub target_page: Option<u32>,
}

pub fn extract_pdf_data(pdf_path: &Path) -> Result<(Vec<LinkInfo>, Vec<TocEntry>)> {
    let doc = Document::load(pdf_path).context("Failed to load PDF")?;

    let mut obj_id_to_page: HashMap<ObjectId, u32> = HashMap::new();
    for (i, (page_id, _gen)) in doc.get_pages().iter().enumerate() {
        obj_id_to_page.insert(*page_id, (i + 1) as u32);
    }

    let links = extract_links(&doc, &obj_id_to_page)?;
    let toc = extract_toc(&doc, &obj_id_to_page)?;

    Ok((links, toc))
}

fn extract_links(doc: &Document, id_to_page: &HashMap<ObjectId, u32>) -> Result<Vec<LinkInfo>> {
    let mut links = Vec::new();

    for (page_num, (page_id, _gen)) in doc.get_pages().iter().enumerate() {
        let page_obj = doc.get_object(*page_id)?;
        let annots = match page_obj.as_dict()?.get(b"Annots") {
            Ok(Object::Array(arr)) => arr,
            _ => continue,
        };

        // Extract whole-page text (pdf-extract 0.10 limitation: no bbox)
        let mut text_output = PagePlainTextOutput::new();
        output_doc(doc, &mut text_output).context("Text extraction failed")?;

        // For now: fallback to full page text for each link (not ideal)
        let page_text = text_output.text.trim().to_string();

        for annot_ref in annots {
            let annot = doc.get_object(annot_ref.as_reference()?)?;
            let annot_dict = annot.as_dict()?;

            if annot_dict.get(b"Subtype")?.as_name()? != b"Link" {
                continue;
            }

            let rect_obj = annot_dict.get(b"Rect")?.as_array()?;
            let rect: Vec<f64> = rect_obj.iter().map(|o| o.as_float().unwrap_or(0.0) as f64).collect();
            if rect.len() != 4 { continue; }

            let mut link_type = "Other Action".to_string();
            let mut target = "Unknown".to_string();

            // URI
            if let Ok(action) = annot_dict.get(b"A") {
                if let Ok(act_dict) = action.as_dict() {
                    if let Ok(s) = act_dict.get(b"S") {
                        if s.as_name()? == b"URI" {
                            if let Ok(uri) = act_dict.get(b"URI") {
                                link_type = "External (URI)".to_string();
                                target = String::from_utf8_lossy(uri.as_str()?).to_string();
                            }
                        } else if s.as_name()? == b"GoToR" {
                            link_type = "Remote (GoToR)".to_string();
                            if let Ok(file) = act_dict.get(b"F") {
                                target = String::from_utf8_lossy(file.as_str()?).to_string();
                            }
                        }
                    }
                }
            }

            // GoTo / Dest
            let dest = annot_dict.get(b"Dest").or_else(|_| annot_dict.get(b"A").and_then(|a| a.as_dict().and_then(|ad| ad.get(b"D"))));
            if let Ok(dest_obj) = dest {
                if let Some(page) = resolve_dest(dest_obj, id_to_page) {
                    link_type = "Internal (GoTo/Dest)".to_string();
                    target = format!("Page {}", page);
                }
            }

            links.push(LinkInfo {
                page: (page_num + 1) as u32,
                rect,
                link_text: if page_text.is_empty() { "Graphic/Empty Link".to_string() } else { page_text.clone() },
                link_type,
                target,
            });
        }
    }

    Ok(links)
}

fn resolve_dest(dest: &Object, id_to_page: &HashMap<ObjectId, u32>) -> Option<u32> {
    match dest {
        Object::Array(arr) if !arr.is_empty() => {
            if let Object::Reference(ref_id) = arr[0] {
                id_to_page.get(&ref_id).copied()
            } else {
                None
            }
        }
        Object::Reference(ref_id) => id_to_page.get(ref_id).copied(),
        _ => None,
    }
}

fn extract_toc(doc: &Document, id_to_page: &HashMap<ObjectId, u32>) -> Result<Vec<TocEntry>> {
    // ... same as previous (TOC parsing)
    // (omitted for brevity - use the previous version)
    Ok(vec![])
}
