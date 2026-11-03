"""Last-resort document parser plugin for Paperless-ngx v3."""

from paperless_fallback_parser._version import __version__
from paperless_fallback_parser.parser import FallbackDocumentParser

__all__ = ["FallbackDocumentParser", "__version__"]
