from __future__ import annotations

import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FrontendProxyHandler(SimpleHTTPRequestHandler):
    backend_base_url = "http://localhost:8000"

    def _proxy_to_backend(self) -> None:
        target_url = f"{self.backend_base_url}{self.path}"
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length > 0 else None

        forward_headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in {"host", "connection", "content-length"}
        }

        request = Request(
            target_url,
            data=body,
            headers=forward_headers,
            method=self.command,
        )

        try:
            with urlopen(request) as response:
                payload = response.read()
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() in {
                        "transfer-encoding",
                        "connection",
                        "keep-alive",
                        "content-encoding",
                    }:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                if payload:
                    self.wfile.write(payload)
        except HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            for key, value in exc.headers.items():
                if key.lower() in {
                    "transfer-encoding",
                    "connection",
                    "keep-alive",
                    "content-encoding",
                }:
                    continue
                self.send_header(key, value)
            self.end_headers()
            if payload:
                self.wfile.write(payload)
        except URLError:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Bad gateway: backend unavailable")

    def _serve_spa_index(self) -> None:
        index_path = Path(self.directory) / "index.html"
        if not index_path.exists():
            self.send_error(404, "index.html not found")
            return

        self.path = "/index.html"
        super().do_GET()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
            return

        requested = Path(self.path.split("?", 1)[0].lstrip("/"))
        candidate = Path(self.directory) / requested

        if requested.as_posix() and candidate.exists() and candidate.is_file():
            super().do_GET()
            return

        if requested.suffix:
            super().do_GET()
            return

        self._serve_spa_index()

    def do_HEAD(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_PUT(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_PATCH(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path.startswith("/api/"):
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve bundled frontend assets and proxy /api to backend."
    )
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--backend-port", type=int, required=True)
    parser.add_argument("--build-dir", type=str, required=True)
    args = parser.parse_args()

    build_dir = Path(args.build_dir)
    if not build_dir.exists():
        raise SystemExit(f"Frontend build directory not found: {build_dir}")

    FrontendProxyHandler.backend_base_url = f"http://localhost:{args.backend_port}"

    def handler(*handler_args, **handler_kwargs):
        return FrontendProxyHandler(
            *handler_args,
            directory=os.fspath(build_dir),
            **handler_kwargs,
        )

    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
