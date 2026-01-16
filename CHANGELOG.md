# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2025-01-16

### Added

- Custom constraints support via `--cc` / `--custom-constraints` flag to override base constraints with local customizations
- `--merge` flag to merge with existing pyproject.toml constraints (default is replace)

### Fixed

- Use correct TOML key `constraint-dependencies` (with hyphen) instead of `constraint_dependencies`

## [0.1.0] - 2025-01-15

### Added

- Initial release
- CLI tool to import constraints.txt into pyproject.toml
- Support for local and remote (HTTP/HTTPS) constraints files
- Merge mode to combine new constraints with existing ones
- Parsing of pip constraints file format (comments, environment markers, inline comments)
- Preserves pyproject.toml formatting using tomlkit
