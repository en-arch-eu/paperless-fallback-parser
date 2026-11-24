"""Decode text files that are not UTF-8 (no Paperless-ngx or Django imports).

Paperless-ngx reads every text file as UTF-8 and replaces what does not decode
with U+FFFD, so a CSV exported by a Windows program in a legacy code page loses
every accented letter. Here a file that is not UTF-8 is decoded with the
single-byte code page that yields the most letters of the expected language.
"""

from __future__ import annotations

import codecs

#: Single-byte code pages tried for text that is not UTF-8, in order of preference
#: on a tie: Windows (most exports), ISO (old web and Unix), DOS.
LEGACY_ENCODINGS = ("cp1250", "iso8859_2", "cp852")

#: Letters a correct decoding produces and a wrong one mostly does not.
EXPECTED_LETTERS = frozenset("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")


def decode_text(raw: bytes) -> tuple[str, str]:
    """``(text, encoding)``. UTF-8 (with or without BOM) and UTF-16 with a BOM
    are kept; a file that is mostly UTF-8 with a few broken bytes stays UTF-8
    (the broken bytes become U+FFFD); anything else is decoded with the legacy
    code page giving the most expected letters."""
    if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return raw.decode("utf-16", errors="replace"), "utf-16"
    if raw.startswith(codecs.BOM_UTF8):
        return raw[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    as_utf8 = raw.decode("utf-8", errors="replace")
    broken = as_utf8.count("�")
    valid = sum(1 for c in as_utf8 if ord(c) > 127) - broken
    if valid > broken:
        return as_utf8, "utf-8"

    def letters(encoding: str) -> int:
        return sum(1 for c in raw.decode(encoding, errors="replace") if c in EXPECTED_LETTERS)

    best = max(LEGACY_ENCODINGS, key=letters)  # max keeps the first one on a tie
    return raw.decode(best, errors="replace"), best
