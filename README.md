# uv-import-constraint-dependencies

A CLI tool to import `constraints.txt` files into `pyproject.toml` as `tool.uv.constraint_dependencies`.

## Overview

This tool reads a pip constraints file (local or remote) and adds the pinned dependencies to your `pyproject.toml` in the format expected by the [uv](https://github.com/astral-sh/uv) package manager.

## Installation


```bash
uv tool install uv-import-constraint-dependencies
```

Or with pip:

```bash
pip install uv-import-constraint-dependencies
```

## Usage

### Basic Usage

Import constraints from a local file:

```bash
uv-import-constraint-dependencies -c constraints.txt
```

Import constraints from a remote URL:

```bash
uv-import-constraint-dependencies -c https://example.com/constraints.txt
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--constraints` | `-c` | Path or URI to constraints.txt file (required) |
| `--pyproject` | `-p` | Path to pyproject.toml file (default: `pyproject.toml`) |
| `--merge` | | Merge with existing constraint_dependencies instead of replacing |
| `--version` | | Show version information |
| `--help` | | Show help message |

### Examples

**Custom pyproject.toml path:**

```bash
uv-import-constraint-dependencies -c constraints.txt -p path/to/pyproject.toml
```

**Merge with existing constraints instead of replacing:**

```bash
uv-import-constraint-dependencies -c constraints.txt --merge
```

## Behavior

### Replace Mode (Default)

By default, all existing `constraint_dependencies` are replaced with the new ones from the constraints file.

### Merge Mode (`--merge`)

When using `--merge`, new constraints are merged with existing ones in `tool.uv.constraint_dependencies`:
- New packages are added
- Existing packages are updated with the new version specifier
- Packages not in the new constraints file are preserved
- Constraints are sorted alphabetically

### Constraints File Format

The tool supports standard pip constraints file format:

```text
# Comments are ignored
requests==2.31.0
flask>=2.0.0,<3.0.0
numpy==1.24.3 ; python_version >= "3.9"  # Inline comments are stripped
urllib3>=1.26.0

# Include directives are skipped
-r requirements.txt
-c other-constraints.txt
```

### Output Format

The constraints are written to `pyproject.toml` as:

```toml
[tool.uv]
constraint_dependencies = [
    "flask>=2.0.0,<3.0.0",
    "numpy==1.24.3 ; python_version >= \"3.9\"",
    "requests==2.31.0",
    "urllib3>=1.26.0",
]
```

## Requirements

- Python >= 3.10

## Dependencies

- [click](https://click.palletsprojects.com/) >= 8.0 - CLI framework
- [tomlkit](https://github.com/sdispater/tomlkit) >= 0.12 - TOML manipulation with formatting preservation

## License

MIT
