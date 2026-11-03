"""Build the MIME type -> preferred extension mapping for the fallback parser.

Deliberately free of any Paperless-ngx or Django imports so it can be tested
standalone (``python -m paperless_fallback_parser.mimemap``).

The mapping is derived from Python's :mod:`mimetypes`, which on Linux reads
``/etc/mime.types`` in addition to its built-in table. That is the same file
Paperless-ngx consults when deciding whether a file dropped into the
consumption directory has an acceptable extension, so keeping the two in sync
is what makes consumption-directory imports work.
"""

from __future__ import annotations

import logging
import mimetypes
import os

logger = logging.getLogger("paperless.parsing.fallback")

# Types we always want to claim even if they are absent from the system table.
#
# libmagic reports plenty of types that never appear as a *value* in
# /etc/mime.types, so deriving the map from mimetypes alone leaves holes.
# text/xml is the canonical example: the system table maps .xml to
# application/xml, so text/xml - which is what libmagic actually returns for a
# plain XML file - was missing entirely and such files were refused.
_ALWAYS: dict[str, str] = {
    "application/octet-stream": ".bin",
    # XML and friends
    "text/xml": ".xml",
    "application/xml": ".xml",
    # Signed containers (common for Polish bank and government documents)
    "application/vnd.etsi.asic-e+zip": ".asice",
    "application/vnd.etsi.asic-s+zip": ".asics",
    "application/pkcs7-signature": ".p7s",
    "application/pkcs7-mime": ".p7m",
    "application/pgp-signature": ".asc",
    # Archives and compression
    "application/gzip": ".gz",
    "application/x-gzip": ".gz",
    "application/x-bzip2": ".bz2",
    "application/x-xz": ".xz",
    "application/x-7z-compressed": ".7z",
    "application/x-rar": ".rar",
    "application/vnd.rar": ".rar",
    "application/x-tar": ".tar",
    "application/x-iso9660-image": ".iso",
    # Data and text formats libmagic names differently
    "text/csv": ".csv",
    "application/csv": ".csv",
    "text/markdown": ".md",
    "text/x-yaml": ".yaml",
    "application/x-yaml": ".yaml",
    "text/calendar": ".ics",
    "text/vcard": ".vcf",
    "message/rfc822": ".eml",
    "application/x-sqlite3": ".sqlite",
    "application/vnd.sqlite3": ".sqlite",
    # Source and scripts
    "text/x-shellscript": ".sh",
    "text/x-python": ".py",
    "text/x-c": ".c",
    "text/x-c++": ".cpp",
    "text/x-java": ".java",
    "text/x-php": ".php",
    "text/x-perl": ".pl",
    "text/x-ruby": ".rb",
    "text/x-diff": ".diff",
    # Binaries
    "application/x-dosexec": ".exe",
    "application/x-executable": ".bin",
    "application/x-sharedlib": ".so",
}

#: Comma-separated ``mime/type:.ext`` pairs, so a missing type can be added
#: without rebuilding the package.
ENV_EXTRA_TYPES = "FALLBACK_PARSER_EXTRA_MIME_TYPES"

# Types that are pointless or actively harmful to archive as documents.
_EXCLUDED: frozenset[str] = frozenset(
    {
        "inode/directory",
        "inode/symlink",
        "inode/chardevice",
        "inode/blockdevice",
        "inode/fifo",
        "inode/socket",
    },
)


def build_mime_map() -> dict[str, str]:
    """Return a ``{mime_type: ".ext"}`` mapping covering every known type.

    Where a MIME type has several registered extensions, the one
    :func:`mimetypes.guess_extension` prefers is used, falling back to the
    alphabetically first. The choice is deterministic so that the extension a
    document gets today is the extension it gets after a restart.
    """
    mimetypes.init()

    by_type: dict[str, set[str]] = {}
    for ext, mime in mimetypes.types_map.items():
        # /etc/mime.types ships mixed-case entries (application/ATF). libmagic
        # reports lowercase, so a mixed-case key would simply never match.
        by_type.setdefault(mime.lower(), set()).add(ext.lower())
    for ext, mime in mimetypes.common_types.items():
        by_type.setdefault(mime.lower(), set()).add(ext.lower())

    mapping: dict[str, str] = {}
    for mime, extensions in by_type.items():
        if mime in _EXCLUDED or not extensions:
            continue
        preferred = mimetypes.guess_extension(mime)
        if preferred not in extensions:
            preferred = sorted(extensions)[0]
        mapping[mime] = preferred

    mapping.update(_ALWAYS)
    mapping.update(_extra_from_env())
    return mapping


def _extra_from_env() -> dict[str, str]:
    """Parse ``FALLBACK_PARSER_EXTRA_MIME_TYPES`` into a mapping.

    Format: ``mime/type:.ext,other/type:.other``. Malformed entries are logged
    and skipped rather than taking the whole parser down at startup.
    """
    raw = os.environ.get(ENV_EXTRA_TYPES, "").strip()
    if not raw:
        return {}

    extra: dict[str, str] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        mime, separator, ext = chunk.rpartition(":")
        mime = mime.strip().lower()
        ext = ext.strip().lower()
        if not separator or "/" not in mime or not ext:
            logger.warning("Ignoring malformed %s entry: %r", ENV_EXTRA_TYPES, chunk)
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        extra[mime] = ext

    if extra:
        logger.info("Added %d MIME types from %s", len(extra), ENV_EXTRA_TYPES)
    return extra


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    mapping = build_mime_map()
    print(f"{len(mapping)} MIME types")
    for mime in sorted(mapping)[:20]:
        print(f"  {mime} -> {mapping[mime]}")
