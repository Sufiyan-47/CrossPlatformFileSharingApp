from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import re
import urllib.parse

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


class FileShareHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            files = os.listdir(UPLOAD_DIR)
            file_links = "".join(
                f"<li><a href='/files/{urllib.parse.quote(fname)}'>{fname}</a></li>" for fname in files
            )
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>File Sharing App</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f0f2f5;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 30px;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                }}
                .card {{
                    background-color: #fff;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    width: 90%;
                    max-width: 400px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                input[type=file] {{
                    margin: 15px 0;
                }}
                button {{
                    padding: 12px 20px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 16px;
                }}
                button:hover {{
                    background-color: #0069d9;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                    margin-top: 15px;
                }}
                li {{
                    margin: 8px 0;
                }}
                a {{
                    text-decoration: none;
                    color: #007bff;
                    font-weight: bold;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
            </head>
            <body>
                <h1>📂 Cross-Platform File Sharing</h1>

                <div class="card">
                    <h3>Upload a File</h3>
                    <form enctype="multipart/form-data" method="post">
                        <input type="file" name="file" required>
                        <br>
                        <button type="submit">Upload</button>
                    </form>
                </div>

                <div class="card">
                    <h3>Available Files</h3>
                    <ul>
                        {file_links}
                    </ul>
                </div>
            </body>
            </html>
            """
            self._respond(html, 200)

        elif self.path.startswith("/files/"):
            requested = self.path.split("/files/", 1)[1]
            filename = os.path.basename(urllib.parse.unquote(requested))
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(os.path.getsize(filepath)))
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._respond("<h2>❌ File not found!</h2>", 404)

        else:
            self._respond("<h2>Invalid path!</h2>", 404)

    def do_POST(self):
        content_type = self.headers.get('Content-Type', '')
        if "multipart/form-data" not in content_type:
            self._respond("<h2>❌ Invalid upload request!</h2>", 400)
            return

        m = re.search(r'boundary=(.+)', content_type)
        if not m:
            self._respond("<h2>❌ Missing boundary!</h2>", 400)
            return

        boundary = m.group(1).strip()
        if boundary.startswith('"') and boundary.endswith('"'):
            boundary = boundary[1:-1]
        boundary_bytes = boundary.encode()

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        parts = body.split(b'--' + boundary_bytes)
        uploaded = False
        for part in parts:
            if not part or part in (b'--', b'--\r\n'):
                continue
            if part.startswith(b'\r\n'):
                part = part[2:]
            if part.endswith(b'\r\n'):
                part = part[:-2]
            sep = part.find(b'\r\n\r\n')
            if sep == -1:
                continue
            header_block = part[:sep].decode('utf-8', errors='ignore')
            data = part[sep + 4 :]

            disp_match = re.search(r'Content-Disposition:\s*form-data;(.+)', header_block, flags=re.IGNORECASE)
            if not disp_match:
                continue
            disp = disp_match.group(1)
            name_m = re.search(r'name="([^"]+)"', disp)
            filename_m = re.search(r'filename="([^"]+)"', disp)
            field_name = name_m.group(1) if name_m else None
            filename = filename_m.group(1) if filename_m else None

            if field_name == 'file' and filename:
                filename = os.path.basename(filename)
                filepath = os.path.join(UPLOAD_DIR, filename)
                with open(filepath, "wb") as out:
                    out.write(data)
                uploaded = True
                break

        if uploaded:
            self._respond("<h2>✅ File uploaded successfully!</h2><a href='/'>Go back</a>", 200)
        else:
            self._respond("<h2>❌ No file uploaded!</h2>", 400)

    def _respond(self, content, code):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))


def run(server_class=HTTPServer, handler_class=FileShareHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Server running at http://0.0.0.0:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
