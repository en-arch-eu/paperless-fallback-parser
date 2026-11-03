# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
