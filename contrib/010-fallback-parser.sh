#!/bin/bash
# Mount the *directory containing this file* into /custom-cont-init.d.
# That directory must be owned by root:root and must not be world-writable.
#
# Runs as root before the webserver starts, so the plugin is present when
# Paperless-ngx discovers parsers via the paperless_ngx.parsers entry point.
# (A parser is not a Django app, so installing it here, after migrations,
# is early enough.)
#
# Installs from a prebuilt wheel: no build backend, no PyPI access needed.
# Preferred layout (see update-fallback-parser.sh): a stable link pointing at the
# versioned file, e.g.
#   /plugins/paperless_fallback_parser.whl -> paperless_fallback_parser-0.3.0-py3-none-any.whl
# Without the link, the highest version found in /plugins is used.
set -euo pipefail

LINK=/plugins/paperless_fallback_parser.whl

if [[ -L "${LINK}" ]]; then
    # pip needs the real, versioned file name
    WHEEL=$(readlink -f "${LINK}")
else
    WHEEL=$(ls -1 /plugins/paperless_fallback_parser-*.whl 2>/dev/null | sort -V | tail -1)
fi

if [[ -z "${WHEEL}" || ! -f "${WHEEL}" ]]; then
    echo "[fallback-parser] ERROR: no wheel found in /plugins"
    ls -la /plugins || true
    exit 1
fi

echo "[fallback-parser] Installing ${WHEEL} ($(stat -c %s "${WHEEL}") bytes)"
pip install --no-cache-dir --no-deps --force-reinstall --root-user-action=ignore "${WHEEL}"

# Fail loudly here rather than leaving a dangling entry point for the registry.
if ! python3 -c "import paperless_fallback_parser._version" 2>/dev/null; then
    echo "[fallback-parser] ERROR: package installed but not importable"
    pip show -f paperless-fallback-parser || true
    exit 1
fi

echo "[fallback-parser] OK: version $(python3 -c 'from paperless_fallback_parser._version import __version__; print(__version__)')"
