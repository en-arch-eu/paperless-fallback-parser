import codecs

import pytest

from paperless_fallback_parser.textenc import decode_text

SAMPLE = "Data;Opis;Kwota\r\n2012-03-22;Zażółć gęślą jaźń, ŁÓDŹ, Śląsk, Ćma, Ńe;-12,50\r\n"


@pytest.mark.parametrize("encoding", ["cp1250", "iso8859_2", "cp852"])
def test_legacy_code_pages(encoding):
    assert decode_text(SAMPLE.encode(encoding)) == (SAMPLE, encoding)


def test_utf8_and_boms():
    assert decode_text(SAMPLE.encode("utf-8")) == (SAMPLE, "utf-8")
    assert decode_text(codecs.BOM_UTF8 + SAMPLE.encode("utf-8")) == (SAMPLE, "utf-8-sig")
    assert decode_text(SAMPLE.encode("utf-16")) == (SAMPLE, "utf-16")


def test_utf8_with_a_broken_byte_stays_utf8():
    text, encoding = decode_text(SAMPLE.encode("utf-8") + b"\xff\r\n")
    assert encoding == "utf-8"
    assert text == SAMPLE + "�\r\n"


def test_ascii_only_and_no_expected_letters():
    assert decode_text(b"plain") == ("plain", "utf-8")
    # a Western text in a legacy code page: no Polish letters anywhere, first code page wins
    assert decode_text("café".encode("cp1252")) == ("café", "cp1250")
