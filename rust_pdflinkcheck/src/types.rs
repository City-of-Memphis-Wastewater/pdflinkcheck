// types.rs
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct LinkRecord {
    pub page: i32,
    pub rect: Option<(f32, f32, f32, f32)>,
    pub link_text: String,
    pub r#type: String,

    pub url: Option<String>,
    pub destination_page: Option<i32>,
    pub destination_view: Option<String>,
    pub remote_file: Option<String>,
    pub action_kind: Option<String>,
    pub source_kind: Option<String>,
    pub xref: Option<i32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TocEntry {
    pub level: i32,
    pub title: String,
    pub target_page: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AnalysisResult {
    pub links: Vec<LinkRecord>,
    pub toc: Vec<TocEntry>,
}
