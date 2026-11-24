"""A last-resort parser for Paperless-ngx v3.

Claims every MIME type known to the system so that files no built-in parser
understands are still stored, thumbnailed and findable, instead of being
rejected at consumption time.

Design notes
------------
* ``score()`` returns ``FALLBACK_SCORE`` (1), deliberately below the 10 used by
  every built-in parser. Returning 10 would be wrong: the registry favours
  third-party parsers on a tie, so a catch-all scoring 10 would steal PDFs
  from Tesseract. Scoring 1 means this parser only ever wins when nothing
  else is willing to handle the file.
* A one-page placeholder PDF is produced as the archive copy, so the web UI
  shows a document card instead of firing a download for formats no browser
  can render. The original is untouched and still downloadable. Rendering
  uses Pillow, which writes PDF natively - Gotenberg is not a dependency.
* Text-looking files get their content indexed (UTF-8 or a legacy code
  page, see ``textenc``). Binaries get a short
  descriptive stub instead, so at minimum the original filename remains
  searchable.
"""

from __future__ import annotations

import datetime
import logging
import shutil
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Self

from django.conf import settings

from documents.parsers import ParseError

from paperless.parsers import MetadataEntry
from paperless.parsers import ParserContext

from paperless_fallback_parser._version import __version__
from paperless_fallback_parser.mimemap import build_mime_map
from paperless_fallback_parser.textenc import decode_text

logger = logging.getLogger("paperless.parsing.fallback")

#: Below the 10 used by built-in parsers, so built-ins always win.
FALLBACK_SCORE = 1

#: Never index more than this much text from a single file.
MAX_TEXT_BYTES = 1024 * 1024

#: How much of the file to inspect when deciding whether it is text.
SNIFF_BYTES = 8192

THUMBNAIL_SIZE = (500, 700)

#: A4 at 150 dpi, for the placeholder archive PDF.
PDF_SIZE = (1240, 1754)
PDF_DPI = 150

#: Text wrapping for the placeholder page.
PDF_MAX_LINES = 60
PDF_WRAP_COLUMNS = 95

METADATA_NAMESPACE = "https://github.com/paperless-fallback-parser/ns/"
METADATA_PREFIX = "fallback"


def _looks_like_text(path: Path) -> bool:
    """Heuristic: no NUL bytes in the head and almost no control characters
    once decoded (UTF-8 or a legacy code page, see ``textenc``)."""
    try:
        with path.open("rb") as handle:
            head = handle.read(SNIFF_BYTES)
    except OSError:
        return False

    if not head or b"\x00" in head:
        return False

    text, _ = decode_text(head)
    controls = sum(1 for c in text if (ord(c) < 32 and c not in "\t\n\r\f") or 0x7F <= ord(c) < 0xA0)
    return controls <= len(text) // 100


def _wrap(text: str, columns: int, max_lines: int) -> list[str]:
    """Hard-wrap text into at most ``max_lines`` lines of ``columns`` chars."""
    out: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line:
            out.append("")
        for start in range(0, len(raw_line), columns):
            out.append(raw_line[start : start + columns])
            if len(out) >= max_lines:
                return out
        if len(out) >= max_lines:
            return out
    return out


def _render_page(
    size: tuple[int, int],
    heading: str,
    subheading: str,
    body_lines: list[str],
):
    """Draw a simple document-looking page. Returns a PIL Image."""
    from PIL import Image
    from PIL import ImageDraw

    width, height = size
    margin = max(12, width // 25)
    scale = width / THUMBNAIL_SIZE[0]

    image = Image.new("RGB", size, color="#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (margin, margin, width - margin, height - margin),
        outline="#b0b0b0",
        width=max(1, int(2 * scale)),
    )

    x = margin * 2
    y = margin * 2
    line_step = max(12, int(14 * scale))

    draw.text((x, y), heading, fill="#202020")
    y += line_step * 2
    draw.text((x, y), subheading, fill="#606060")
    y += line_step * 2

    for line in body_lines:
        if y > height - margin * 2:
            break
        draw.text((x, y), line, fill="#404040")
        y += line_step

    return image


class FallbackDocumentParser:
    """Stores documents of any MIME type when no other parser will."""

    name = "Fallback Parser"
    version = __version__
    author = "self-hosted"
    url = "https://github.com/en-arch-eu/paperless-fallback-parser"

    @classmethod
    def supported_mime_types(cls) -> dict[str, str]:
        return build_mime_map()

    @classmethod
    def score(
        cls,
        mime_type: str,
        filename: str,
        path: Path | None = None,
    ) -> int | None:
        return FALLBACK_SCORE

    @property
    def can_produce_archive(self) -> bool:
        # A placeholder page, not a faithful rendition - but enough to give
        # the UI something to display instead of triggering a download.
        return True

    @property
    def requires_pdf_rendition(self) -> bool:
        # These formats cannot be displayed by a browser, so the PDF must stay.
        return True

    def __init__(self, logging_group: object = None) -> None:
        settings.SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self._tempdir = Path(
            tempfile.mkdtemp(prefix="paperless-fallback-", dir=settings.SCRATCH_DIR),
        )
        self._text: str = ""
        self._archive_path: Path | None = None
        self._logging_group = logging_group

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        shutil.rmtree(self._tempdir, ignore_errors=True)

    def configure(self, context: ParserContext) -> None:
        return None

    def parse(
        self,
        document_path: Path,
        mime_type: str,
        *,
        produce_archive: bool = True,
    ) -> None:
        try:
            stat = document_path.stat()
        except OSError as exc:
            raise ParseError(f"Cannot stat {document_path}: {exc}") from exc

        header = (
            f"{document_path.name}\n"
            f"MIME type: {mime_type}\n"
            f"Size: {stat.st_size} bytes\n"
        )

        if _looks_like_text(document_path):
            try:
                with document_path.open("rb") as handle:
                    body, _ = decode_text(handle.read(MAX_TEXT_BYTES))
            except OSError as exc:
                raise ParseError(f"Cannot read {document_path}: {exc}") from exc
            body = body.replace("\x00", "")
            self._text = f"{header}\n{body}"
            preview = _wrap(body, PDF_WRAP_COLUMNS, PDF_MAX_LINES)
        else:
            logger.info(
                "Archiving %s (%s) without text extraction",
                document_path.name,
                mime_type,
            )
            self._text = (
                f"{header}\n"
                "Archived by the fallback parser. No text could be extracted "
                "from this file type. Download the original to work with it."
            )
            preview = [
                "Archived by the fallback parser.",
                "No text could be extracted from this file type.",
                "",
                "Download the original to work with it.",
            ]

        if produce_archive:
            self._archive_path = self._write_placeholder_pdf(
                document_path,
                mime_type,
                stat.st_size,
                preview,
            )

    def _write_placeholder_pdf(
        self,
        document_path: Path,
        mime_type: str,
        size_bytes: int,
        body_lines: list[str],
    ) -> Path | None:
        """Render a one-page stand-in so the UI has something to display."""
        try:
            page = _render_page(
                PDF_SIZE,
                document_path.name,
                f"{mime_type} - {size_bytes} bytes",
                body_lines,
            )
            out = self._tempdir / "archived.pdf"
            page.save(out, format="PDF", resolution=PDF_DPI)
        except Exception:
            # A missing archive copy is survivable; a failed import is not.
            logger.warning(
                "Could not render placeholder PDF for %s",
                document_path.name,
                exc_info=True,
            )
            return None
        return out

    def get_text(self) -> str:
        return self._text

    def get_date(self) -> datetime.datetime | None:
        # Let Paperless-ngx run its own date guessing over filename and text.
        return None

    def get_archive_path(self) -> Path | None:
        return self._archive_path

    def get_page_count(self, document_path: Path, mime_type: str) -> int | None:
        return None

    def get_thumbnail(self, document_path: Path, mime_type: str) -> Path:
        suffix = document_path.suffix.lstrip(".").upper() or "FILE"

        image = _render_page(
            THUMBNAIL_SIZE,
            suffix,
            mime_type,
            [document_path.name[:48]],
        )
        out = self._tempdir / "thumb.webp"
        image.save(out, format="WEBP")
        return out

    def extract_metadata(
        self,
        document_path: Path,
        mime_type: str,
    ) -> list[MetadataEntry]:
        # Contract: this must never raise.
        try:
            stat = document_path.stat()
            modified = datetime.datetime.fromtimestamp(
                stat.st_mtime,
                tz=datetime.timezone.utc,
            ).isoformat()
            values = {
                "OriginalFileName": document_path.name,
                "MimeType": mime_type,
                "SizeBytes": str(stat.st_size),
                "ModifiedUtc": modified,
            }
        except Exception:  # noqa: BLE001 - must never propagate
            return []

        return [
            MetadataEntry(
                namespace=METADATA_NAMESPACE,
                prefix=METADATA_PREFIX,
                key=key,
                value=value,
            )
            for key, value in values.items()
        ]
