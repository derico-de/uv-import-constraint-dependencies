"""Parser for constraints.txt files.

This module provides functionality to parse pip constraints files,
extracting valid constraint specifications while ignoring comments,
blank lines, and include directives.
"""

from typing import List


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
