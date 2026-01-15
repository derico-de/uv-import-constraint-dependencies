"""Parser for constraints.txt files.

This module provides functionality to parse pip constraints files,
extracting valid constraint specifications while ignoring comments,
blank lines, and include directives.
"""

import re
from typing import List, Set


def extract_package_name(constraint: str) -> str:
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
        >>> extract_package_name('requests==2.31.0')
        'requests'

        >>> extract_package_name('urllib3>=1.26.0,<2.0.0')
        'urllib3'

        >>> extract_package_name('NumPy>=1.24 ; python_version >= "3.9"')
        'numpy'

        >>> extract_package_name('my-package[extra]>=1.0')
        'my-package'

        >>> extract_package_name('requests[security]==2.31.0')
        'requests'
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


def parse_constraints(content: str) -> List[str]:
    """
    Parse constraints.txt content and return list of constraint strings.

    This function processes the content of a pip constraints file and extracts
    valid constraint specifications. It properly handles:

    - Comments (lines starting with #)
    - Blank lines
    - Package constraints (package==1.0.0, package>=1.0,<2.0)
    - Environment markers (package==1.0.0 ; python_version >= "3.8")
    - Inline comments (text after # on constraint lines)

    Include directives (-r, -c flags) are skipped as they reference other files
    and are not direct constraints.

    Args:
        content: The raw text content of a constraints.txt file.

    Returns:
        A list of constraint strings, with each string representing a single
        package constraint (potentially with version specifiers and/or
        environment markers).

    Examples:
        >>> parse_constraints("requests==2.31.0\\n# comment\\nurllib3>=1.26")
        ['requests==2.31.0', 'urllib3>=1.26']

        >>> parse_constraints("numpy==1.24.3 ; python_version >= '3.9'")
        ["numpy==1.24.3 ; python_version >= '3.9'"]

        >>> parse_constraints("-r requirements.txt\\nflask==2.0.0")
        ['flask==2.0.0']
    """
    constraints: List[str] = []

    for line in content.splitlines():
        # Strip whitespace from both ends
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip comment lines (lines that start with #)
        if line.startswith('#'):
            continue

        # Skip include directives (-r, -c, --requirement, --constraint, etc.)
        if line.startswith('-'):
            continue

        # Handle inline comments: strip everything after #
        # But be careful with URL fragments and quoted strings
        # For simplicity, we only strip inline comments if there's a space before #
        if ' #' in line:
            # Find the position of inline comment
            comment_pos = line.find(' #')
            line = line[:comment_pos].strip()

        # Skip if line became empty after stripping inline comment
        if not line:
            continue

        constraints.append(line)

    return constraints


def _get_package_names(constraints: List[str]) -> Set[str]:
    """
    Get a set of package names from a list of constraints.

    Args:
        constraints: List of constraint strings.

    Returns:
        Set of normalized package names.

    Examples:
        >>> _get_package_names(['requests==2.31.0', 'flask>=2.0.0'])
        {'requests', 'flask'}
    """
    return {extract_package_name(c) for c in constraints}


def merge_constraints(
    base_constraints: List[str],
    custom_constraints: List[str],
) -> List[str]:
    """
    Merge base and custom constraints with custom taking precedence.

    When the same package appears in both lists, the custom constraint version
    is used. Packages unique to each list are all included in the result.
    Package names are compared case-insensitively.

    Args:
        base_constraints: List of constraint strings from the base file.
        custom_constraints: List of constraint strings from the custom file
            that should take precedence.

    Returns:
        A merged list of constraint strings, sorted alphabetically by package
        name. Custom constraints override base constraints for packages that
        appear in both lists.

    Examples:
        >>> merge_constraints(['requests==1.0'], ['requests==2.0'])
        ['requests==2.0']

        >>> merge_constraints(['flask==2.0.0'], ['django==4.0.0'])
        ['django==4.0.0', 'flask==2.0.0']

        >>> merge_constraints(
        ...     ['requests==1.0', 'flask==2.0'],
        ...     ['requests==2.0', 'django==4.0']
        ... )
        ['django==4.0', 'flask==2.0', 'requests==2.0']

        >>> merge_constraints(['Requests==1.0'], ['requests==2.0'])
        ['requests==2.0']

        >>> merge_constraints(['requests==1.0'], [])
        ['requests==1.0']

        >>> merge_constraints([], ['requests==2.0'])
        ['requests==2.0']
    """
    # Handle empty cases
    if not custom_constraints:
        return sorted(base_constraints, key=lambda c: extract_package_name(c))
    if not base_constraints:
        return sorted(custom_constraints, key=lambda c: extract_package_name(c))

    # Get package names from custom constraints
    custom_package_names = _get_package_names(custom_constraints)

    # Keep base constraints for packages not being replaced by custom
    merged: List[str] = []
    for base_constraint in base_constraints:
        base_pkg_name = extract_package_name(base_constraint)
        if base_pkg_name not in custom_package_names:
            merged.append(base_constraint)

    # Add all custom constraints
    merged.extend(custom_constraints)

    # Sort alphabetically by package name for consistency
    return sorted(merged, key=lambda c: extract_package_name(c))
