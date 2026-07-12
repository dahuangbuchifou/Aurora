"""Repeatable local performance observations for M2-002 parsers.

This is not a pass/fail benchmark. It records elapsed time, unit count, input size,
and Python allocation peak for representative upper-bound fixtures.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Callable

from reportlab.pdfgen import canvas

from aurora.collector.base import CollectedInput
from aurora.ingestion.contracts import PdfTableMode
from aurora.parser.html import HtmlDocumentParser
from aurora.parser.pdf import PdfDocumentParser
from aurora.parser.transcript import TranscriptParser


def _measure(name: str, input_bytes: int, action: Callable[[], object]) -> dict[str, object]:
    tracemalloc.start()
    start = time.perf_counter()
    result = action()
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    units = getattr(result, "units", ())
    return {
        "name": name,
        "input_bytes": input_bytes,
        "elapsed_seconds": round(elapsed, 6),
        "python_peak_allocated_bytes": peak,
        "content_unit_count": len(units),
        "parse_status": getattr(getattr(result, "parse_status", None), "value", None),
        "warning_count": len(getattr(result, "warnings", ())),
    }


def _html_case() -> tuple[CollectedInput, int]:
    target = 10 * 1024 * 1024
    prefix = b"<html><body><article><h1>Benchmark</h1><p>"
    suffix = b"</p></article></body></html>"
    payload = prefix + (b"A" * (target - len(prefix) - len(suffix))) + suffix
    collected = CollectedInput(
        path=Path("benchmark.html"),
        input_uri="file:///benchmark.html",
        file_name="benchmark.html",
        suffix=".html",
        size_bytes=len(payload),
        text=payload.decode("utf-8"),
        raw_bytes=payload,
        media_type="text/html",
    )
    return collected, len(payload)


def _pdf_case(temp_dir: Path) -> tuple[CollectedInput, int]:
    path = temp_dir / "benchmark_232_pages.pdf"
    pdf = canvas.Canvas(str(path))
    for page_no in range(1, 233):
        pdf.drawString(72, 780, f"Aurora M2-002 benchmark page {page_no}")
        pdf.drawString(72, 750, "Machine generated PDF paragraph for deterministic parsing.")
        pdf.showPage()
    pdf.save()
    payload = path.read_bytes()
    return (
        CollectedInput(
            path=path,
            input_uri=path.resolve().as_uri(),
            file_name=path.name,
            suffix=".pdf",
            size_bytes=len(payload),
            text="",
            raw_bytes=payload,
            media_type="application/pdf",
        ),
        len(payload),
    )


def _transcript_case() -> tuple[CollectedInput, int]:
    blocks: list[str] = ["WEBVTT", ""]
    for index in range(10_000):
        start_ms = index * 2000
        end_ms = start_ms + 1500
        start = _vtt_timestamp(start_ms)
        end = _vtt_timestamp(end_ms)
        blocks.extend([f"{start} --> {end}", f"Speaker: cue {index}", ""])
    text = "\n".join(blocks)
    payload = text.encode("utf-8")
    return (
        CollectedInput(
            path=Path("benchmark.vtt"),
            input_uri="file:///benchmark.vtt",
            file_name="benchmark.vtt",
            suffix=".vtt",
            size_bytes=len(payload),
            text=text,
            raw_bytes=payload,
            media_type="text/vtt",
        ),
        len(payload),
    )


def _vtt_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("PERFORMANCE_OBSERVATIONS.json"))
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="aurora_m2002_bench_") as temp:
        temp_dir = Path(temp)
        html, html_bytes = _html_case()
        pdf, pdf_bytes = _pdf_case(temp_dir)
        transcript, transcript_bytes = _transcript_case()

        results = [
            _measure(
                "html_10_mib",
                html_bytes,
                lambda: HtmlDocumentParser().parse(html),
            ),
            _measure(
                "pdf_232_pages",
                pdf_bytes,
                lambda: PdfDocumentParser(table_mode=PdfTableMode.OFF, max_pages=500).parse(pdf),
            ),
            _measure(
                "webvtt_10000_cues",
                transcript_bytes,
                lambda: TranscriptParser(transcript_format="vtt").parse(transcript),
            ),
        ]

    payload = {
        "benchmark_type": "non_blocking_local_observation",
        "notes": [
            "Results depend on host CPU, memory, Python and dependency versions.",
            "This is not a production SLA or release gate.",
            "Peak allocation is measured with tracemalloc and excludes native allocations.",
        ],
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
