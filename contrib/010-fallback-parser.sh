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
# The check must not import the package: importing it loads the parser, which
# needs Django settings and Paperless modules, present only inside Paperless.
# Paperless itself logs "Loaded third-party parser ..." when it loads it.
if ! VERSION=$(python3 - <<'EOF'
import importlib.metadata
import importlib.util

assert importlib.util.find_spec("paperless_fallback_parser"), "package not found"
print(importlib.metadata.version("paperless-fallback-parser"))
EOF
); then
    echo "[fallback-parser] ERROR: package not found after install"
    pip show -f paperless-fallback-parser || true
    exit 1
fi

echo "[fallback-parser] OK: version ${VERSION}"
