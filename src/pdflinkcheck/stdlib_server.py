# src/pdflinkcheck/stdlib_server.py
import http.server
import socketserver
import json
import tempfile
import shutil
import os
from pathlib import Path
import email  # This replaces cgi for multipart parsing

from pdflinkcheck.report import run_report

PORT = 8000

HTML_FORM = """
<!doctype html>
<html>
<head><title>pdflinkcheck Stdlib Server</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 40px auto;">
  <h1>pdflinkcheck API (Pure Stdlib, without cgi)</h1>
  <p>Upload a PDF for link/TOC analysis. Zero third-party deps, future-proof.</p>
  <form action="/" method="post" enctype="multipart/form-data">
    <p><input type="file" name="file" accept=".pdf" required></p>
    <p>
      <label>Engine:</label>
      <select name="pdf_library">
        <option value="pypdf" selected>pypdf (pure Python, Termux-friendly)</option>
        <option value="pymupdf">pymupdf (faster, if installed)</option>
      </select>
    </p>
    <p>
      <label>Max links to show (0 = all):</label>
      <input type="number" name="max_links" value="0" min="0">
    </p>
    <p><button type="submit">Analyze PDF</button></p>
  </form>
  <hr>
  <p>Returns JSON. Works on Termux & Python 3.13+.</p>
</body>
</html>
"""

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class PDFLinkCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FORM.encode("utf-8"))
            return
            
        if self.path == "/favicon.ico":
            return
            # Silent no-content response (most browsers cache this)
            self.send_response(204)
            self.end_headers()
            return
        
        self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path != "/":
            self.send_error(404, "Not Found")
            return

        # Get Content-Type and Content-Length
        content_type = self.headers.get("Content-Type")
        if not content_type or "multipart/form-data" not in content_type:
            self._send_json_error("Expected multipart/form-data", 400)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_json_error("No body sent", 400)
            return

        # Read the entire body
        body = self.rfile.read(content_length)

        # Parse using email.message (pure stdlib, no cgi)
        msg = email.message_from_bytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body)

        if not msg.is_multipart():
            self._send_json_error("Invalid multipart message", 400)
            return

        # Extract parts
        file_item = None
        pdf_library = "pypdf"
        max_links = 0

        for part in msg.get_payload():
            disposition = part.get("Content-Disposition", "")
            if not disposition.startswith("form-data"):
                continue

            name = part.get_param("name", header="Content-Disposition")
            filename = part.get_param("filename", header="Content-Disposition")

            if name == "file" and filename:
                if not filename.lower().endswith(".pdf"):
                    self._send_json_error("Only .pdf files allowed", 400)
                    return
                file_item = part.get_payload(decode=True)  # bytes
                file_filename = filename

            elif name == "pdf_library":
                pdf_library = part.get_payload(decode=True).decode().lower()
                if pdf_library not in {"pypdf", "pymupdf"}:
                    self._send_json_error("Invalid pdf_library", 400)
                    return

            elif name == "max_links":
                try:
                    max_links = int(part.get_payload(decode=True).decode())
                except ValueError:
                    max_links = 0

        if not file_item:
            self._send_json_error("No PDF file uploaded", 400)
            return

        # Save uploaded file to temp
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_item)
                tmp_path = tmp_file.name

            result = run_report(
                pdf_path=tmp_path,
                max_links=max_links if max_links > 0 else 0,
                export_format="",
                pdf_library=pdf_library,
                print_bool=False
            )
            metadata = result.get("metadata", {"total_links": 0, "pdf_name": file_filename})
            total_links = metadata.get("total_links", 0)

            response = {
                "filename": file_filename,
                "pdf_library_used": pdf_library,
                "total_links": total_links,
                "data": result["data"],
                "text_report": result["text"]
            }

            self._send_json(response)

        except Exception as e:
            self._send_json_error(f"Analysis failed: {str(e)}", 500)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.wfile.write(json_bytes)

    def _send_json_error(self, message, status=400):
        self._send_json({"error": message}, status)

if __name__ == "__main__":
    with ThreadedTCPServer(("", PORT), PDFLinkCheckHandler) as httpd:
        print(f"pdflinkcheck pure-stdlib server (no cgi) running at http://localhost:{PORT}")
        print("Future-proof for Python 3.13+ • Handles concurrent uploads")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.server_close()
