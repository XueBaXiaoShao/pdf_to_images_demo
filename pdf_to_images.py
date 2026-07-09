#!/usr/bin/env python
"""Convert PDF pages to image files using Poppler's pdftoppm."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


SUPPORTED_FORMATS = ("png", "jpeg", "tiff")
FORMAT_EXTENSIONS = {"png": "png", "jpeg": "jpg", "tiff": "tif"}
ProgressCallback = Callable[[int, int, Path], None]


class PdfConversionOptions:
    def __init__(
        self,
        pdf_path: Path,
        output_dir: Path | None = None,
        image_format: str = "png",
        dpi: int = 200,
        first_page: int | None = None,
        last_page: int | None = None,
        pdftoppm_path: str | None = None,
    ) -> None:
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.image_format = image_format
        self.dpi = dpi
        self.first_page = first_page
        self.last_page = last_page
        self.pdftoppm_path = pdftoppm_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a PDF into one image per page."
    )
    parser.add_argument("pdf", help="Path to the input PDF file.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Folder for generated images. Defaults to '<pdf_name>_images'.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=SUPPORTED_FORMATS,
        default="png",
        help="Output image format. Default: png.",
    )
    parser.add_argument(
        "-r",
        "--dpi",
        type=int,
        default=200,
        help="Render resolution in DPI. Default: 200.",
    )
    parser.add_argument(
        "--first-page",
        type=int,
        default=None,
        help="First page to convert, starting from 1.",
    )
    parser.add_argument(
        "--last-page",
        type=int,
        default=None,
        help="Last page to convert, starting from 1.",
    )
    parser.add_argument(
        "--pdftoppm",
        default=None,
        help="Optional path to pdftoppm if it is not on PATH.",
    )
    return parser.parse_args()


def find_pdftoppm(explicit_path: str | None) -> str:
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"pdftoppm was not found at: {path}")

    if os.name == "nt":
        found_exe = shutil.which("pdftoppm.exe")
        if found_exe:
            return found_exe

    found = shutil.which("pdftoppm")
    if found:
        return found

    raise FileNotFoundError(
        "pdftoppm was not found. Install Poppler and make sure pdftoppm is on PATH."
    )


def find_pdfinfo(pdftoppm_path: str) -> str:
    sibling = Path(pdftoppm_path).with_name("pdfinfo.exe" if os.name == "nt" else "pdfinfo")
    if sibling.exists():
        return str(sibling)

    if os.name == "nt":
        found_exe = shutil.which("pdfinfo.exe")
        if found_exe:
            return found_exe

    found = shutil.which("pdfinfo")
    if found:
        return found

    raise FileNotFoundError(
        "pdfinfo was not found. Install Poppler and make sure pdfinfo is on PATH."
    )


def get_pdf_page_count(pdf_path: Path, pdftoppm_path: str) -> int:
    pdfinfo = find_pdfinfo(pdftoppm_path)
    completed = subprocess.run(
        [pdfinfo, str(pdf_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(message or "pdfinfo failed without an error message.")

    for line in completed.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())

    raise RuntimeError("Could not read the PDF page count.")


def build_command(
    pdftoppm: str,
    pdf_path: Path,
    output_prefix: Path,
    image_format: str,
    dpi: int,
    first_page: int | None,
    last_page: int | None,
) -> list[str]:
    command = [pdftoppm, f"-{image_format}", "-r", str(dpi)]

    if first_page is not None:
        command.extend(["-f", str(first_page)])
    if last_page is not None:
        command.extend(["-l", str(last_page)])

    command.extend([str(pdf_path), str(output_prefix)])
    return command


def validate_args(args: argparse.Namespace, pdf_path: Path) -> None:
    validate_options(
        PdfConversionOptions(
            pdf_path=pdf_path,
            image_format=args.format,
            dpi=args.dpi,
            first_page=args.first_page,
            last_page=args.last_page,
        )
    )


def validate_options(options: PdfConversionOptions) -> None:
    if not options.pdf_path.exists():
        raise FileNotFoundError(f"Input PDF was not found: {options.pdf_path}")
    if not options.pdf_path.is_file():
        raise ValueError(f"Input path is not a file: {options.pdf_path}")
    if options.pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Input file must be a PDF: {options.pdf_path}")
    if options.image_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Image format must be one of: {', '.join(SUPPORTED_FORMATS)}")
    if options.dpi <= 0:
        raise ValueError("DPI must be greater than 0.")
    if options.first_page is not None and options.first_page <= 0:
        raise ValueError("--first-page must be greater than 0.")
    if options.last_page is not None and options.last_page <= 0:
        raise ValueError("--last-page must be greater than 0.")
    if (
        options.first_page is not None
        and options.last_page is not None
        and options.first_page > options.last_page
    ):
        raise ValueError("--first-page cannot be greater than --last-page.")


def convert_pdf_to_images(
    options: PdfConversionOptions,
    progress_callback: ProgressCallback | None = None,
) -> tuple[Path, list[Path]]:
    options.pdf_path = options.pdf_path.expanduser().resolve()
    validate_options(options)
    pdftoppm = find_pdftoppm(options.pdftoppm_path)
    page_count = get_pdf_page_count(options.pdf_path, pdftoppm)

    output_dir = (
        options.output_dir.expanduser().resolve()
        if options.output_dir
        else options.pdf_path.with_name(f"{options.pdf_path.stem}_images")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    first_page = options.first_page or 1
    last_page = options.last_page or page_count
    if first_page > page_count:
        raise ValueError(f"--first-page cannot be greater than the PDF page count ({page_count}).")
    if last_page > page_count:
        raise ValueError(f"--last-page cannot be greater than the PDF page count ({page_count}).")

    output_prefix = output_dir / options.pdf_path.stem
    total_pages = last_page - first_page + 1
    output_extension = FORMAT_EXTENSIONS[options.image_format]
    files: list[Path] = []

    for done, page_number in enumerate(range(first_page, last_page + 1), start=1):
        command = build_command(
            pdftoppm=pdftoppm,
            pdf_path=options.pdf_path,
            output_prefix=output_prefix,
            image_format=options.image_format,
            dpi=options.dpi,
            first_page=page_number,
            last_page=page_number,
        )

        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(message or "pdftoppm failed without an error message.")

        image_path = output_dir / f"{options.pdf_path.stem}-{page_number}.{output_extension}"
        files.append(image_path)
        if progress_callback:
            progress_callback(done, total_pages, image_path)

    return output_dir, files


def main() -> int:
    args = parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()

    try:
        output_dir, files = convert_pdf_to_images(
            PdfConversionOptions(
            pdf_path=pdf_path,
                image_format=args.format,
                dpi=args.dpi,
                first_page=args.first_page,
                last_page=args.last_page,
                output_dir=Path(args.output_dir) if args.output_dir else None,
                pdftoppm_path=args.pdftoppm,
            )
        )
        print(f"Converted {len(files)} page(s) to: {output_dir}")
        for file_path in files:
            print(file_path)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
