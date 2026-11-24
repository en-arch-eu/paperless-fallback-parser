# paperless-fallback-parser

A last-resort document parser plugin for **Paperless-ngx v3.0+**.

Paperless-ngx rejects files that no parser claims. This plugin claims every
MIME type known to the system (`/etc/mime.types` via Python's `mimetypes`) and
handles them at the lowest possible priority, so files like CAD drawings, tax
software exports, archives or signed XML containers are stored, thumbnailed
and searchable by filename instead of being refused.

It replaces two built-in parsers with the same parsers plus an encoding fix:

- the text parser (txt, csv) also reads legacy code pages: Paperless-ngx reads
  every text file as UTF-8 and turns the accented letters of a file in another
  encoding (a CSV exported by a Windows program in `cp1250`) into `�`;
- the mail parser (eml) declares the encoding of the HTML part to Tika:
  Paperless-ngx sends it as UTF-8 without saying so, Tika guesses, and the text
  content of a Polish mail comes out as `Dzie艅 dobry` or `zostaÅ‚a` (the PDF
  of the mail was right).

Every other built-in parser is left alone.

## How it behaves

| File | Result |
| --- | --- |
| Anything a built-in parser handles (PDF, images, Office via Tika…) | Untouched — the built-in wins |
| Text and CSV (`text/plain`, `text/csv`, `application/csv`) | Like the built-in text parser; a file that is not UTF-8 is decoded with the Central European code page (`cp1250`, `iso8859_2` or `cp852`) that gives the most Polish letters, and gets a PDF archive copy of the decoded text (made by Gotenberg) so the preview shows it right; UTF-8 files get no archive copy |
| Mail (`message/rfc822`, `.eml`) | Like the built-in mail parser; the HTML part goes to Tika with `<meta charset="utf-8">` in front and every `<meta>` charset declaration in it set to `utf-8`, since the text is UTF-8 by then whatever the mail's encoding was |
| A text-like file no built-in claims | Content indexed for full-text search (same decoding) |
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

2. Put the update script in the plugins directory and run it as root:

   ```
   cd /mnt/tank/apps/paperless/plugins
   curl -fsSLO https://github.com/en-arch-eu/paperless-fallback-parser/releases/latest/download/update-fallback-parser.sh
   chmod 755 update-fallback-parser.sh
   ./update-fallback-parser.sh
   ```

   It downloads the latest wheel, checks it against `SHA256SUMS` from the
   release, points a stable, relative link at it and puts
   `010-fallback-parser.sh` (root, mode 755) in the `custom-cont-init.d`
   directory next to `plugins` (elsewhere: `INIT_DIR=<dir> ./update-fallback-parser.sh`):

   ```
   custom-cont-init.d/
     010-fallback-parser.sh
   plugins/
     paperless_fallback_parser-0.6.0-py3-none-any.whl
     paperless_fallback_parser.whl -> paperless_fallback_parser-0.6.0-py3-none-any.whl
     update-fallback-parser.sh
   ```

   Without the link, the init script takes the highest version found.

3. Restart the app and check the logs for:

   ```
   [fallback-parser] OK: version 0.6.0
   Loaded third-party parser 'Fallback Parser' v0.6.0 by self-hosted (entrypoint: 'fallback').
   Loaded third-party parser 'Fallback Parser: text in any code page' v0.6.0 by self-hosted (entrypoint: 'text').
   Loaded third-party parser 'Fallback Parser: mail with the HTML encoding declared' v0.6.0 by self-hosted (entrypoint: 'mail').
   ```

   If the `Loaded` lines are missing, the package is not installed in the
   interpreter Paperless runs under, or the entry point is not being read.

Updating: `./update-fallback-parser.sh` (latest release; the script also
updates itself), restart. Rolling back: `./update-fallback-parser.sh 0.3.1`
(any released version; one already in the directory works offline), restart.

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

```bash
uv run pytest -q    # textenc (decoding), no Paperless needed
```

The text and mail parsers subclass Paperless' own
`paperless.parsers.text.TextDocumentParser` and
`paperless.parsers.mail.MailDocumentParser` (checked on 3.5.1; the mail fix
overrides `tika_parse`); check them after every Paperless upgrade.

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

The public API covered by the version is: the `paperless_ngx.parsers` entry points `fallback` and `text`, the set of MIME types it accepts by default, and the `FALLBACK_PARSER_EXTRA_MIME_TYPES` environment variable.

## Licence

GPL-3.0-or-later.
