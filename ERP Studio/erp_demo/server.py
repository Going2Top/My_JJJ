"""Same-origin JSON API and static file server using Python's standard library."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import json
import logging
import mimetypes
import uuid

from .service import ApiError, Service

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
LOG = logging.getLogger("erp-demo")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class Handler(SimpleHTTPRequestHandler):
    server_version = "ERPStudioDemo/1.0"

    def __init__(self, *args, service, **kwargs):
        self.service = service
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        super().end_headers()

    def json_response(self, status, value):
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def api(self):
        trace_id = "request-" + uuid.uuid4().hex[:12]
        try:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 1024 * 1024:
                raise ApiError(413, "BODY_TOO_LARGE", "请求正文最多 1 MB")
            if self.command != "GET":
                origin = self.headers.get("Origin")
                if origin and urlparse(origin).netloc != self.headers.get("Host"):
                    raise ApiError(403, "ORIGIN_DENIED", "此本地 Demo 仅接受同源操作")
            data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
            result = self.service.request(self.command, unquote(parsed.path)[len("/api/v1"):], data, query,
                                          actor=self.headers.get("X-Demo-Actor", "operator"),
                                          department=self.headers.get("X-Department-ID", "finance"),
                                          key=self.headers.get("Idempotency-Key"))
            self.json_response(200, result)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            self.json_response(400, {"code": "INVALID_JSON", "message": "请求格式无效", "details": None, "traceId": trace_id})
        except ApiError as error:
            self.json_response(error.status, {"code": error.code, "message": error.message,
                                             "details": error.details, "traceId": trace_id})
        except Exception:
            LOG.exception("Internal error %s", trace_id)
            self.json_response(500, {"code": "INTERNAL_ERROR", "message": "服务异常，请查看本地终端日志",
                                     "details": None, "traceId": trace_id})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/v1/"):
            return self.api()
        target = (WEB_ROOT / unquote(parsed.path).lstrip("/")).resolve()
        if not target.is_relative_to(WEB_ROOT):
            return self.send_error(403)
        if target.is_file():
            return super().do_GET()
        if target.suffix:
            return self.send_error(404)
        self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        self.api() if self.path.startswith("/api/v1/") else self.send_error(404)

    def do_PUT(self):
        self.api() if self.path.startswith("/api/v1/") else self.send_error(404)

    def log_message(self, fmt, *args):
        LOG.info("%s %s", self.client_address[0], fmt % args)


def serve(host="127.0.0.1", port=8765, database=None):
    database = database or Path(__file__).resolve().parent.parent / "data" / "erp_demo.sqlite3"
    service = Service(database)
    server = ThreadingHTTPServer((host, port), partial(Handler, service=service))
    server.daemon_threads = True
    print(f"ERP Studio Demo is ready: http://{host}:{port}", flush=True)
    print("Python + SQLite | deterministic mock adapters | real ERP writes disabled", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo server stopped.", flush=True)
    finally:
        server.server_close()
