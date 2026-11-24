"""The built-in mail parser (.eml) with the HTML part's encoding declared to Tika.

Paperless-ngx sends the HTML part of a mail to Tika as UTF-8 bytes with
``Content-Type: text/html`` and no charset (``tika_client`` encodes the text with
``str.encode()``). Tika ignores a charset in the request header for HTML and
takes it from ``<meta>``; without one it guesses, often wrong for Polish (GBK:
"Dzień" becomes "Dzie艅"), and an old declaration left in the HTML
(``<meta charset="windows-1250">``) is wrong as well, since the bytes are UTF-8
by then. Only the text content (search) is affected; the PDF is made from the
same HTML by Gotenberg and is right.

Same parser otherwise; third-party parsers win ties, the score is set above the
built-in 10 to make the choice explicit.
"""

from __future__ import annotations

from pathlib import Path

from paperless.parsers.mail import MailDocumentParser

from paperless_fallback_parser._version import __version__
from paperless_fallback_parser.textenc import declare_utf8

MAIL_SCORE = 20


class MailParser(MailDocumentParser):
    name = "Fallback Parser: mail with the HTML encoding declared"
    version = __version__
    author = "self-hosted"
    url = "https://github.com/en-arch-eu/paperless-fallback-parser"

    @classmethod
    def score(cls, mime_type: str, filename: str, path: Path | None = None) -> int | None:
        return MAIL_SCORE if super().score(mime_type, filename, path) else None

    def tika_parse(self, html: str) -> str:
        return super().tika_parse(declare_utf8(html))
