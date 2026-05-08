from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .layout import apply_generation_layout
from .legacy_ped_image import LegacyPed, is_legacy_ped, load_legacy_ped, save_legacy_ped
from .models import Pedigree
from .ped_io import load_ped, save_ped


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"


class PedigreeApp:
    def __init__(self, path: Path):
        self.path = path
        self.mode = "legacy_grid" if is_legacy_ped(path) else "pedigree"
        if self.mode == "legacy_grid":
            self.pedigree = load_legacy_ped(path)
        else:
            self.pedigree = load_ped(path)
            if self.pedigree.people and any(
                person.x is None or person.y is None for person in self.pedigree.people.values()
            ):
                apply_generation_layout(self.pedigree)

    def as_json(self) -> bytes:
        if self.mode == "legacy_grid":
            data = self.pedigree.to_dict()
            data["source_path"] = str(self.path)
            return json.dumps(data, indent=2).encode("utf-8")
        self.pedigree.source_path = str(self.path)
        data = self.pedigree.to_dict()
        data["mode"] = "pedigree"
        return json.dumps(data, indent=2).encode("utf-8")

    def replace_from_json(self, payload: bytes) -> None:
        data = json.loads(payload.decode("utf-8"))
        if data.get("mode") == "legacy_grid" or self.mode == "legacy_grid":
            self.mode = "legacy_grid"
            self.pedigree = LegacyPed.from_dict(data)
            save_legacy_ped(self.pedigree, self.path)
        else:
            self.mode = "pedigree"
            self.pedigree = Pedigree.from_dict(data)
            self.pedigree.source_path = str(self.path)
            save_ped(self.pedigree, self.path)


def make_handler(app: PedigreeApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "PedigreeLab/0.1"

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} - {format % args}")

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/pedigree":
                self._send_bytes(app.as_json(), "application/json")
                return
            if parsed.path == "/api/layout":
                if app.mode != "legacy_grid":
                    apply_generation_layout(app.pedigree)
                self._send_bytes(app.as_json(), "application/json")
                return

            target = WEB_ROOT / (parsed.path.removeprefix("/") or "index.html")
            if not _is_safe_path(target, WEB_ROOT) or not target.exists() or target.is_dir():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send_bytes(target.read_bytes(), content_type)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/pedigree":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("content-length", "0"))
            payload = self.rfile.read(length)
            try:
                app.replace_from_json(payload)
            except Exception as exc:
                self._send_bytes(
                    json.dumps({"error": str(exc)}).encode("utf-8"),
                    "application/json",
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            self._send_bytes(app.as_json(), "application/json")

        def _send_bytes(
            self,
            body: bytes,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _is_safe_path(target: Path, root: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PedigreeLab prototype")
    parser.add_argument("--file", default="samples/example.ped", help=".ped file to edit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    ped_path = Path(args.file)
    if not ped_path.is_absolute():
        ped_path = ROOT / ped_path

    app = PedigreeApp(ped_path)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"PedigreeLab serving {ped_path} at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
