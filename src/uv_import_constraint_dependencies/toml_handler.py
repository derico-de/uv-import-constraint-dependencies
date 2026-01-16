"""TOML handler for reading and updating pyproject.toml.

This module provides functionality to read and update pyproject.toml files
with constraint-dependencies while preserving existing formatting and comments.
Uses tomlkit for TOML manipulation to maintain document structure.
"""

import re
from pathlib import Path
from typing import List, Set

import tomlkit
from tomlkit import TOMLDocument
from tomlkit.exceptions import TOMLKitError


class TOMLError(Exception):
    """Exception raised for TOML-related errors."""

    pass


def _extract_package_name(constraint: str) -> str:
    """
    Extract the package name from a constraint string.

    This handles various version specifiers and environment markers to
    extract just the base package name for comparison purposes.

    Args:
        constraint: A constraint string like "requests==2.31.0" or
            "numpy>=1.24 ; python_version >= '3.9'"

    Returns:
        The package name portion of the constraint, normalized to lowercase.

    Examples:
        >>> _extract_package_name('requests==2.31.0')
        'requests'

        >>> _extract_package_name('urllib3>=1.26.0,<2.0.0')
        'urllib3'

        >>> _extract_package_name('NumPy>=1.24 ; python_version >= "3.9"')
        'numpy'

        >>> _extract_package_name('my-package[extra]>=1.0')
        'my-package'
    """
    # Remove environment markers first (everything after ;)
    constraint = constraint.split(';')[0].strip()

    # Remove extras (everything in square brackets)
    constraint = re.sub(r'\[.*?\]', '', constraint)

    # Split on version specifiers
    # Match any of: ==, !=, >=, <=, >, <, ~=, ===, @
    # Use regex to find the first occurrence of any version specifier
    match = re.match(r'^([a-zA-Z0-9_\-\.]+)', constraint)
    if match:
        return match.group(1).lower()

    return constraint.strip().lower()


def _get_existing_package_names(constraints: List[str]) -> Set[str]:
    """
    Get a set of package names from a list of constraints.

    Args:
        constraints: List of constraint strings.

    Returns:
        Set of normalized package names.
    """
    return {_extract_package_name(c) for c in constraints}


def read_pyproject(pyproject_path: Path) -> TOMLDocument:
    """
    Read and parse a pyproject.toml file.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        Parsed TOML document that preserves formatting.

    Raises:
        TOMLError: If the file cannot be read or parsed.

    Examples:
        >>> doc = read_pyproject(Path('pyproject.toml'))
        >>> doc['project']['name']
        'my-package'
    """
    if not pyproject_path.exists():
        raise TOMLError(f"pyproject.toml not found: {pyproject_path}")

    try:
        content = pyproject_path.read_text(encoding='utf-8')
    except OSError as e:
        raise TOMLError(f"Failed to read {pyproject_path}: {e}") from e

    try:
        return tomlkit.parse(content)
    except TOMLKitError as e:
        raise TOMLError(f"Failed to parse {pyproject_path}: {e}") from e


def get_constraint_dependencies(doc: TOMLDocument) -> List[str]:
    """
    Get existing constraint-dependencies from a parsed TOML document.

    Args:
        doc: A parsed TOML document.

    Returns:
        List of existing constraint strings, or empty list if none exist.

    Examples:
        >>> doc = read_pyproject(Path('pyproject.toml'))
        >>> get_constraint_dependencies(doc)
        ['requests==2.31.0', 'flask>=2.0.0']
    """
    try:
        tool = doc.get('tool')
        if tool is None:
            return []

        uv = tool.get('uv')
        if uv is None:
            return []

        constraints = uv.get('constraint-dependencies')
        if constraints is None:
            return []

        return list(constraints)
    except (KeyError, TypeError):
        return []


def update_constraint_dependencies(
    pyproject_path: Path,
    constraints: List[str],
    merge: bool = True,
) -> None:
    """
    Update pyproject.toml with constraint-dependencies.

    This function reads a pyproject.toml file, updates or creates the
    tool.uv.constraint-dependencies section, and writes the file back
    while preserving formatting and comments.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        constraints: List of constraint strings to add.
        merge: If True (default), merge new constraints with existing ones.
            New constraints take precedence for packages that already exist.
            If False, replace all existing constraints.

    Raises:
        TOMLError: If the file cannot be read, parsed, or written.

    Examples:
        >>> update_constraint_dependencies(
        ...     Path('pyproject.toml'),
        ...     ['requests==2.31.0', 'flask>=2.0.0'],
        ...     merge=True
        ... )
    """
    # Read existing file or create new document
    if pyproject_path.exists():
        doc = read_pyproject(pyproject_path)
    else:
        doc = tomlkit.document()

    # Ensure tool section exists
    if 'tool' not in doc:
        doc['tool'] = tomlkit.table()

    tool = doc['tool']

    # Ensure tool.uv section exists
    if 'uv' not in tool:
        tool['uv'] = tomlkit.table()

    uv = tool['uv']

    # Handle merge behavior
    if merge:
        existing = get_constraint_dependencies(doc)
        if existing:
            # Get package names from new constraints
            new_package_names = _get_existing_package_names(constraints)

            # Keep existing constraints for packages not being replaced
            merged: List[str] = []
            for existing_constraint in existing:
                existing_pkg_name = _extract_package_name(existing_constraint)
                if existing_pkg_name not in new_package_names:
                    merged.append(existing_constraint)

            # Add all new constraints
            merged.extend(constraints)

            # Sort alphabetically for consistency
            constraints = sorted(merged, key=lambda c: _extract_package_name(c))

    # Sort constraints alphabetically if not already sorted
    if not merge or not get_constraint_dependencies(doc):
        constraints = sorted(constraints, key=lambda c: _extract_package_name(c))

    # Create a properly formatted array
    constraint_array = tomlkit.array()
    for constraint in constraints:
        constraint_array.append(constraint)

    # Set multiline formatting for readability if there are multiple items
    if len(constraints) > 1:
        constraint_array.multiline(True)

    uv['constraint-dependencies'] = constraint_array

    # Write back to file
    try:
        pyproject_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
    except OSError as e:
        raise TOMLError(f"Failed to write {pyproject_path}: {e}") from e


def create_minimal_pyproject(pyproject_path: Path) -> None:
    """
    Create a minimal pyproject.toml file with only the tool.uv section.

    This is useful when no pyproject.toml exists and we need to create one
    to store constraint-dependencies.

    Args:
        pyproject_path: Path where the pyproject.toml will be created.

    Raises:
        TOMLError: If the file cannot be written.

    Examples:
        >>> create_minimal_pyproject(Path('pyproject.toml'))
        >>> # Creates a file with [tool.uv] section
    """
    doc = tomlkit.document()
    doc['tool'] = tomlkit.table()
    doc['tool']['uv'] = tomlkit.table()

    try:
        pyproject_path.write_text(tomlkit.dumps(doc), encoding='utf-8')
    except OSError as e:
        raise TOMLError(f"Failed to create {pyproject_path}: {e}") from e
