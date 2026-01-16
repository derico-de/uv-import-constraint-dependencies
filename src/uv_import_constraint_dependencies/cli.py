"""Command-line interface for uv-import-constraint-dependencies.

This module provides the CLI interface using Click, allowing users to import
constraints.txt files (local or remote) into pyproject.toml as
tool.uv.constraint-dependencies.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from uv_import_constraint_dependencies import __version__
from uv_import_constraint_dependencies.parser import merge_constraints, parse_constraints
from uv_import_constraint_dependencies.toml_handler import (
    TOMLError,
    update_constraint_dependencies,
)
from uv_import_constraint_dependencies.uri_handler import (
    URIError,
    fetch_constraints,
    is_uri,
)


class ConstraintsError(Exception):
    """Exception raised for constraints-related errors."""

    pass


def _read_constraints(constraints_path: str) -> str:
    """
    Read constraints from a local file or remote URI.

    Args:
        constraints_path: Path to local file or URI to remote constraints file.

    Returns:
        The content of the constraints file as a string.

    Raises:
        ConstraintsError: If the file cannot be read or downloaded.
    """
    if is_uri(constraints_path):
        try:
            return fetch_constraints(constraints_path)
        except URIError as e:
            raise ConstraintsError(str(e)) from e
    else:
        path = Path(constraints_path)
        if not path.exists():
            raise ConstraintsError(f"Constraints file not found: {constraints_path}")
        if not path.is_file():
            raise ConstraintsError(
                f"Constraints path is not a file: {constraints_path}"
            )
        try:
            return path.read_text(encoding='utf-8')
        except OSError as e:
            raise ConstraintsError(
                f"Failed to read constraints file {constraints_path}: {e}"
            ) from e


@click.command()
@click.option(
    '-c',
    '--constraints',
    required=True,
    help='Path or URI to constraints.txt file.',
)
@click.option(
    '-p',
    '--pyproject',
    default='pyproject.toml',
    show_default=True,
    help='Path to pyproject.toml file.',
)
@click.option(
    '--merge',
    is_flag=True,
    default=False,
    help='Merge with existing constraint-dependencies instead of replacing.',
)
@click.option(
    '--cc',
    '--custom-constraints',
    'custom_constraints',
    default=None,
    help='Path to local custom constraints file for overriding base constraints.',
)
@click.version_option(version=__version__, prog_name='uv-import-constraint-dependencies')
def main(
    constraints: str,
    pyproject: str,
    merge: bool,
    custom_constraints: Optional[str],
) -> None:
    """Import constraints.txt into pyproject.toml as tool.uv.constraint-dependencies.

    This tool reads a constraints file (local or remote HTTP/HTTPS URL) and
    imports the pinned dependencies into your pyproject.toml file in the format
    expected by the uv package manager.

    \b
    Examples:
        # Import from local file
        uv-import-constraint-dependencies -c constraints.txt

        # Import from remote URL
        uv-import-constraint-dependencies -c https://example.com/constraints.txt

        # Use custom pyproject.toml path
        uv-import-constraint-dependencies -c constraints.txt -p path/to/pyproject.toml

        # Merge with existing constraints instead of replacing
        uv-import-constraint-dependencies -c constraints.txt --merge
    """
    pyproject_path = Path(pyproject)

    try:
        # Read constraints content (local or remote)
        content = _read_constraints(constraints)

        # Parse the base constraints
        parsed_constraints = parse_constraints(content)

        # If custom constraints file is provided, read and merge
        if custom_constraints:
            custom_path = Path(custom_constraints)
            if not custom_path.exists():
                raise ConstraintsError(
                    f"Custom constraints file not found: {custom_constraints}"
                )
            if not custom_path.is_file():
                raise ConstraintsError(
                    f"Custom constraints path is not a file: {custom_constraints}"
                )
            try:
                custom_content = custom_path.read_text(encoding='utf-8')
            except OSError as e:
                raise ConstraintsError(
                    f"Failed to read custom constraints file {custom_constraints}: {e}"
                ) from e

            parsed_custom = parse_constraints(custom_content)

            # Merge constraints - custom takes precedence over base
            if parsed_custom:
                parsed_constraints = merge_constraints(parsed_constraints, parsed_custom)

        if not parsed_constraints:
            click.echo("No constraints found in the input file.", err=True)
            sys.exit(0)

        # Update pyproject.toml (replace by default, merge if --merge is specified)
        update_constraint_dependencies(pyproject_path, parsed_constraints, merge=merge)

        # Report success
        count = len(parsed_constraints)
        action = "merged into" if merge and pyproject_path.exists() else "written to"
        click.echo(
            f"Successfully {action} {pyproject}: "
            f"{count} constraint{'s' if count != 1 else ''} imported."
        )

    except ConstraintsError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    except TOMLError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
