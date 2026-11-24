"""Last-resort document parser plugin for Paperless-ngx v3."""

from paperless_fallback_parser._version import __version__

__all__ = ["FallbackDocumentParser", "__version__"]


def __getattr__(name: str):
    # lazy: the parser needs Paperless-ngx and Django, ``mimemap`` and ``textenc`` do not
    if name == "FallbackDocumentParser":
        from paperless_fallback_parser.parser import FallbackDocumentParser

        return FallbackDocumentParser
    raise AttributeError(name)
