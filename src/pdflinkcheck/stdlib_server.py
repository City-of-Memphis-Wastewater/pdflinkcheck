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

PUBLIC MODE:
------------
When --public is enabled, this server assumes:
- A reverse proxy is present
- TLS is terminated upstream
- The service may be reachable by untrusted clients

In public mode, the server:
- Enables stricter limits
- Refuses new work during shutdown
"""

from __future__ import annotations
from pathlib import Path
import http.server
import socketserver
import json
import tempfile
import os
import email
import signal
import threading
from dataclasses import dataclass
from typing import Optional

from pdflinkcheck import environment as enviro

try:
    from pdflinkcheck.report import run_report_and_call_exports
except:
    pass

# =========================
# Configuration
# =========================

HOST = "127.0.0.1"
PORT = 8000

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
#ALLOWED_LIBRARIES = {"auto", "pypdf", "pymupdf", "pdfium"}
ALLOWED_LIBRARIES = {"auto", "pypdf"}
if enviro.pymupdf_is_available():
    ALLOWED_LIBRARIES.add("pymupdf")
if enviro.pdfium_is_available():
    ALLOWED_LIBRARIES.add("pdfium")

# Concurrency control
MAX_CONCURRENT_JOBS = 2
REQUEST_SEMAPHORE = threading.Semaphore(MAX_CONCURRENT_JOBS)

# Shutdown coordination
SHUTDOWN_EVENT = threading.Event()

# Set via CLI in real usage
PUBLIC_MODE = False



# =========================
# HTML UI
# =========================

HTML_FORM = """<!doctype html>
<html>
<head>
  <title>pdflinkcheck API</title>
  <meta charset="utf-8">
  <!--style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 800px;
      margin: 40px auto;
    }
    button { padding: 6px 12px; }
  </style-->
  <style>
  body {
    font-family: system-ui, sans-serif;
    max-width: 800px;
    margin: 40px auto;
    line-height: 1.6;
    background: #f8f9fa;
    color: #212529;
    }
  h1 { text-align: center; }
  form {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 0 12px rgba(0,0,0,0.1);
  }
  input, select, button {
    padding: 8px 12px;
    margin-top: 6px;
    margin-bottom: 12px;
    border-radius: 6px;
    border: 1px solid #ccc;
    width: 100%;
    box-sizing: border-box;
  }
  button {
    background-color: #0d6efd;
    color: white;
    border: none;
    cursor: pointer;
  }
  button:hover { background-color: #0b5ed7; }
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
        <option value="auto" selected>Automatically choose PDF engine</option>
        <option value="pypdf">pypdf (pure Python)</option>
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
# Documentation
# =========================
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "pdflinkcheck API",
        "description": (
            "Single-purpose API for analyzing PDF links and tables of contents.\n\n"
            "This service is designed to run behind a reverse proxy and accepts "
            "multipart/form-data uploads containing a PDF file."
        ),
        "version": "1.1.0",
        "license": {
            "name": "MIT"
        }
    },
    "servers": [
        {"url": "/"}
    ],
    "paths": {
        "/": {
            "post": {
                "summary": "Analyze a PDF",
                "description": "Uploads a PDF file and returns link analysis results.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["file"],
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "format": "binary",
                                        "description": "PDF file to analyze"
                                    },
                                    "pdf_library": {
                                        "type": "string",
                                        "enum": ["auto", "pypdf", "pymupdf", "pdfium"],
                                        "default": "auto"
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Analysis result",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/AnalysisResponse"
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Validation error"
                    },
                    "503": {
                        "description": "Server shutting down"
                    }
                }
            }
        },
        "/ready": {
            "get": {
                "summary": "Readiness probe",
                "description": "Indicates whether the server is ready to accept new work.",
                "responses": {
                    "200": {"description": "Server ready"},
                    "503": {"description": "Server shutting down"}
                }
            }
        },
        "/openapi.json": {
            "get": {
                "summary": "OpenAPI specification",
                "description": "Returns the OpenAPI 3.0 specification for this service.",
                "responses": {
                    "200": {"description": "OpenAPI JSON document"}
                }
            }
        }
    },
    "components": {
        "schemas": {
            "AnalysisResponse": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "pdf_library_used": {
                        "type": "string",
                        "description": "PDF engine actually used (may differ from user selection if 'auto')"
                    },
                    "total_links_count": {"type": "integer"},
                    "data": {
                        "type": "object",
                        "description": "Structured analysis data"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Report metadata including library used and link counts",
                        "properties": {
                            "file_overview": {
                                "type": "object",
                                "properties": {
                                    "pdf_name": {"type": "string"},
                                    "total_pages": {"type": "integer"},
                                    "source_path": {"type": "string"},
                                    "processing_path": {"type": "string"}
                                }
                            },
                            "library_used": {"type": "string"},
                            "link_counts": {
                                "type": "object",
                                "properties": {
                                    "toc_entry_count": {"type": "integer"},
                                    "internal_goto_links_count": {"type": "integer"},
                                    "interal_resolve_action_links_count": {"type": "integer"},
                                    "total_internal_links_count": {"type": "integer"},
                                    "external_uri_links_count": {"type": "integer"},
                                    "other_links_count": {"type": "integer"},
                                    "total_links_count": {"type": "integer"}
                                }
                            }
                        }
                    },
                    "text_report": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ],
                        "description": "Human-readable text report (string or array of lines)"
                    }
                },
                "required": ["filename", "pdf_library_used", "total_links_count", "data", "text_report", "metadata"]
            }
        }
    }
}

# =========================
# Validation Models
# =========================

@dataclass(frozen=True)
class UploadRequest:
    filename: str
    pdf_bytes: bytes
    pdf_library: str


class ValidationError(Exception):
    """Client-side validation error (HTTP 400)."""


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
    """Extracts fields from multipart/form-data using stdlib email parser."""

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
    daemon_threads = True	

class APIHandler(http.server.BaseHTTPRequestHandler):
    server_version = "pdflinkcheck-stdlib/1.1"

    def log_message(self, format, *args):
        # simple per-request logging
        print(f"[{self.log_date_time_string()}] {self.client_address[0]} - {self.command} {self.path} - {format % args}")
        return

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
    
    # -------------------------
    # GET Helpers
    # -------------------------

    def _serve_html_form(self):
        """Serve the main HTML upload form."""
        body = HTML_FORM.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_openapi(self):
        """Serve the OpenAPI JSON specification."""
        self._send_json(OPENAPI_SPEC)

    def _serve_ready(self):
        """Serve the readiness probe."""
        if SHUTDOWN_EVENT.is_set():
            self._send_error_json("Server shutting down", 503)
        else:
            self._send_json({"status": "ready"})

    # -------- Handlers --------
    def do_GET(self):
        if self.path == "/":
            self._serve_html_form()
        elif self.path == "/openapi.json":
            self._serve_openapi()
        elif self.path == "/ready":
            self._serve_ready()
        elif self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)    
    
    def do_POST(self):
        if self.path != "/":
            self.send_error(404)
            return

        if SHUTDOWN_EVENT.is_set():
            self._send_error_json("Server shutting down", 503)
            return

        try:
            self.connection.settimeout(30)

            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValidationError("Empty request body")

            if content_length > MAX_UPLOAD_BYTES * 2:
                raise ValidationError("Request too large")

            body = self.rfile.read(min(content_length, MAX_UPLOAD_BYTES * 2))
            fields = MultipartParser.parse(self.headers, body)

            file_field = fields.get("file")
            if not isinstance(file_field, dict):
                raise ValidationError("Missing file upload")

            upload = RequestValidator.validate_upload(
                filename=file_field["filename"],
                pdf_bytes=file_field["data"],
                pdf_library=fields.get("pdf_library", "auto"),
            )

            with REQUEST_SEMAPHORE:
                response = self._process_pdf(upload)

            self._send_json(response)
            print(f"Content-Length: {content_length} bytes")
            print(f"Semaphore acquired: {REQUEST_SEMAPHORE._value} remaining slots")

        except ValidationError as e:
            self._send_error_json(str(e), 400)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            self._send_error_json(f"Internal server error: {e}", 500)
    # -------- Business Logic --------
    def _process_pdf(self, upload: UploadRequest) -> dict:
        """
        Process an uploaded PDF and return analysis results.
        If the report fails, returns zero counts and the error message.
        """
        print(f"Processing upload: {upload.filename} using {upload.pdf_library}")
        tmp_path: Optional[str] = None

        try:
            # Save PDF to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(upload.pdf_bytes)
                tmp_path = tmp.name

            # Run report analysis
            result = run_report_and_call_exports(
                pdf_path=tmp_path,
                #export_format="",
                export_format="json,txt",
                pdf_library=upload.pdf_library,
                print_bool=False,
            )

            result["metadata"]["file_overview"]["source_path"] = upload.filename
            result["metadata"]["file_overview"]["processing_path"] = tmp_path
            
            return {
                "filename": upload.filename,
                "pdf_library_used": result.get("metadata", {}).get("library_used",upload.pdf_library),
                "total_links_count": (
                    result.get("metadata", {}).get("link_counts", {}).get("total_links_count", 0)
                ),
                "data": result.get("data", {}),
                "text_report": result.get("text-lines", ""),
            }

        except Exception as e:
            # Simple fallback on error
            print(f"Error running report: {e}")
            return {
                "filename": upload.filename,
                "pdf_library_used": upload.pdf_library,
                "total_links_count": 0,
                "data": {},
                "text_report": f"Error: {e}",
            }

        finally:
            if tmp_path and os.path.exists(tmp_path):
                print(f"Deleting temporary file: {tmp_path}")
                os.unlink(tmp_path)

# =========================
# Entrypoint
# =========================

def main():
    with ThreadedHTTPServer((HOST, PORT), APIHandler) as httpd:

        def shutdown_server():
            SHUTDOWN_EVENT.set()
            httpd.shutdown()

        def handle_signal(signum, frame):
            print("\nShutdown signal received")
            threading.Thread(
                target=shutdown_server,
                daemon=True
            ).start()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        print(f"pdflinkcheck stdlib server running at http://{HOST}:{PORT}")
        print("Pure stdlib • Explicit validation • Graceful shutdown • Termux-safe")
        print(f"Public mode: {PUBLIC_MODE}")
        print(f"Max concurrent jobs: {MAX_CONCURRENT_JOBS}")
        try:
            httpd.serve_forever()
        finally:
            httpd.server_close()
            print("Server closed socket and cleaned up")

    print("Server shut down.")


if __name__ == "__main__":
    main()

