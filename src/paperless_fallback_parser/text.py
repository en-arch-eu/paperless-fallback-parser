"""The built-in text parser (txt, csv) with legacy code pages decoded.

Same MIME types and behaviour as Paperless-ngx' own ``TextDocumentParser``,
except that a file which is not UTF-8 is decoded with ``textenc.decode_text``
instead of turning its accented letters into U+FFFD. Third-party parsers win
ties, but the score is set above the built-in 10 to make the choice explicit.

Such a file also gets a PDF archive copy (the decoded text through Gotenberg):
the web UI shows a text document by loading the original and reading it as
UTF-8, so without the PDF the preview would still show U+FFFD. UTF-8 files get
no archive copy, as with the built-in parser.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path

from django.conf import settings
from paperless.parsers.text import TextDocumentParser

from paperless_fallback_parser._version import __version__
from paperless_fallback_parser.textenc import decode_text

logger = logging.getLogger("paperless.parsing.fallback")

TEXT_SCORE = 20

#: The thumbnail shows the beginning of the file only.
THUMBNAIL_BYTES = 400_000

UTF8 = ("utf-8", "utf-8-sig")


def text_html(text: str, title: str) -> str:
    """The text as an HTML page for Gotenberg: monospace, long lines wrapped."""
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        "<style>body{margin:0;font-family:'DejaVu Sans Mono','Liberation Mono',monospace;"
        "font-size:8pt;white-space:pre-wrap;overflow-wrap:anywhere}</style>"
        f"</head><body>{html.escape(text)}</body></html>"
    )


class TextParser(TextDocumentParser):
    name = "Fallback Parser: text in any code page"
    version = __version__
    author = "self-hosted"
    url = "https://github.com/en-arch-eu/paperless-fallback-parser"

    @classmethod
    def score(cls, mime_type: str, filename: str, path: Path | None = None) -> int | None:
        return TEXT_SCORE if super().score(mime_type, filename, path) else None

    def __init__(self, logging_group: object = None) -> None:
        super().__init__(logging_group)
        self._archive_path: Path | None = None

    @property
    def can_produce_archive(self) -> bool:
        return True

    @property
    def requires_pdf_rendition(self) -> bool:
        # Asked before parse(), without the file: always ask for an archive and
        # make one only for files that are not UTF-8 (None otherwise, which the
        # consumer and reprocessing accept).
        return True

    def parse(self, document_path: Path, mime_type: str, *, produce_archive: bool = True) -> None:
        text, encoding = decode_text(document_path.read_bytes())
        self._text = text.replace("\x00", "")  # PostgreSQL rejects NUL in text fields
        if encoding in UTF8:
            return
        logger.info("%s decoded as %s", document_path.name, encoding)
        if produce_archive:
            self._archive_path = self._pdf(self._text, document_path.name)

    def _pdf(self, text: str, title: str) -> Path | None:
        from gotenberg_client import GotenbergClient
        from gotenberg_client.constants import A4
        from gotenberg_client.options import Measurement, MeasurementUnitType, PageMarginsType

        page = self._tempdir / "index.html"
        page.write_text(text_html(text, title), encoding="utf-8")
        margin = Measurement(0.4, MeasurementUnitType.Inches)
        try:
            with (
                GotenbergClient(host=settings.TIKA_GOTENBERG_ENDPOINT, timeout=settings.CELERY_TASK_TIME_LIMIT) as client,
                client.chromium.html_to_pdf() as route,
            ):
                response = (
                    route.index(page)
                    .margins(PageMarginsType(top=margin, bottom=margin, left=margin, right=margin))
                    .size(A4)
                    .run()
                )
        except Exception:
            # without the PDF the document is still consumed, only the preview stays wrong
            logger.warning("Could not render %s to PDF with Gotenberg", title, exc_info=True)
            return None
        out = self._tempdir / "archive.pdf"
        out.write_bytes(response.content)
        return out

    def get_archive_path(self) -> Path | None:
        return self._archive_path

    def get_thumbnail(self, document_path: Path, mime_type: str) -> Path:
        # the built-in renders the file read as UTF-8: give it a UTF-8 copy
        with document_path.open("rb") as handle:
            text, _ = decode_text(handle.read(THUMBNAIL_BYTES))
        utf8 = self._tempdir / "thumbnail-source.txt"
        utf8.write_text(text, encoding="utf-8")
        return super().get_thumbnail(utf8, mime_type)
