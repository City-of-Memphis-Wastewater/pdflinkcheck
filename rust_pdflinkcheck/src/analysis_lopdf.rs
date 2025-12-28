// src/analysis_lopdf.rs

use anyhow::{Context, Result};
use lopdf::{Document, Object, ObjectId};
use pdf_extract::{
    output_doc, PagePlainTextOutput, TextItem,
};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct LinkInfo {
    pub page: u32,              // 1-based
    pub rect: Vec<f64>,
    pub link_text: String,
    pub link_type: String,
    pub target: String,
}

#[derive(Debug, Clone)]
pub struct TocEntry {
    pub level: usize,
    pub title: String,
    pub target_page: Option<u32>,
}


// In analysis_lopdf.rs
#[derive(Debug, Clone, serde::Serialize)]
pub struct LinkInfo {
    pub page: u32,
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
/// Extracts all links (with anchor text) and TOC from a PDF using pure-Rust crates.
pub fn extract_pdf_data(pdf_path: &Path) -> Result<(Vec<LinkInfo>, Vec<TocEntry>)> {
    let doc = Document::load(pdf_path).context("Failed to load PDF")?;

    // Map object IDs to 1-based page numbers
    let mut obj_id_to_page: HashMap<ObjectId, u32> = HashMap::new();
    for (page_num, page_id) in doc.get_pages().iter().enumerate() {
        obj_id_to_page.insert(*page_id, (page_num + 1) as u32);
    }

    let links = extract_links(&doc, &obj_id_to_page)?;
    let toc = extract_toc(&doc, &obj_id_to_page)?;

    Ok((links, toc))
}

fn extract_links(doc: &Document, id_to_page: &HashMap<ObjectId, u32>) -> Result<Vec<LinkInfo>> {
    let mut links = Vec::new();

    for (page_num, page_id) in doc.get_pages() {
        let page_obj = doc.get_object(page_id)?;
        let annots = match page_obj.as_dict()?.get(b"Annots") {
            Ok(Object::Array(arr)) => arr,
            _ => continue,
        };

        // Extract text items for this page (pdf-extract)
        let mut text_output = PagePlainTextOutput::new();
        output_doc(doc, &mut text_output).context("Text extraction failed")?;
        let page_text_items: Vec<TextItem> = text_output
            .items
            .into_iter()
            .filter(|item| item.page == page_num as i32)
            .collect();

        for annot_obj in annots {
            let annot = doc.get_object(annot_obj.as_reference()?)?;
            let annot_dict = annot.as_dict()?;

            if annot_dict.get(b"Subtype")?.as_name()? != b"Link" {
                continue;
            }

            let rect_obj = annot_dict.get(b"Rect")?.as_array()?;
            let rect: Vec<f64> = rect_obj.iter().map(|o| o.as_real().unwrap_or(0.0)).collect();
            if rect.len() != 4 { continue; }

            let x_min = rect[0].min(rect[2]);
            let y_min = rect[1].min(rect[3]);
            let x_max = rect[0].max(rect[2]);
            let y_max = rect[1].max(rect[3]);

            // Collect overlapping text
            let mut parts = Vec::new();
            const TOLERANCE: f64 = 10.0;

            for item in &page_text_items {
                if let Some(bbox) = &item.bbox {
                    if (x_min - TOLERANCE) <= bbox.max_x && (x_max + TOLERANCE) >= bbox.min_x
                        && (y_min - TOLERANCE) <= bbox.max_y && (y_max + TOLERANCE) >= bbox.min_y
                    {
                        let txt = item.text.trim();
                        if !txt.is_empty() {
                            parts.push(txt.to_string());
                        }
                    }
                }
            }

            let link_text = if parts.is_empty() {
                "Graphic/Empty Link".to_string()
            } else {
                parts.join(" ").trim().to_string()
            };

            // Resolve link type & target
            let mut link_type = "Other Action".to_string();
            let mut target = "Unknown".to_string();

            // URI
            if let Ok(action) = annot_dict.get(b"A") {
                if let Ok(act_dict) = action.as_dict() {
                    if let Ok(s) = act_dict.get(b"S") {
                        if s.as_name()? == b"URI" {
                            if let Ok(uri) = act_dict.get(b"URI") {
                                link_type = "External (URI)".to_string();
                                target = uri.as_string()?.to_string();
                            }
                        } else if s.as_name()? == b"GoToR" {
                            link_type = "Remote (GoToR)".to_string();
                            if let Ok(file) = act_dict.get(b"F") {
                                target = file.as_string()?.to_string();
                            }
                        }
                    }
                }
            }

            // GoTo / Dest
            if let Ok(dest) = annot_dict.get(b"Dest") {
                if let Some(page) = resolve_dest(doc, dest, id_to_page) {
                    link_type = "Internal (GoTo/Dest)".to_string();
                    target = format!("Page {}", page);
                }
            } else if let Ok(action) = annot_dict.get(b"A") {
                if let Ok(act_dict) = action.as_dict() {
                    if let Ok(s) = act_dict.get(b"S") {
                        if s.as_name()? == b"GoTo" {
                            if let Ok(d) = act_dict.get(b"D") {
                                if let Some(page) = resolve_dest(doc, d, id_to_page) {
                                    link_type = "Internal (GoTo)".to_string();
                                    target = format!("Page {}", page);
                                }
                            }
                        }
                    }
                }
            }

            links.push(LinkInfo {
                page: page_num + 1,
                rect,
                link_text,
                link_type,
                target,
            });
        }
    }

    Ok(links)
}

/// Resolve Destination (simple version: handles array/indirect, skips named for now)
fn resolve_dest(
    doc: &Document,
    dest: &Object,
    id_to_page: &HashMap<ObjectId, u32>,
) -> Option<u32> {
    match dest {
        Object::Array(arr) if !arr.is_empty() => {
            if let Ok(ref_id) = arr[0].as_reference() {
                id_to_page.get(&ref_id).copied()
            } else {
                None
            }
        }
        Object::Indirect(id) => id_to_page.get(id).copied(),
        _ => None, // TODO: handle named destinations if needed
    }
}

fn extract_toc(doc: &Document, id_to_page: &HashMap<ObjectId, u32>) -> Result<Vec<TocEntry>> {
    let mut toc = Vec::new();

    let outline = doc.get_outline().unwrap_or_default();

    fn flatten_outline(
        items: &[lopdf::OutlineItem],
        level: usize,
        toc: &mut Vec<TocEntry>,
        id_to_page: &HashMap<ObjectId, u32>,
    ) {
        for item in items {
            let target_page = match &item.destination {
                Some(dest) => resolve_dest(&doc, dest, id_to_page), // reuse resolver
                None => None,
            };

            toc.push(TocEntry {
                level,
                title: item.title.clone(),
                target_page,
            });

            flatten_outline(&item.children, level + 1, toc, id_to_page);
        }
    }

    flatten_outline(&outline, 1, &mut toc, id_to_page);

    Ok(toc)
}
