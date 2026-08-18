#!/usr/bin/env python3
"""Local setup server: serve ui/setup and read/write .git_projects.json in the project."""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
UI_DIR = PLUGIN_ROOT / "ui" / "setup"


class Handler(BaseHTTPRequestHandler):
    project: pathlib.Path
    plugin_root: pathlib.Path

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, code: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/config":
            cfg_path = self.project / ".git_projects.json"
            if cfg_path.is_file():
                self._send_json(200, json.loads(cfg_path.read_text()))
            else:
                self._send_json(200, {"version": 1, "projects": [], "routing": [], "automation": {"enabled": True, "interval_minutes": 10}})
            return
        if path == "/api/meta":
            self._send_json(
                200,
                {
                    "project_path": str(self.project.resolve()),
                    "plugin_version": json.loads(
                        (self.plugin_root / "config" / "managed-manifest.json").read_text()
                    ).get("version", "0.4.0"),
                },
            )
            return
        rel = path.lstrip("/") or "index.html"
        file_path = UI_DIR / rel
        if not file_path.is_file() or UI_DIR not in file_path.resolve().parents:
            self.send_error(404)
            return
        content = file_path.read_bytes()
        ctype = "text/html; charset=utf-8"
        if rel.endswith(".js"):
            ctype = "application/javascript; charset=utf-8"
        elif rel.endswith(".css"):
            ctype = "text/css; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/config":
            data = self._read_json_body()
            cfg_path = self.project / ".git_projects.json"
            cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            self._send_json(200, {"ok": True, "path": str(cfg_path)})
            return
        if path == "/api/apply":
            cfg_path = self.project / ".git_projects.json"
            if not cfg_path.is_file():
                self._send_json(400, {"ok": False, "error": "Save .git_projects.json first"})
                return
            try:
                proc = subprocess.run(
                    ["bash", str(self.plugin_root / "scripts" / "apply-setup.sh"), "--project", str(self.project)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self._send_json(200, {"ok": True, "output": proc.stdout})
            except subprocess.CalledProcessError as exc:
                self._send_json(
                    500,
                    {"ok": False, "error": exc.stderr or exc.stdout or str(exc)},
                )
            return
        self.send_error(404)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Codex execution project directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    project = pathlib.Path(args.project).resolve()
    project.mkdir(parents=True, exist_ok=True)

    Handler.project = project
    Handler.plugin_root = PLUGIN_ROOT

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"eng-agents setup server: {url}")
    print(f"project: {project}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
