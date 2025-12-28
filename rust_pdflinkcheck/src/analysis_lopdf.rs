// src/analysis_lopdf.rs

use anyhow::{Context, Result};
use lopdf::{Document, Object, ObjectId};
use pdf_extract::{output_doc, PlainTextOutput, TextSpan};
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

/// Extracts links (with anchor text) and basic TOC outline.
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

    for (page_num, (page_id, _)) in doc.get_pages().iter().enumerate() {
        let page_obj = doc.get_object(*page_id)?;
        let annots = match page_obj.as_dict()?.get(b"Annots") {
            Ok(Object::Array(arr)) => arr,
            _ => continue,
        };

        // Extract text spans for the page
        let mut text_output = PlainTextOutput::default();
        output_doc(doc, &mut text_output).context("Text extraction failed")?;
        let page_spans: Vec<&TextSpan> = text_output
            .spans
            .iter()
            .filter(|span| span.page == page_num as i32)
            .collect();

        for annot_ref in annots {
            let annot = doc.get_object(annot_ref.as_reference()?)?;
            let annot_dict = annot.as_dict()?;

            if annot_dict.get(b"Subtype")?.as_name()? != b"Link" {
                continue;
            }

            let rect_obj = annot_dict.get(b"Rect")?.as_array()?;
            let rect: Vec<f64> = rect_obj
                .iter()
                .map(|o| o.as_float().unwrap_or(0.0) as f64)
                .collect();
            if rect.len() != 4 {
                continue;
            }

            let x_min = rect[0].min(rect[2]);
            let y_min = rect[1].min(rect[3]);
            let x_max = rect[0].max(rect[2]);
            let y_max = rect[1].max(rect[3]);

            let mut parts = Vec::new();
            const TOLERANCE: f64 = 10.0;

            for span in &page_spans {
                if let Some(bbox) = &span.bbox {
                    if (x_min - TOLERANCE) <= bbox.max_x as f64
                        && (x_max + TOLERANCE) >= bbox.min_x as f64
                        && (y_min - TOLERANCE) <= bbox.max_y as f64
                        && (y_max + TOLERANCE) >= bbox.min_y as f64
                    {
                        let txt = span.text.trim();
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
            let dest = annot_dict.get(b"Dest").or_else(|_| {
                annot_dict
                    .get(b"A")
                    .and_then(|a| a.as_dict())
                    .and_then(|ad| ad.get(b"D"))
            });

            if let Ok(dest_obj) = dest {
                if let Some(page) = resolve_dest(doc, dest_obj, id_to_page) {
                    link_type = "Internal (GoTo/Dest)".to_string();
                    target = format!("Page {}", page);
                }
            }

            links.push(LinkInfo {
                page: (page_num + 1) as u32,
                rect,
                link_text,
                link_type,
                target,
            });
        }
    }

    Ok(links)
}

/// Resolve simple destinations (array with page ref as first element, or indirect)
fn resolve_dest(
    _doc: &Document,
    dest: &Object,
    id_to_page: &HashMap<ObjectId, u32>,
) -> Option<u32> {
    match dest {
        Object::Array(arr) if !arr.is_empty() => {
            if let Object::Reference(ref_id) = arr[0] {
                id_to_page.get(&ref_id).copied()
            } else {
                None
            }
        }
        Object::Reference(ref_id) => id_to_page.get(ref_id).copied(),
        _ => None, // TODO: add named destinations if needed
    }
}

/// Basic TOC extraction (recursive traversal of /Outlines)
fn extract_toc(doc: &Document, id_to_page: &HashMap<ObjectId, u32>) -> Result<Vec<TocEntry>> {
    let mut toc = Vec::new();

    let root_outlines = doc
        .trailer
        .get(b"Root")
        .and_then(|r| r.as_dict())
        .and_then(|root| root.get(b"Outlines"))
        .ok();

    fn traverse(
        doc: &Document,
        item_ref: ObjectId,
        level: usize,
        toc: &mut Vec<TocEntry>,
        id_to_page: &HashMap<ObjectId, u32>,
    ) -> Result<()> {
        let item_obj = doc.get_object(item_ref)?;
        let item_dict = item_obj.as_dict()?;

        let title = item_dict
            .get(b"Title")
            .map(|t| String::from_utf8_lossy(t.as_str().unwrap_or(&[])).to_string())
            .unwrap_or_default();

        let dest = item_dict.get(b"Dest").ok();
        let target_page = dest.and_then(|d| resolve_dest(doc, d, id_to_page));

        toc.push(TocEntry {
            level,
            title,
            target_page,
        });

        if let Ok(first) = item_dict.get(b"First") {
            if let Object::Reference(first_id) = first {
                traverse(doc, *first_id, level + 1, toc, id_to_page)?;
            }
        }

        if let Ok(next) = item_dict.get(b"Next") {
            if let Object::Reference(next_id) = next {
                traverse(doc, *next_id, level, toc, id_to_page)?;
            }
        }

        Ok(())
    }

    if let Some(Object::Reference(outlines_id)) = root_outlines {
        if let Ok(first) = doc.get_object(*outlines_id)?.as_dict()?.get(b"First") {
            if let Object::Reference(first_id) = first {
                traverse(doc, *first_id, 1, &mut toc, id_to_page)?;
            }
        }
    }

    Ok(toc)
}
