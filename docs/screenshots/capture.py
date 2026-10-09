"""Regenerate the terminal screenshots in docs/screenshots/.

Every image is produced by running the command it displays (via
``bash -c``) and rendering its real combined stdout/stderr and exit code.
Nothing is typed or edited by hand: the command string drawn in the image is
the exact string that ran, in the working directory named in the title bar.

Setup that is *not* shown (generating the services the later shots run in,
downloading Go modules, starting the servers) happens before the shots that
need it and is printed to this script's own stderr.

Requirements (not dependencies of goldpath itself):
  - ``goldpath`` on PATH (``pip install -e .``)
  - Pillow, plus fastapi / uvicorn / prometheus-client importable by this
    interpreter (the generated FastAPI service's requirements.txt)
  - ``go``, ``curl`` and ``python3`` on PATH; ports 8000 and 8080 free

Usage:
    python docs/screenshots/capture.py
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent

WIDTH = 902
PAD_X = 20
TITLE_H = 36
PAD_TOP = 18
PAD_BOTTOM = 16
FONT_SIZE = 14
LINE_H = 22
MAX_OUTPUT_LINES = 40

BG = (13, 17, 23)
TITLE_BG = (22, 27, 34)
BORDER = (48, 54, 61)
FG = (230, 237, 243)
DIM = (139, 148, 158)
PROMPT = (88, 166, 255)
OK = (63, 185, 80)
FAIL = (248, 81, 73)
DOTS = ((255, 95, 86), (255, 189, 46), (39, 201, 63))

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/Library/Fonts/DejaVuSansMono.ttf",
)
BOLD_CANDIDATES = tuple(p.replace("Mono.ttf", "Mono-Bold.ttf") for p in FONT_CANDIDATES)


def _font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    sys.exit("error: DejaVu Sans Mono not found; install fonts-dejavu-core")


def log(msg: str) -> None:
    print(f"[capture] {msg}", file=sys.stderr)


def run(command: str, cwd: Path) -> tuple[str, int]:
    proc = subprocess.run(
        ["bash", "-c", command],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )
    return proc.stdout, proc.returncode


def setup(command: str, cwd: Path) -> None:
    log(f"setup ({cwd.name}): {command}")
    subprocess.run(["bash", "-c", command], cwd=cwd, check=True)


def wrap(text: str, cols: int) -> list[str]:
    """Hard-wrap at the terminal width, the way a terminal does."""
    lines: list[str] = []
    for raw in text.expandtabs(8).split("\n"):
        while len(raw) > cols:
            lines.append(raw[:cols])
            raw = raw[cols:]
        lines.append(raw)
    return lines


def render(path: Path, title: str, command: str, output: str, code: int) -> None:
    font = _font(FONT_CANDIDATES, FONT_SIZE)
    bold = _font(BOLD_CANDIDATES, FONT_SIZE)
    char_w = font.getlength("M")
    cols = int((WIDTH - 2 * PAD_X) // char_w)

    cmd_lines = wrap("$ " + command, cols)
    out_lines = wrap(output.rstrip("\n"), cols) if output.strip() else []
    if len(out_lines) > MAX_OUTPUT_LINES:
        out_lines = out_lines[:MAX_OUTPUT_LINES] + ["... (output truncated)"]

    rows = len(cmd_lines) + len(out_lines) + 1
    height = TITLE_H + PAD_TOP + rows * LINE_H + PAD_BOTTOM
    img = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WIDTH - 1, TITLE_H], fill=TITLE_BG)
    draw.line([0, TITLE_H, WIDTH, TITLE_H], fill=BORDER)
    for i, color in enumerate(DOTS):
        cx = 20 + i * 20
        draw.ellipse([cx - 6, TITLE_H // 2 - 6, cx + 6, TITLE_H // 2 + 6], fill=color)
    draw.text((84, TITLE_H // 2), title, font=font, fill=DIM, anchor="lm")

    y = TITLE_H + PAD_TOP
    for i, line in enumerate(cmd_lines):
        x = PAD_X
        if i == 0:
            draw.text((x, y), "$", font=bold, fill=PROMPT)
            x += 2 * char_w
            line = line[2:]
        draw.text((x, y), line, font=bold, fill=FG)
        y += LINE_H
    for line in out_lines:
        draw.text((PAD_X, y), line, font=font, fill=FG)
        y += LINE_H
    draw.text((PAD_X, y), f"exit {code}", font=font, fill=OK if code == 0 else FAIL)
    img.save(path)


def shot(filename: str, cwd: Path, command: str) -> None:
    output, code = run(command, cwd)
    title = f"{cwd.name} — {command if len(command) <= 70 else command[:67] + '...'}"
    render(OUT_DIR / filename, title, command, output, code)
    log(f"wrote {filename} (exit {code})")
    if code != 0:
        sys.exit(f"error: {command!r} exited {code}:\n{output}")


def wait_for_port(port: int, proc: subprocess.Popen, timeout: float = 30) -> None:
    # A bare TCP connect, so the readiness check never shows up in the metrics.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            sys.exit(f"error: server for port {port} exited with {proc.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    sys.exit(f"error: nothing listening on port {port} after {timeout}s")


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def serve(argv: list[str], cwd: Path, port: int) -> subprocess.Popen:
    log(f"setup ({cwd.name}): {' '.join(argv)} &")
    proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_for_port(port, proc)
    return proc


def main() -> None:
    for tool in ("goldpath", "go", "curl", "python3"):
        if shutil.which(tool) is None:
            sys.exit(f"error: {tool} not found on PATH")
    for port in (8000, 8080):
        if not port_free(port):
            sys.exit(f"error: port {port} is already in use")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "services"
        work.mkdir()
        orders = work / "orders-api"
        inventory = work / "inventory-svc"

        shot("01-new.png", work, "goldpath new orders-api --flavor fastapi")
        shot("02-list.png", work, "goldpath list")
        shot("06-new-go.png", work, "goldpath new inventory-svc --flavor go")

        shot(
            "05-grafana.png",
            orders,
            "python3 -c \"import json; d=json.load(open('grafana/dashboard.json')); "
            "print('title:', d['title']); "
            "[print(f'  panel: {p[\\\"title\\\"]!r} ({p[\\\"type\\\"]})') for p in d['panels']]\"",
        )

        server = serve(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"], orders, 8000
        )
        try:
            shot(
                "04-metrics.png",
                orders,
                "curl -s -w '\\n' localhost:8000/healthz && "
                "curl -s localhost:8000/metrics | grep orders_api_requests_total",
            )
        finally:
            server.terminate()
            server.wait()

        setup("go mod download", inventory)
        shot("07-go-build-test.png", inventory, "go build -o inventory-svc ./cmd/server && go test ./...")

        server = serve(["./inventory-svc"], inventory, 8080)
        try:
            shot(
                "08-go-metrics.png",
                inventory,
                "curl -s localhost:8080/healthz && "
                "curl -s localhost:8080/metrics | grep requests_total",
            )
        finally:
            server.terminate()
            server.wait()


if __name__ == "__main__":
    main()
