#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
pdflinkcheck stdlib HTTP service
===============================

This module implements a small, single-purpose HTTP service intended to be:

- Packaged inside a PYZ
- Run locally, on LAN, or behind a reverse proxy
- Used as a backend for CLI, GUI, or web clients

IMPORTANT:
----------
This server is NOT intended to be exposed directly to the public internet.

When running in public-facing deployments, it MUST be placed behind a
reverse proxy (e.g. Caddy, nginx, cloudflared) which provides:

- TLS termination
- Request size limits
- Connection timeouts
- Rate limiting
- Protection against slowloris-style attacks

This module intentionally does NOT:
- Manage TLS certificates
- Implement authentication
- Perform rate limiting
- Handle HTTP/2 or proxy protocols

Those concerns belong to infrastructure, not application code.
"""

"""
pdflinkcheck stdlib HTTP server
--------------------------------
Pure-stdlib, Termux-compatible API server with explicit validation layer.
"""
# NOTE:
# We intentionally do not implement authentication here.
# This service is designed to be deployed behind a proxy
# or access-controlled at the network layer.

# NOTE:
# This server uses blocking I/O by design.
# Concurrency is intentionally limited to avoid
# resource exhaustion on low-powered hosts.

from __future__ import annotations

import http.server
import socketserver
import json
import tempfile
import os
import email
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pdflinkcheck.report import run_report_and_call_exports

# =========================
# Configuration
# =========================

HOST = ""
PORT = 8000

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB hard limit
ALLOWED_LIBRARIES = {"pypdf", "pymupdf", "pdfium"}

PUBLIC_MODE = False  # Set via CLI flag
# PUBLIC MODE ASSUMPTIONS:
# - A reverse proxy is present
# - TLS is terminated upstream
# - Request sizes are limited externally


# =========================
# HTML UI
# =========================

HTML_FORM = """<!doctype html>
<html>
<head>
  <title>pdflinkcheck API</title>
  <meta charset="utf-8">
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 800px;
      margin: 40px auto;
    }
    button { padding: 6px 12px; }
  </style>
</head>
<body>
  <h1>pdflinkcheck (stdlib server)</h1>
  <p>Upload a PDF for link and TOC analysis.</p>

  <form action="/" method="post" enctype="multipart/form-data">
    <p>
      <input type="file" name="file" accept=".pdf" required>
    </p>
    <p>
      <label>Engine:</label>
      <select name="pdf_library">
        <option value="pypdf" selected>pypdf (pure Python)</option>
        <option value="pymupdf">PyMuPDF (fast, AGPL)</option>
        <option value="pdfium">PDFium (fast, permissive)</option>
      </select>
    </p>
    <button type="submit">Analyze</button>
  </form>

  <p>Returns JSON.</p>
</body>
</html>
"""

# =========================
# Validation Models
# =========================

@dataclass(frozen=True)
class UploadRequest:
    filename: str
    pdf_bytes: bytes
    pdf_library: str


class ValidationError(Exception):
    """Client-side error (400)."""


# =========================
# Validation Layer
# =========================

class RequestValidator:
    """Pure validation: no I/O, no side effects."""

    @staticmethod
    def validate_upload(
        *,
        filename: str,
        pdf_bytes: bytes,
        pdf_library: str,
    ) -> UploadRequest:

        if not filename:
            raise ValidationError("Missing filename")

        if not filename.lower().endswith(".pdf"):
            raise ValidationError("Only .pdf files are allowed")

        if not pdf_bytes:
            raise ValidationError("Empty file upload")

        if len(pdf_bytes) > MAX_UPLOAD_BYTES:
            raise ValidationError("File exceeds size limit")

        if pdf_library not in ALLOWED_LIBRARIES:
            raise ValidationError("Invalid pdf_library")

        return UploadRequest(
            filename=filename,
            pdf_bytes=pdf_bytes,
            pdf_library=pdf_library,
        )


# =========================
# Multipart Parsing
# =========================

class MultipartParser:
    """Extracts fields from multipart/form-data."""

    @staticmethod
    def parse(headers, body: bytes) -> dict:
        content_type = headers.get("Content-Type")
        if not content_type or "multipart/form-data" not in content_type:
            raise ValidationError("Expected multipart/form-data")

        msg = email.message_from_bytes(
            b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body
        )

        if not msg.is_multipart():
            raise ValidationError("Invalid multipart payload")

        fields = {}

        for part in msg.get_payload():
            disposition = part.get("Content-Disposition", "")
            if not disposition.startswith("form-data"):
                continue

            name = part.get_param("name", header="Content-Disposition")
            filename = part.get_param("filename", header="Content-Disposition")

            if filename:
                fields[name] = {
                    "filename": filename,
                    "data": part.get_payload(decode=True),
                }
            else:
                fields[name] = part.get_payload(decode=True).decode().strip()

        return fields


# =========================
# HTTP Server
# =========================

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class APIHandler(http.server.BaseHTTPRequestHandler):

    server_version = "pdflinkcheck-stdlib/1.0"

    # -------- Utilities --------

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int) -> None:
        self._send_json({"error": message}, status)

    # -------- Handlers --------

    def do_GET(self):
        if self.path == "/":
            body = HTML_FORM.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != "/":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValidationError("Empty request body")

            if content_length > MAX_UPLOAD_BYTES * 2:
                raise ValidationError("Request too large")

            body = self.rfile.read(content_length)

            fields = MultipartParser.parse(self.headers, body)

            file_field = fields.get("file")
            if not isinstance(file_field, dict):
                raise ValidationError("Missing file upload")

            upload = RequestValidator.validate_upload(
                filename=file_field["filename"],
                pdf_bytes=file_field["data"],
                pdf_library=fields.get("pdf_library", "pypdf"),
            )

            response = self._process_pdf(upload)
            self._send_json(response)

        except ValidationError as e:
            self._send_error_json(str(e), 400)

        except Exception as e:
            self._send_error_json("Internal server error", 500)

    # -------- Business Logic --------

    def _process_pdf(self, upload: UploadRequest) -> dict:
        tmp_path: Optional[str] = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf"
            ) as tmp:
                tmp.write(upload.pdf_bytes)
                tmp_path = tmp.name

            result = run_report_and_call_exports(
                pdf_path=tmp_path,
                export_format="",
                pdf_library=upload.pdf_library,
                print_bool=False,
            )

            link_count = (
                result.get("metadata", {})
                .get("link_counts", {})
                .get("total_links_count", 0)
            )

            return {
                "filename": upload.filename,
                "pdf_library_used": upload.pdf_library,
                "total_links_count": link_count,
                "data": result["data"],
                "text_report": result["text"],
            }

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)


# =========================
# Entrypoint
# =========================

def main():
    with ThreadedHTTPServer((HOST, PORT), APIHandler) as httpd:
        print(f"pdflinkcheck stdlib server running at http://localhost:{PORT}")
        print("Pure stdlib • Explicit validation • Termux-safe")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()
