"""Pytest fixtures and helpers for uv-import-constraint-dependencies tests.

This module provides reusable fixtures for testing, including:
- Sample constraints file content
- Temporary file helpers
- Sample pyproject.toml content
"""

from pathlib import Path
from typing import Callable

import pytest


# =============================================================================
# Sample Constraints Content Fixtures
# =============================================================================


@pytest.fixture
def basic_constraints_content() -> str:
    """Simple constraints.txt content with basic version specifiers."""
    return """\
requests==2.31.0
urllib3>=1.26.0,<2.0.0
certifi>=2023.7.22
"""


@pytest.fixture
def constraints_with_comments() -> str:
    """Constraints content with comments and blank lines."""
    return """\
# Production dependencies
requests==2.31.0
urllib3>=1.26.0,<2.0.0

# Security
certifi>=2023.7.22

# This is the last one
flask==2.3.3
"""


@pytest.fixture
def constraints_with_markers() -> str:
    """Constraints content with environment markers."""
    return """\
numpy==1.24.3 ; python_version >= "3.9"
pandas>=2.0.0 ; sys_platform == "linux"
pywin32>=306 ; sys_platform == "win32"
"""


@pytest.fixture
def constraints_with_extras() -> str:
    """Constraints content with package extras."""
    return """\
requests[security]==2.31.0
celery[redis,auth]>=5.3.0
uvicorn[standard]>=0.23.0
"""


@pytest.fixture
def constraints_with_directives() -> str:
    """Constraints content with include directives to skip."""
    return """\
# Include other files (should be skipped)
-r requirements.txt
-c base-constraints.txt
--constraint other.txt
--requirement dev.txt

# Actual constraints
requests==2.31.0
flask>=2.0.0
"""


@pytest.fixture
def constraints_with_inline_comments() -> str:
    """Constraints content with inline comments."""
    return """\
requests==2.31.0  # Main HTTP library
urllib3>=1.26.0,<2.0.0  # HTTP connection pooling
certifi>=2023.7.22 # SSL certificates
"""


@pytest.fixture
def empty_constraints_content() -> str:
    """Empty constraints content."""
    return ""


@pytest.fixture
def comment_only_constraints() -> str:
    """Constraints content with only comments (no actual constraints)."""
    return """\
# This file only has comments
# No actual constraints here

# Another comment
"""


@pytest.fixture
def complex_constraints_content() -> str:
    """Complex constraints content combining multiple features."""
    return """\
# Constraints for production dependencies
requests==2.31.0  # Main HTTP client
urllib3>=1.26.0,<2.0.0
certifi>=2023.7.22

# Data processing
numpy==1.24.3 ; python_version >= "3.9"
pandas>=2.0.0,<3.0.0 ; python_version >= "3.10"

# Database
psycopg2-binary==2.9.9

# Include directive (should be skipped)
-r dev-requirements.txt

# Web framework
flask[async]==2.3.3
django>=4.2.0,<5.0.0

"""


# =============================================================================
# Sample pyproject.toml Content Fixtures
# =============================================================================


@pytest.fixture
def minimal_pyproject_content() -> str:
    """Minimal pyproject.toml with only project name."""
    return """\
[project]
name = "test-project"
version = "0.1.0"
"""


@pytest.fixture
def pyproject_with_tool_uv() -> str:
    """pyproject.toml with existing tool.uv section but no constraints."""
    return """\
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
dev-dependencies = ["pytest>=7.0"]
"""


@pytest.fixture
def pyproject_with_constraints() -> str:
    """pyproject.toml with existing constraint-dependencies."""
    return """\
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
constraint-dependencies = [
    "existing-package==1.0.0",
    "another-package>=2.0.0",
]
"""


@pytest.fixture
def pyproject_with_comments() -> str:
    """pyproject.toml with comments to test formatting preservation."""
    return """\
# Project configuration
[project]
name = "test-project"
version = "0.1.0"
description = "A test project"

# Tool configurations
[tool.uv]
# These are the existing constraints
constraint-dependencies = [
    "existing-package==1.0.0",
]

# Other tool settings
[tool.pytest.ini_options]
testpaths = ["tests"]
"""


@pytest.fixture
def empty_pyproject_content() -> str:
    """Empty pyproject.toml content."""
    return ""


# =============================================================================
# Temporary File Fixtures
# =============================================================================


@pytest.fixture
def tmp_constraints_file(
    tmp_path: Path,
    basic_constraints_content: str,
) -> Path:
    """Create a temporary constraints.txt file with basic content."""
    constraints_file = tmp_path / "constraints.txt"
    constraints_file.write_text(basic_constraints_content, encoding="utf-8")
    return constraints_file


@pytest.fixture
def tmp_pyproject_file(
    tmp_path: Path,
    minimal_pyproject_content: str,
) -> Path:
    """Create a temporary pyproject.toml file with minimal content."""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")
    return pyproject_file


@pytest.fixture
def tmp_empty_dir(tmp_path: Path) -> Path:
    """Create an empty temporary directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    return empty_dir


# =============================================================================
# Factory Fixtures
# =============================================================================


@pytest.fixture
def create_constraints_file(tmp_path: Path) -> Callable[[str, str], Path]:
    """Factory fixture to create constraints files with custom content.

    Returns:
        A callable that takes (filename, content) and returns the created file path.

    Example:
        def test_something(create_constraints_file):
            constraints_path = create_constraints_file(
                "my-constraints.txt",
                "requests==2.31.0\\nflask>=2.0.0"
            )
            # Use constraints_path in test...
    """

    def _create(filename: str, content: str) -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create


@pytest.fixture
def create_pyproject_file(tmp_path: Path) -> Callable[[str], Path]:
    """Factory fixture to create pyproject.toml files with custom content.

    Returns:
        A callable that takes content and returns the created file path.

    Example:
        def test_something(create_pyproject_file):
            pyproject_path = create_pyproject_file(
                '[project]\\nname = "test"'
            )
            # Use pyproject_path in test...
    """

    def _create(content: str) -> Path:
        file_path = tmp_path / "pyproject.toml"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create


@pytest.fixture
def create_project_dir(
    tmp_path: Path,
) -> Callable[[str, str], tuple[Path, Path, Path]]:
    """Factory fixture to create a project directory with both files.

    Creates a directory containing both a constraints.txt and pyproject.toml file.

    Returns:
        A callable that takes (constraints_content, pyproject_content) and returns
        a tuple of (project_dir, constraints_path, pyproject_path).

    Example:
        def test_something(create_project_dir):
            project_dir, constraints, pyproject = create_project_dir(
                "requests==2.31.0",
                '[project]\\nname = "test"'
            )
            # Use paths in test...
    """

    def _create(
        constraints_content: str,
        pyproject_content: str,
    ) -> tuple[Path, Path, Path]:
        project_dir = tmp_path / "project"
        project_dir.mkdir(exist_ok=True)

        constraints_path = project_dir / "constraints.txt"
        constraints_path.write_text(constraints_content, encoding="utf-8")

        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text(pyproject_content, encoding="utf-8")

        return project_dir, constraints_path, pyproject_path

    return _create


# =============================================================================
# Expected Results Fixtures
# =============================================================================


@pytest.fixture
def expected_basic_constraints() -> list[str]:
    """Expected parsed result for basic_constraints_content."""
    return [
        "requests==2.31.0",
        "urllib3>=1.26.0,<2.0.0",
        "certifi>=2023.7.22",
    ]


@pytest.fixture
def expected_complex_constraints() -> list[str]:
    """Expected parsed result for complex_constraints_content (sorted)."""
    return [
        "certifi>=2023.7.22",
        "django>=4.2.0,<5.0.0",
        "flask[async]==2.3.3",
        "numpy==1.24.3 ; python_version >= \"3.9\"",
        "pandas>=2.0.0,<3.0.0 ; python_version >= \"3.10\"",
        "psycopg2-binary==2.9.9",
        "requests==2.31.0",
        "urllib3>=1.26.0,<2.0.0",
    ]


# =============================================================================
# URI Fixtures
# =============================================================================


@pytest.fixture
def valid_http_uri() -> str:
    """A valid HTTP URI for testing URI detection."""
    return "http://example.com/constraints.txt"


@pytest.fixture
def valid_https_uri() -> str:
    """A valid HTTPS URI for testing URI detection."""
    return "https://example.com/constraints.txt"


@pytest.fixture
def invalid_uris() -> list[str]:
    """List of strings that should not be detected as URIs."""
    return [
        "constraints.txt",
        "/path/to/constraints.txt",
        "./relative/path.txt",
        "file:///local/file.txt",
        "ftp://server.com/file.txt",
        "",
    ]


# =============================================================================
# Custom Constraints Content Fixtures
# =============================================================================


@pytest.fixture
def custom_constraints_basic() -> str:
    """Basic custom constraints content for merging tests."""
    return """\
django>=4.2.0
celery>=5.3.0
redis>=4.5.0
"""


@pytest.fixture
def custom_constraints_override() -> str:
    """Custom constraints that override packages in basic_constraints_content.

    Use with basic_constraints_content to test that custom versions take precedence.
    - requests==2.31.0 in base -> requests==2.32.0 in custom (override)
    - urllib3>=1.26.0,<2.0.0 in base -> urllib3>=2.0.0 in custom (override)
    """
    return """\
requests==2.32.0
urllib3>=2.0.0
"""


@pytest.fixture
def custom_constraints_mixed() -> str:
    """Custom constraints with both override and new packages.

    Use with basic_constraints_content to test union and override together.
    - requests: overrides base version
    - django, celery: new packages unique to custom
    """
    return """\
# Override from base constraints
requests==2.32.0

# New packages not in base
django>=4.2.0
celery>=5.3.0
"""


@pytest.fixture
def custom_constraints_with_extras() -> str:
    """Custom constraints with package extras that override base packages.

    Tests that packages are matched by name regardless of extras.
    """
    return """\
requests[security]==2.32.0
celery[redis,auth]>=5.3.0
"""


@pytest.fixture
def custom_constraints_with_markers() -> str:
    """Custom constraints with environment markers."""
    return """\
requests==2.32.0 ; python_version >= "3.10"
django>=4.2.0 ; sys_platform == "linux"
"""


@pytest.fixture
def custom_constraints_case_mismatch() -> str:
    """Custom constraints with different case than base packages.

    Tests case-insensitive package name matching.
    - Base might have 'requests' but custom has 'Requests'
    """
    return """\
Requests==2.32.0
URLLIB3>=2.0.0
Django>=4.2.0
"""


@pytest.fixture
def custom_constraints_empty() -> str:
    """Empty custom constraints content.

    When merged with base, should result in base constraints only.
    """
    return ""


@pytest.fixture
def custom_constraints_comments_only() -> str:
    """Custom constraints with only comments (no actual constraints).

    When merged with base, should result in base constraints only.
    """
    return """\
# This custom constraints file only has comments
# No actual package constraints here

# Another comment
"""


@pytest.fixture
def custom_constraints_complex() -> str:
    """Complex custom constraints combining multiple features.

    For comprehensive merge testing with complex_constraints_content.
    """
    return """\
# Override existing packages with new versions
requests==2.32.0  # Newer than base
numpy==1.25.0 ; python_version >= "3.9"  # Override with different version

# Add new packages not in base
sqlalchemy>=2.0.0
pydantic>=2.0.0,<3.0.0

# Package with extras
aiohttp[speedups]>=3.9.0

# Include directive (should be skipped)
-r local-dev.txt
"""


@pytest.fixture
def expected_basic_custom_merge() -> list[str]:
    """Expected result of merging basic_constraints_content with custom_constraints_basic.

    Alphabetically sorted, union of both constraint sets.
    """
    return [
        "celery>=5.3.0",
        "certifi>=2023.7.22",
        "django>=4.2.0",
        "redis>=4.5.0",
        "requests==2.31.0",
        "urllib3>=1.26.0,<2.0.0",
    ]


@pytest.fixture
def expected_override_merge() -> list[str]:
    """Expected result of merging basic_constraints_content with custom_constraints_override.

    Custom versions take precedence for requests and urllib3.
    """
    return [
        "certifi>=2023.7.22",
        "requests==2.32.0",
        "urllib3>=2.0.0",
    ]


@pytest.fixture
def expected_mixed_merge() -> list[str]:
    """Expected result of merging basic_constraints_content with custom_constraints_mixed.

    - requests: overridden by custom version
    - urllib3, certifi: from base (not in custom)
    - django, celery: new from custom
    """
    return [
        "celery>=5.3.0",
        "certifi>=2023.7.22",
        "django>=4.2.0",
        "requests==2.32.0",
        "urllib3>=1.26.0,<2.0.0",
    ]


# =============================================================================
# Custom Constraints File Fixtures
# =============================================================================


@pytest.fixture
def tmp_custom_constraints_file(
    tmp_path: Path,
    custom_constraints_basic: str,
) -> Path:
    """Create a temporary custom-constraints.txt file with basic content."""
    custom_file = tmp_path / "custom-constraints.txt"
    custom_file.write_text(custom_constraints_basic, encoding="utf-8")
    return custom_file


@pytest.fixture
def create_custom_constraints_file(tmp_path: Path) -> Callable[[str, str], Path]:
    """Factory fixture to create custom constraints files with custom content.

    Returns:
        A callable that takes (filename, content) and returns the created file path.

    Example:
        def test_something(create_custom_constraints_file):
            custom_path = create_custom_constraints_file(
                "custom-constraints.txt",
                "requests==2.32.0\\ndjango>=4.2.0"
            )
            # Use custom_path in test...
    """

    def _create(filename: str, content: str) -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create


@pytest.fixture
def create_project_with_custom_constraints(
    tmp_path: Path,
) -> Callable[[str, str, str], tuple[Path, Path, Path, Path]]:
    """Factory fixture to create a project directory with base, custom, and pyproject files.

    Creates a directory containing:
    - constraints.txt (base constraints)
    - custom-constraints.txt (custom override constraints)
    - pyproject.toml

    Returns:
        A callable that takes (base_content, custom_content, pyproject_content) and returns
        a tuple of (project_dir, base_constraints_path, custom_constraints_path, pyproject_path).

    Example:
        def test_something(create_project_with_custom_constraints):
            project_dir, base, custom, pyproject = create_project_with_custom_constraints(
                "requests==2.31.0",
                "requests==2.32.0",
                '[project]\\nname = "test"'
            )
            # Use paths in test...
    """

    def _create(
        base_content: str,
        custom_content: str,
        pyproject_content: str,
    ) -> tuple[Path, Path, Path, Path]:
        project_dir = tmp_path / "project"
        project_dir.mkdir(exist_ok=True)

        base_path = project_dir / "constraints.txt"
        base_path.write_text(base_content, encoding="utf-8")

        custom_path = project_dir / "custom-constraints.txt"
        custom_path.write_text(custom_content, encoding="utf-8")

        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text(pyproject_content, encoding="utf-8")

        return project_dir, base_path, custom_path, pyproject_path

    return _create
