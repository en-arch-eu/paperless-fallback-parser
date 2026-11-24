# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-11-24

### Added

- Entry point `text`: the built-in text parser (`text/plain`, `text/csv`,
  `application/csv`) with legacy code pages. Paperless-ngx reads text files as
  UTF-8 only, so a file in `cp1250` lost every Polish letter (`�` in the content,
  the search index and the thumbnail). A file that is not UTF-8 is now decoded
  with `cp1250`, `iso8859_2` or `cp852`, whichever gives the most Polish
  letters; a UTF-8 file with a few broken bytes stays UTF-8. Documents consumed
  before keep their content until reprocessed.

### Changed

- The fallback parser decodes text-like files the same way; a text file that
  is not UTF-8 had been treated as binary (no content indexed).

## [0.3.3] - 2026-11-03

### Fixed

- `010-fallback-parser.sh` reported "package installed but not importable"
  and exited 1 on every start (since 0.3.1), although Paperless loaded the
  parser. The check imported the package, which loads the parser and needs
  Paperless and Django settings, absent in the init script. It now only
  checks that the package is installed and reads its version from the
  package metadata.

## [0.3.2] - 2026-11-03

### Changed

- `contrib/install-wheel.sh` replaced by `update-fallback-parser.sh`, which
  lives in the plugins directory and takes no arguments: it installs the
  latest release (or the version given, for a rollback), checks it against
  `SHA256SUMS`, switches the link, keeps `010-fallback-parser.sh` in
  `custom-cont-init.d` equal to the release's copy and updates itself. Both
  scripts are attached to each release. The parser itself is unchanged.

## [0.3.1] - 2026-11-03

### Changed

- Version kept in one place (`_version.py`), reported by the parser and by
  the init script (`[fallback-parser] OK: version …`).
- `contrib/010-fallback-parser.sh` installs the wheel the stable link
  `/plugins/paperless_fallback_parser.whl` points at; without a link, the
  highest version (`sort -V`) instead of the last in alphabetical order.
- README: installation from a wheel (the source-directory install did not work).
- Parser `url` points at the public repository.

## [0.3.0] - 2026-08-31

First version in use (Paperless-ngx 3.x). History before this is not kept.
