from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LegacyPed:
    title: str
    columns: int
    rows: int
    settings: str
    cells: list[str]
    source_text: str

    def to_dict(self) -> dict:
        return {
            "mode": "legacy_grid",
            "title": self.title,
            "columns": self.columns,
            "rows": self.rows,
            "settings": self.settings,
            "cells": list(self.cells),
        }

    @classmethod
    def from_dict(cls, data: dict, source_text: str = "") -> "LegacyPed":
        columns = int(data["columns"])
        rows = int(data["rows"])
        cells = [str(cell) for cell in data.get("cells", [])]
        cell_count = columns * rows
        if len(cells) < cell_count:
            cells.extend(["E"] * (cell_count - len(cells)))
        return cls(
            title=str(data.get("title") or "PED PedigreeLab"),
            columns=columns,
            rows=rows,
            settings=str(data.get("settings") or f"colRows: {columns} @ {rows}~"),
            cells=cells[:cell_count],
            source_text=source_text,
        )


def load_legacy_ped(path: str | Path) -> LegacyPed:
    source_path = Path(path)
    source_text = source_path.read_text(encoding="utf-8", errors="replace")
    lines = source_text.splitlines()
    if len(lines) < 2 or not lines[0].startswith("PED "):
        raise ValueError("not a legacy PED grid file")

    match = re.search(r"colRows:\s*(\d+)\s*@\s*(\d+)~", lines[1])
    if not match:
        raise ValueError("missing colRows header")

    columns = int(match.group(1))
    rows = int(match.group(2))
    cell_count = columns * rows
    cells = [line for line in lines[2:] if line != "~~~"][:cell_count]
    if len(cells) < cell_count:
        cells.extend(["E"] * (cell_count - len(cells)))

    return LegacyPed(
        title=lines[0],
        columns=columns,
        rows=rows,
        settings=lines[1],
        cells=cells,
        source_text=source_text,
    )


def is_legacy_ped(path: str | Path) -> bool:
    source_path = Path(path)
    if not source_path.exists():
        return False
    lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return len(lines) >= 2 and lines[0].startswith("PED ") and "colRows:" in lines[1]


def save_legacy_ped(pedigree: LegacyPed, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    lines = [pedigree.title, pedigree.settings, *pedigree.cells, "~~~"]
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_path.replace(output_path)


def render_svg(pedigree: LegacyPed, output: str | Path, cell_w: int = 27, cell_h: int = 22) -> Path:
    output_path = Path(output)
    margin_x = 12
    margin_y = 12
    width = pedigree.columns * cell_w + margin_x * 2
    height = pedigree.rows * cell_h + margin_y * 2
    body: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<metadata>",
        html.escape(pedigree.source_text),
        "</metadata>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g stroke="#111111" stroke-width="2" stroke-linecap="square" fill="none">',
    ]

    for index, cell in enumerate(pedigree.cells):
        col, row = _cell_position(index, pedigree)
        x = margin_x + col * cell_w
        y = margin_y + row * cell_h
        body.extend(_line_svg(cell, x, y, cell_w, cell_h))

    body.append("</g>")
    body.append('<g stroke="#111111" stroke-width="2" fill="#ffffff">')
    for index, cell in enumerate(pedigree.cells):
        col, row = _cell_position(index, pedigree)
        x = margin_x + col * cell_w
        y = margin_y + row * cell_h
        body.extend(_symbol_svg(cell, x, y, cell_w, cell_h))
    body.append("</g>")
    body.append('<g font-family="Arial, sans-serif" font-size="11" fill="#111111">')
    for index, cell in enumerate(pedigree.cells):
        col, row = _cell_position(index, pedigree)
        x = margin_x + col * cell_w
        y = margin_y + row * cell_h
        body.extend(_text_svg(cell, x, y, cell_w, cell_h))
    body.append("</g>")
    body.append("</svg>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(body), encoding="utf-8")
    return output_path


def render_png(pedigree: LegacyPed, output: str | Path, cell_w: int = 27, cell_h: int = 22) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required for PNG export") from exc

    margin_x = 12
    margin_y = 12
    width = pedigree.columns * cell_w + margin_x * 2
    height = pedigree.rows * cell_h + margin_y * 2
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 11)
    except OSError:
        font = ImageFont.load_default()

    for index, cell in enumerate(pedigree.cells):
        col, row = _cell_position(index, pedigree)
        x = margin_x + col * cell_w
        y = margin_y + row * cell_h
        _draw_line(draw, cell, x, y, cell_w, cell_h)

    for index, cell in enumerate(pedigree.cells):
        col, row = _cell_position(index, pedigree)
        x = margin_x + col * cell_w
        y = margin_y + row * cell_h
        _draw_symbol(draw, cell, x, y, cell_w, cell_h)
        _draw_text(draw, font, cell, x, y, cell_w, cell_h)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def _cell_position(index: int, pedigree: LegacyPed) -> tuple[int, int]:
    return index // pedigree.rows, index % pedigree.rows


def _line_svg(cell: str, x: int, y: int, cell_w: int, cell_h: int) -> list[str]:
    lines = []
    for x1, y1, x2, y2 in _line_segments(cell, x, y, cell_w, cell_h):
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')
    return lines


def _symbol_svg(cell: str, x: int, y: int, cell_w: int, cell_h: int) -> list[str]:
    kind = _symbol_kind(cell)
    if kind is None:
        return []
    cx = x + cell_w / 2
    cy = y + cell_h / 2
    size = min(cell_w, cell_h) * 0.72
    half = size / 2
    fill = "#111111" if "abortc" in cell or "\\16777216\\" in cell else "#ffffff"

    if kind == "male":
        return [f'<rect x="{cx - half}" y="{cy - half}" width="{size}" height="{size}" fill="{fill}"/>']
    if kind == "female":
        return [f'<circle cx="{cx}" cy="{cy}" r="{half}" fill="{fill}"/>']
    points = f"{cx},{cy - half} {cx + half},{cy} {cx},{cy + half} {cx - half},{cy}"
    return [f'<polygon points="{points}" fill="{fill}"/>']


def _text_svg(cell: str, x: int, y: int, cell_w: int, cell_h: int) -> list[str]:
    texts = _extract_text(cell)
    if not texts:
        return []
    cx = x + cell_w / 2
    cy = y + cell_h / 2
    out = []
    for offset, text in enumerate(texts):
        out.append(f'<text x="{cx + 12}" y="{cy - 4 + offset * 12}">{html.escape(text)}</text>')
    if "rmc: pfeil" in cell:
        out.append(f'<path d="M {cx - 18} {cy + 17} L {cx - 6} {cy + 6}" stroke="#111111" fill="none"/>')
        out.append(f'<path d="M {cx - 12} {cy + 8} L {cx - 6} {cy + 6} L {cx - 8} {cy + 12}" stroke="#111111" fill="none"/>')
    return out


def _draw_line(draw, cell: str, x: int, y: int, cell_w: int, cell_h: int) -> None:
    for x1, y1, x2, y2 in _line_segments(cell, x, y, cell_w, cell_h):
        draw.line((x1, y1, x2, y2), fill=(17, 17, 17), width=2)


def _draw_symbol(draw, cell: str, x: int, y: int, cell_w: int, cell_h: int) -> None:
    kind = _symbol_kind(cell)
    if kind is None:
        return
    cx = x + cell_w / 2
    cy = y + cell_h / 2
    size = min(cell_w, cell_h) * 0.72
    half = size / 2
    fill = (17, 17, 17) if "abortc" in cell or "\\16777216\\" in cell else (255, 255, 255)
    outline = (17, 17, 17)

    if kind == "male":
        draw.rectangle((cx - half, cy - half, cx + half, cy + half), fill=fill, outline=outline, width=2)
    elif kind == "female":
        draw.ellipse((cx - half, cy - half, cx + half, cy + half), fill=fill, outline=outline, width=2)
    else:
        draw.polygon(((cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)), fill=fill, outline=outline)


def _draw_text(draw, font, cell: str, x: int, y: int, cell_w: int, cell_h: int) -> None:
    texts = _extract_text(cell)
    cx = x + cell_w / 2
    cy = y + cell_h / 2
    for offset, text in enumerate(texts):
        draw.text((cx + 12, cy - 10 + offset * 12), text, fill=(17, 17, 17), font=font)
    if "rmc: pfeil" in cell:
        draw.line((cx - 18, cy + 17, cx - 6, cy + 6), fill=(17, 17, 17), width=2)
        draw.line((cx - 12, cy + 8, cx - 6, cy + 6, cx - 8, cy + 12), fill=(17, 17, 17), width=2)


def _line_segments(cell: str, x: int, y: int, cell_w: int, cell_h: int) -> list[tuple[float, float, float, float]]:
    if not cell.startswith("Lrn:"):
        return []
    kind = cell.split(":", 1)[1].split("~", 1)[0].strip()
    cx = x + cell_w / 2
    cy = y + cell_h / 2
    left = x
    right = x + cell_w
    top = y
    bottom = y + cell_h
    segments = {
        "horizontal": [(left, cy, right, cy)],
        "vertikal": [(cx, top, cx, bottom)],
        "plus": [(left, cy, right, cy), (cx, top, cx, bottom)],
        "t": [(left, cy, right, cy), (cx, cy, cx, bottom)],
        "treverse": [(left, cy, right, cy), (cx, top, cx, cy)],
        "tstop": [(cx, top, cx, cy)],
        "l": [(cx, cy, right, cy), (cx, top, cx, cy)],
        "ldown": [(cx, cy, right, cy), (cx, cy, cx, bottom)],
        "lreverse": [(left, cy, cx, cy), (cx, top, cx, cy)],
        "ldownreverse": [(left, cy, cx, cy), (cx, cy, cx, bottom)],
    }
    return segments.get(kind, [])


def _symbol_kind(cell: str) -> str | None:
    if cell.startswith("Mrf:"):
        return "male"
    if cell.startswith("Wrf:"):
        return "female"
    if cell.startswith("Srf:"):
        return "other"
    return None


def _extract_text(cell: str) -> list[str]:
    match = re.search(r"rw:\s*(.*?)~rn:", cell)
    if not match:
        return []
    raw = match.group(1).strip()
    if not raw:
        return []
    text = raw.replace("\\\\\\", "\n").replace("\\\\", "\n").replace("\\", "\n")
    return [part.strip() for part in text.splitlines() if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a legacy graphical .ped file")
    parser.add_argument("input")
    parser.add_argument("--svg", required=True)
    parser.add_argument("--png")
    args = parser.parse_args()

    pedigree = load_legacy_ped(args.input)
    render_svg(pedigree, args.svg)
    if args.png:
        render_png(pedigree, args.png)


if __name__ == "__main__":
    main()
