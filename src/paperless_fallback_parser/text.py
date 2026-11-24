"""The built-in text parser (txt, csv) with legacy code pages decoded.

Same MIME types and behaviour as Paperless-ngx' own ``TextDocumentParser``,
except that a file which is not UTF-8 is decoded with ``textenc.decode_text``
instead of turning its accented letters into U+FFFD. Third-party parsers win
ties, but the score is set above the built-in 10 to make the choice explicit.
"""

from __future__ import annotations

import logging
from pathlib import Path

from paperless.parsers.text import TextDocumentParser

from paperless_fallback_parser._version import __version__
from paperless_fallback_parser.textenc import decode_text

logger = logging.getLogger("paperless.parsing.fallback")

TEXT_SCORE = 20

#: The thumbnail shows the beginning of the file only.
THUMBNAIL_BYTES = 400_000


class TextParser(TextDocumentParser):
    name = "Fallback Parser: text in any code page"
    version = __version__
    author = "self-hosted"
    url = "https://github.com/en-arch-eu/paperless-fallback-parser"

    @classmethod
    def score(cls, mime_type: str, filename: str, path: Path | None = None) -> int | None:
        return TEXT_SCORE if super().score(mime_type, filename, path) else None

    def parse(self, document_path: Path, mime_type: str, *, produce_archive: bool = True) -> None:
        text, encoding = decode_text(document_path.read_bytes())
        if encoding not in ("utf-8", "utf-8-sig"):
            logger.info("%s decoded as %s", document_path.name, encoding)
        self._text = text.replace("\x00", "")  # PostgreSQL rejects NUL in text fields

    def get_thumbnail(self, document_path: Path, mime_type: str) -> Path:
        # the built-in renders the file read as UTF-8: give it a UTF-8 copy
        with document_path.open("rb") as handle:
            text, _ = decode_text(handle.read(THUMBNAIL_BYTES))
        utf8 = self._tempdir / "thumbnail-source.txt"
        utf8.write_text(text, encoding="utf-8")
        return super().get_thumbnail(utf8, mime_type)
