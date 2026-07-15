#!/usr/bin/env python3
"""Serve the Zoomies site plus a private development BIN/CUE over the LAN."""

from __future__ import annotations

import argparse
import email.utils
import functools
import json
import os
import re
import socket
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit


SITE_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = Path.home() / "workspace" / "pspsps-engine"
PREFERRED_DISC = ENGINE_ROOT / "Zoomies.bin"
LEGACY_DISC = ENGINE_ROOT / "pspsps.bin"


def default_disc_path() -> Path:
    for candidate in (PREFERRED_DISC, LEGACY_DISC):
        if candidate.is_file():
            return candidate
    return PREFERRED_DISC


def default_cover_path(disc: Path) -> Path | None:
    candidates = (
        disc.with_name("Zoomies-cover.png"),
        disc.parent / "assets" / "branding" / "Zoomies-cover.png",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def cue_bin_names(cue: Path) -> list[str]:
    pattern = re.compile(r'^\s*FILE\s+"([^"]+)"\s+BINARY\s*$', re.IGNORECASE)
    return [
        match.group(1)
        for line in cue.read_text(encoding="ascii").splitlines()
        if (match := pattern.match(line)) is not None
    ]


class ZoomiesDevHandler(SimpleHTTPRequestHandler):
    server_version = "ZoomiesDevServer/0.2"

    @property
    def disc_path(self) -> Path:
        return self.server.disc_path  # type: ignore[attr-defined]

    @property
    def cue_path(self) -> Path:
        return self.server.cue_path  # type: ignore[attr-defined]

    @property
    def cover_path(self) -> Path | None:
        return self.server.cover_path  # type: ignore[attr-defined]

    def _request_path(self) -> str:
        return urlsplit(self.path).path

    @staticmethod
    def _game_url(path: Path) -> str:
        return f"/game/{quote(path.name, safe='')}"

    def _build_id(self) -> str:
        stat = self.disc_path.stat()
        return f"{stat.st_mtime_ns:x}-{stat.st_size:x}"

    def _metadata(self) -> bytes:
        stat = self.disc_path.stat()
        build_id = self._build_id()
        modified = datetime.fromtimestamp(stat.st_mtime).astimezone()
        payload = {
            "bin_size": stat.st_size,
            "bin_url": f"{self._game_url(self.disc_path)}?v={build_id}",
            "bios": "HLE",
            "build_id": build_id,
            "build_label": modified.strftime("build %Y-%m-%d %H:%M:%S"),
            "core": "pcsx_rearmed",
            "cue_url": f"{self._game_url(self.cue_path)}?v={build_id}",
        }
        if self.cover_path is not None:
            payload["cover_url"] = f"{self._game_url(self.cover_path)}?v={build_id}"
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def _send_bytes(self, data: bytes, content_type: str, head_only: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def _send_disc_file(self, path: Path, content_type: str):
        try:
            file_handle = path.open("rb")
        except OSError:
            self.send_error(404, "Development disc is unavailable")
            return None

        stat = os.fstat(file_handle.fileno())
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(stat.st_size))
        self.send_header("Last-Modified", email.utils.formatdate(stat.st_mtime, usegmt=True))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return file_handle

    def send_head(self):
        path = self._request_path()
        if path == self._game_url(self.disc_path):
            return self._send_disc_file(self.disc_path, "application/octet-stream")
        if path == self._game_url(self.cue_path):
            return self._send_disc_file(self.cue_path, "text/plain; charset=utf-8")
        if self.cover_path is not None and path == self._game_url(self.cover_path):
            return self._send_disc_file(self.cover_path, "image/png")
        return super().send_head()

    def do_GET(self) -> None:
        if self._request_path() == "/game/metadata.json":
            self._send_bytes(self._metadata(), "application/json", head_only=False)
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if self._request_path() == "/game/metadata.json":
            self._send_bytes(self._metadata(), "application/json", head_only=True)
            return
        super().do_HEAD()

    def end_headers(self) -> None:
        if not any(
            header.lower().startswith(b"cache-control:")
            for header in self._headers_buffer
        ):
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, message: str, *args: object) -> None:
        status = str(args[1]) if len(args) > 1 else ""
        if status.startswith(("4", "5")):
            super().log_message(message, *args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disc", type=Path, default=default_disc_path())
    parser.add_argument("--cover", type=Path)
    parser.add_argument("--site", type=Path, default=SITE_ROOT)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    return parser.parse_args()


def lan_address() -> str | None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        return probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()


def open_server(host: str, first_port: int, handler):
    ports = [0] if first_port == 0 else range(first_port, first_port + 20)
    last_error: OSError | None = None
    for port in ports:
        try:
            return ThreadingHTTPServer((host, port), handler)
        except OSError as error:
            last_error = error
    raise RuntimeError(f"no available port from {first_port} through {first_port + 19}") from last_error


def main() -> None:
    args = parse_args()
    site = args.site.expanduser().resolve()
    disc = args.disc.expanduser().resolve()
    cue = disc.with_suffix(".cue")
    cover = (
        args.cover.expanduser().resolve()
        if args.cover is not None
        else default_cover_path(disc)
    )

    if not site.joinpath("play", "index.html").is_file():
        raise SystemExit(f"ERROR: Zoomies player not found under {site}")
    if not disc.is_file():
        raise SystemExit(f"ERROR: development BIN not found: {disc}")
    if not cue.is_file():
        raise SystemExit(f"ERROR: development CUE not found: {cue}")
    if disc.name not in cue_bin_names(cue):
        raise SystemExit(f"ERROR: CUE does not reference {disc.name}: {cue}")
    if cover is not None and not cover.is_file():
        raise SystemExit(f"ERROR: cover art not found: {cover}")

    handler = functools.partial(ZoomiesDevHandler, directory=str(site))
    server = open_server(args.host, args.port, handler)
    server.disc_path = disc  # type: ignore[attr-defined]
    server.cue_path = cue  # type: ignore[attr-defined]
    server.cover_path = cover  # type: ignore[attr-defined]
    server.daemon_threads = True

    port = server.server_address[1]
    address = lan_address()
    print("Zoomies browser prototype: PCSX-ReARMed with HLE BIOS", flush=True)
    print(f"Disc: {cue}", flush=True)
    print(f"Local: http://127.0.0.1:{port}/play/", flush=True)
    if address:
        print(f"LAN:   http://{address}:{port}/play/", flush=True)
    print("Press Ctrl-C to stop.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
