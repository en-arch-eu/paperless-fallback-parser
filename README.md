# paperless-fallback-parser

A last-resort document parser plugin for **Paperless-ngx v3.0+**.

Paperless-ngx rejects files that no parser claims. This plugin claims every
MIME type known to the system (`/etc/mime.types` via Python's `mimetypes`) and
handles them at the lowest possible priority, so files like CAD drawings, tax
software exports, archives or signed XML containers are stored, thumbnailed
and searchable by filename instead of being refused.

It does **not** replace any built-in parser.

## How it behaves

| File | Result |
| --- | --- |
| Anything a built-in parser handles (PDF, images, Office via Tika…) | Untouched — the built-in wins |
| A text-like file no built-in claims | Content indexed for full-text search |
| An arbitrary binary | Stored with a stub text record (filename, MIME type, size) and a generic thumbnail |

A one-page placeholder PDF is generated as the archive copy, so the web UI
displays a document card instead of firing a browser download for formats
nothing can render. The original is always downloadable, untouched.

## Why the score is 1

The registry picks the parser with the **highest** `score()`, and **ties are
resolved in favour of third-party parsers**. Built-ins score 10. A catch-all
returning 10 would therefore silently take PDFs away from Tesseract and you
would lose OCR without an obvious error. This plugin returns `1`, so it only
ever runs when every other parser has declined.

If you fork this, keep the score below 10.

## Installation on TrueNAS SCALE (official Paperless-ngx app)

Paperless-ngx runs scripts from `/custom-cont-init.d` as root before the
webserver starts; the script installs the wheel there. (A parser is not a
Django app, so this is early enough.)

1. Two host directories, mounted in the app:

   - `.../custom-cont-init.d` → `/custom-cont-init.d` (owned by root, not
     writable by others: the init skips scripts in a directory that is)
   - `.../plugins` → `/plugins`

2. Put `contrib/010-fallback-parser.sh` in the first one (root, mode 755).

3. Put the wheel in the second one, with a stable link pointing at it. The
   `contrib/install-wheel.sh` script does that (download, SHA-256 check, link switch):

   ```
   plugins/
     paperless_fallback_parser-0.3.1-py3-none-any.whl
     paperless_fallback_parser.whl -> paperless_fallback_parser-0.3.1-py3-none-any.whl
   ```

   Without the link, the init script takes the highest version found.

   On the host, as root, for example:

   ```
   ./install-wheel.sh --dir /mnt/tank/apps/paperless/plugins \
     https://github.com/en-arch-eu/paperless-fallback-parser/releases/download/v0.3.1/paperless_fallback_parser-0.3.1-py3-none-any.whl \
     paperless_fallback_parser.whl
   ```

   The script checks the file against `SHA256SUMS` from the same release.

4. Restart the app and check the logs for:

   ```
   [fallback-parser] OK: version 0.3.1
   Loaded third-party parser 'Fallback Parser' v0.3.1 by self-hosted (entrypoint: 'fallback').
   ```

   If the second line is missing, the package is not installed in the
   interpreter Paperless runs under, or the entry point is not being read.

No environment variables are needed. `PAPERLESS_APPS` is the *old* (pre-v3)
mechanism and is not used here.

## Known limitations

**Consumption directory extension gate.** Paperless-ngx detects file types by
content, but files arriving through the consumption directory are rejected if
their extension is not registered for that MIME type. This plugin registers one
extension per MIME type — the one `mimetypes.guess_extension()` prefers. A file
whose extension is a less-common alias for the same MIME type (`.yml` where
`.yaml` was chosen) will still be refused from the consumption directory while
working fine through the web UI. Fix by adding the alias to `/etc/mime.types`
in a second init script.

**Download extension.** Paperless-ngx names downloads from the MIME type, so an
`application/octet-stream` original comes back as `.bin` and may need renaming.

**Unknown MIME types.** If libmagic reports a type absent from
`/etc/mime.types`, this plugin cannot register for it and you get
*File type {mime-type} not supported*. Add the type to `/etc/mime.types`.

**Documents with no text are near-invisible.** Auto-matching, the classifier
and the AI features have nothing to work with. Tag these documents manually.

## Development

`mimemap.py` has no Paperless-ngx or Django imports and can be run directly:

```bash
python -m paperless_fallback_parser.mimemap
```

## Versioning

Releases follow [Semantic Versioning 2.0.0](https://semver.org/):
`MAJOR.MINOR.PATCH`, released versions only (no pre-release suffixes, so the
version is the same in the git tag, the wheel name and PEP 440). While the
major version is 0, a breaking change raises MINOR. A released version is
never rebuilt or changed. Changes are listed in `CHANGELOG.md`.

The public API covered by the version is: the `paperless_ngx.parsers` entry point `fallback`, the set of MIME types it accepts by default, and the `FALLBACK_PARSER_EXTRA_MIME_TYPES` environment variable.

## Licence

GPL-3.0-or-later.
