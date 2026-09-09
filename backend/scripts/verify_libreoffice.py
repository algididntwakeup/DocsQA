"""Verify headless LibreOffice can convert a DOCX into a non-empty PDF."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    source = args.docx.resolve()
    if not source.is_file() or source.suffix.lower() != ".docx":
        parser.error(f"DOCX input does not exist: {source}")

    output_dir = (args.output_dir or Path(tempfile.mkdtemp(prefix="docsqa-render-"))).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = os.environ.get("LIBREOFFICE_BIN", "soffice")
    result = subprocess.run(
        [binary, "--headless", "--convert-to", "pdf", str(source), "--outdir", str(output_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"LibreOffice conversion failed: {result.stderr.strip()}")

    rendered = output_dir / f"{source.stem}.pdf"
    if not rendered.is_file() or rendered.stat().st_size == 0:
        raise SystemExit(f"LibreOffice produced no usable PDF: {rendered}")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
