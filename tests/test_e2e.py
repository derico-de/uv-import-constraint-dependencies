"""End-to-end verification tests for uv-import-constraint-dependencies.

This module provides comprehensive E2E tests that verify the complete workflow:
1. Create sample constraints.txt with test dependencies
2. Create minimal pyproject.toml
3. Run uv-import-constraint-dependencies -c constraints.txt
4. Verify tool.uv.constraint-dependencies section exists with correct values

These tests match the verification requirements from the spec's QA acceptance criteria.
"""

from pathlib import Path
from typing import Callable

import pytest
from click.testing import CliRunner

from uv_import_constraint_dependencies.cli import main
from uv_import_constraint_dependencies.toml_handler import (
    get_constraint_dependencies,
    read_pyproject,
)


# =============================================================================
# Sample Content Constants (matching spec examples)
# =============================================================================

SPEC_SAMPLE_CONSTRAINTS = """\
# Constraints for production dependencies
requests==2.31.0
urllib3>=1.26.0,<2.0.0
certifi>=2023.7.22
numpy==1.24.3 ; python_version >= "3.9"

# Database
psycopg2-binary==2.9.9
"""

SPEC_EXPECTED_CONSTRAINTS = [
    "certifi>=2023.7.22",
    'numpy==1.24.3 ; python_version >= "3.9"',
    "psycopg2-binary==2.9.9",
    "requests==2.31.0",
    "urllib3>=1.26.0,<2.0.0",
]

MINIMAL_PYPROJECT = """\
[project]
name = "test-project"
version = "0.1.0"
"""

PYPROJECT_WITH_EXISTING_CONSTRAINTS = """\
[project]
name = "test-project"
version = "1.0.0"

[tool.uv]
constraint-dependencies = [
    "existing-package==1.0.0",
    "another-package>=2.0.0",
]
"""

PYPROJECT_WITH_COMMENTS = """\
# Project configuration
[project]
name = "test-project"
version = "0.1.0"
description = "A test project"

# Tool configurations
[tool.uv]
# Development settings
dev-dependencies = ["pytest>=7.0"]

# Other tool settings
[tool.pytest.ini_options]
testpaths = ["tests"]
"""


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def create_e2e_project(tmp_path: Path) -> Callable[[str, str], tuple[Path, Path, Path]]:
    """Factory fixture to create a complete project for E2E testing.

    Returns:
        A callable that takes (constraints_content, pyproject_content) and returns
        (project_dir, constraints_path, pyproject_path).
    """

    def _create(
        constraints_content: str,
        pyproject_content: str | None = None,
    ) -> tuple[Path, Path, Path]:
        project_dir = tmp_path / "e2e_project"
        project_dir.mkdir(exist_ok=True)

        constraints_path = project_dir / "constraints.txt"
        constraints_path.write_text(constraints_content, encoding="utf-8")

        pyproject_path = project_dir / "pyproject.toml"
        if pyproject_content is not None:
            pyproject_path.write_text(pyproject_content, encoding="utf-8")

        return project_dir, constraints_path, pyproject_path

    return _create


# =============================================================================
# E2E Test: Basic Usage Flow (Spec Requirement)
# =============================================================================


class TestE2EBasicUsage:
    """E2E tests for basic usage as described in the spec.

    Verification steps:
    1. Create sample constraints.txt with test dependencies
    2. Create minimal pyproject.toml
    3. Run uv-import-constraint-dependencies -c constraints.txt
    4. Verify tool.uv.constraint-dependencies section exists with correct values
    """

    def test_e2e_spec_sample_workflow(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test the exact workflow from the spec with sample constraints.

        This is the primary E2E verification test matching spec requirements.
        """
        # Step 1: Create sample constraints.txt with test dependencies
        # Step 2: Create minimal pyproject.toml
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            SPEC_SAMPLE_CONSTRAINTS,
            MINIMAL_PYPROJECT,
        )

        # Step 3: Run uv-import-constraint-dependencies -c constraints.txt
        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        # Verify CLI completed successfully
        assert result.exit_code == 0, f"CLI failed: {result.output} {result.stderr}"
        assert "Successfully" in result.output

        # Step 4: Verify tool.uv.constraint-dependencies section exists with correct values
        assert pyproject_path.exists()
        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)

        # Verify constraints exist and are correct
        assert len(constraints) == 5, f"Expected 5 constraints, got {len(constraints)}"
        assert constraints == SPEC_EXPECTED_CONSTRAINTS

        # Verify TOML structure
        assert "tool" in doc
        assert "uv" in doc["tool"]
        assert "constraint-dependencies" in doc["tool"]["uv"]

    def test_e2e_creates_pyproject_if_missing(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that pyproject.toml is created when it doesn't exist."""
        # Create only constraints file, no pyproject.toml
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            SPEC_SAMPLE_CONSTRAINTS,
            None,  # No pyproject.toml
        )

        assert not pyproject_path.exists()

        # Run CLI
        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        # Verify success
        assert result.exit_code == 0

        # Verify pyproject.toml was created
        assert pyproject_path.exists()

        # Verify content
        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)
        assert len(constraints) == 5

    def test_e2e_constraints_sorted_alphabetically(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that constraints are sorted alphabetically in output."""
        # Use unsorted constraints
        unsorted_constraints = """\
zebra-lib==1.0.0
apple-lib==2.0.0
mango-lib==3.0.0
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            unsorted_constraints,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)

        # Verify alphabetical ordering
        assert constraints == [
            "apple-lib==2.0.0",
            "mango-lib==3.0.0",
            "zebra-lib==1.0.0",
        ]


# =============================================================================
# E2E Test: Merge Flow
# =============================================================================


class TestE2EMergeFlow:
    """E2E tests for merging with existing constraints."""

    def test_e2e_default_replaces_all(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test default behavior replaces all existing constraints."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0",
            PYPROJECT_WITH_EXISTING_CONSTRAINTS,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)

        # Should only have new constraint (default is replace)
        assert constraints == ["requests==2.31.0"]

    def test_e2e_merge_with_existing_constraints(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test --merge flag: old and new constraints should both be present."""
        # Create project with existing constraints
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0\nflask>=2.0.0",
            PYPROJECT_WITH_EXISTING_CONSTRAINTS,
        )

        # Run CLI with --merge
        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
            "--merge",
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)

        # Should have both old and new constraints
        assert len(constraints) == 4
        assert any("existing-package" in c for c in constraints)
        assert any("another-package" in c for c in constraints)
        assert any("requests" in c for c in constraints)
        assert any("flask" in c for c in constraints)

    def test_e2e_merge_updates_same_package(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that merging updates version for same package."""
        # Create project with existing constraint for same package
        initial_pyproject = """\
[project]
name = "test-project"

[tool.uv]
constraint-dependencies = [
    "requests==2.0.0",
]
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0",  # New version
            initial_pyproject,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
            "--merge",
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)

        # Should have new version, not old
        assert "requests==2.31.0" in constraints
        assert "requests==2.0.0" not in constraints


# =============================================================================
# E2E Test: Formatting Preservation
# =============================================================================


class TestE2EFormattingPreservation:
    """E2E tests for preserving pyproject.toml formatting."""

    def test_e2e_preserves_comments(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that comments in pyproject.toml are preserved."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0",
            PYPROJECT_WITH_COMMENTS,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        # Read raw content to check comments
        content = pyproject_path.read_text()

        assert "# Project configuration" in content
        assert "# Tool configurations" in content
        assert "# Development settings" in content
        assert "# Other tool settings" in content

    def test_e2e_preserves_other_sections(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that other TOML sections are preserved."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0",
            PYPROJECT_WITH_COMMENTS,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)

        # Verify other sections are preserved
        assert doc["project"]["name"] == "test-project"
        assert doc["project"]["version"] == "0.1.0"
        assert "pytest" in doc["tool"]

    def test_e2e_multiline_array_format(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that multiple constraints are formatted as multiline array."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            SPEC_SAMPLE_CONSTRAINTS,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        # Read raw content to check formatting
        content = pyproject_path.read_text()

        # Multiple constraints should be on separate lines
        assert "constraint-dependencies = [" in content


# =============================================================================
# E2E Test: Complex Constraints
# =============================================================================


class TestE2EComplexConstraints:
    """E2E tests for handling complex constraint formats."""

    def test_e2e_environment_markers(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that environment markers are preserved."""
        constraints = """\
numpy==1.24.3 ; python_version >= "3.9"
pandas>=2.0.0 ; sys_platform == "linux"
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            constraints,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        parsed = get_constraint_dependencies(doc)

        # Markers should be preserved
        assert any('python_version >= "3.9"' in c for c in parsed)
        assert any('sys_platform == "linux"' in c for c in parsed)

    def test_e2e_package_extras(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that package extras are preserved."""
        constraints = """\
requests[security]==2.31.0
celery[redis,auth]>=5.3.0
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            constraints,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        parsed = get_constraint_dependencies(doc)

        # Extras should be preserved
        assert any("[security]" in c for c in parsed)
        assert any("[redis,auth]" in c for c in parsed)

    def test_e2e_version_ranges(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that version ranges are preserved."""
        constraints = """\
requests>=2.0,<3.0
urllib3>=1.26.0,<2.0.0
django>=4.2,!=4.2.1
flask~=2.3.0
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            constraints,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        parsed = get_constraint_dependencies(doc)

        # All version specifiers should be preserved
        assert any(">=2.0,<3.0" in c for c in parsed)
        assert any(">=1.26.0,<2.0.0" in c for c in parsed)
        assert any(">=4.2,!=4.2.1" in c for c in parsed)
        assert any("~=2.3.0" in c for c in parsed)


# =============================================================================
# E2E Test: Edge Cases
# =============================================================================


class TestE2EEdgeCases:
    """E2E tests for edge cases and error handling."""

    def test_e2e_empty_constraints_file(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test handling of empty constraints file."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "",
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        # Should exit cleanly with warning
        assert result.exit_code == 0
        assert "No constraints found" in result.stderr

    def test_e2e_comments_only_file(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test handling of constraints file with only comments."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "# Only comments\n# No constraints\n",
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0
        assert "No constraints found" in result.stderr

    def test_e2e_missing_constraints_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test error handling for missing constraints file."""
        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(MINIMAL_PYPROJECT, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(tmp_path / "nonexistent.txt"),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 1
        assert "not found" in result.stderr.lower()

    def test_e2e_invalid_pyproject_toml(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test error handling for invalid pyproject.toml."""
        constraints_path = tmp_path / "constraints.txt"
        constraints_path.write_text("requests==2.31.0", encoding="utf-8")

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text("invalid [toml syntax", encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 1
        assert "Error" in result.stderr

    def test_e2e_include_directives_skipped(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that -r and -c include directives are skipped."""
        constraints = """\
-r base.txt
-c other.txt
--requirement dev.txt
--constraint prod.txt
requests==2.31.0
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            constraints,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        parsed = get_constraint_dependencies(doc)

        # Only actual constraint should be present
        assert parsed == ["requests==2.31.0"]

    def test_e2e_inline_comments_stripped(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that inline comments are stripped from constraints."""
        constraints = """\
requests==2.31.0  # Main HTTP library
flask>=2.0.0 # Web framework
"""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            constraints,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        parsed = get_constraint_dependencies(doc)

        # Comments should be stripped
        assert "requests==2.31.0" in parsed
        assert "flask>=2.0.0" in parsed
        # No inline comments
        assert not any("#" in c for c in parsed)


# =============================================================================
# E2E Test: Idempotency
# =============================================================================


class TestE2EIdempotency:
    """E2E tests for idempotent behavior."""

    def test_e2e_multiple_runs_same_result(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that running CLI multiple times produces same result."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            SPEC_SAMPLE_CONSTRAINTS,
            MINIMAL_PYPROJECT,
        )

        # Run CLI multiple times
        for _ in range(3):
            result = cli_runner.invoke(main, [
                "-c", str(constraints_path),
                "-p", str(pyproject_path),
            ])
            assert result.exit_code == 0

        # Should have same result as single run
        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)
        assert constraints == SPEC_EXPECTED_CONSTRAINTS

    def test_e2e_same_constraints_no_duplicates(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test that running with same constraints doesn't create duplicates."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0",
            MINIMAL_PYPROJECT,
        )

        # Run twice with same constraints
        for _ in range(2):
            result = cli_runner.invoke(main, [
                "-c", str(constraints_path),
                "-p", str(pyproject_path),
            ])
            assert result.exit_code == 0

        doc = read_pyproject(pyproject_path)
        constraints = get_constraint_dependencies(doc)

        # Should have exactly one constraint, no duplicates
        assert constraints == ["requests==2.31.0"]


# =============================================================================
# E2E Test: CLI Help and Version
# =============================================================================


class TestE2ECLIInterface:
    """E2E tests for CLI interface (help, version)."""

    def test_e2e_help_output(self, cli_runner: CliRunner) -> None:
        """Test --help output as specified in acceptance criteria."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "-c" in result.output or "--constraints" in result.output
        assert "pyproject.toml" in result.output
        assert "constraint-dependencies" in result.output

    def test_e2e_version_output(self, cli_runner: CliRunner) -> None:
        """Test --version output as specified in acceptance criteria."""
        from uv_import_constraint_dependencies import __version__

        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output
        assert "uv-import-constraint-dependencies" in result.output

    def test_e2e_missing_required_option(self, cli_runner: CliRunner) -> None:
        """Test error when -c option is missing."""
        result = cli_runner.invoke(main, [])

        assert result.exit_code != 0
        assert "constraints" in result.stderr.lower() or "required" in result.stderr.lower()


# =============================================================================
# E2E Test: Output Messages
# =============================================================================


class TestE2EOutputMessages:
    """E2E tests for CLI output messages."""

    def test_e2e_success_message_count(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test success message shows correct constraint count."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            SPEC_SAMPLE_CONSTRAINTS,
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0
        assert "5 constraints" in result.output  # 5 in spec sample

    def test_e2e_success_message_singular(
        self,
        cli_runner: CliRunner,
        create_e2e_project: Callable,
    ) -> None:
        """Test success message uses singular 'constraint' for count=1."""
        project_dir, constraints_path, pyproject_path = create_e2e_project(
            "requests==2.31.0",
            MINIMAL_PYPROJECT,
        )

        result = cli_runner.invoke(main, [
            "-c", str(constraints_path),
            "-p", str(pyproject_path),
        ])

        assert result.exit_code == 0
        assert "1 constraint " in result.output  # Note the space to avoid matching "constraints"


# =============================================================================
# E2E Test: Real Local Files Integration
# =============================================================================


class TestE2ERealLocalFiles:
    """E2E tests using real local example files from fixtures directory."""

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get the path to the fixtures directory."""
        return Path(__file__).parent / "fixtures"

    def test_real_constraints_file_replace(
        self,
        cli_runner: CliRunner,
        fixtures_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test importing from real example constraints.txt file with replace mode."""
        # Copy example pyproject.toml to temp directory
        example_pyproject = fixtures_dir / "example_pyproject.toml"
        target_pyproject = tmp_path / "pyproject.toml"
        target_pyproject.write_text(example_pyproject.read_text(), encoding="utf-8")

        # Use real constraints file
        constraints_file = fixtures_dir / "example_constraints.txt"

        # Run CLI (default replace mode)
        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(target_pyproject),
        ])

        assert result.exit_code == 0
        assert "Successfully" in result.output

        # Verify pyproject.toml was updated correctly
        doc = read_pyproject(target_pyproject)
        constraints = get_constraint_dependencies(doc)

        # Should have 10 constraints (from example file, excluding -r/-c directives)
        assert len(constraints) == 10

        # Verify specific constraints are present
        assert "requests==2.31.0" in constraints
        assert any("numpy" in c for c in constraints)
        assert any("flask" in c for c in constraints)
        assert any("celery" in c for c in constraints)

        # Verify environment markers are preserved
        assert any('python_version >= "3.9"' in c for c in constraints)

        # Verify extras are preserved
        assert any("[async]" in c for c in constraints)
        assert any("[redis,auth]" in c for c in constraints)

        # Old constraints should be replaced
        assert not any("old-package" in c for c in constraints)
        assert not any("legacy-lib" in c for c in constraints)

        # Other sections should be preserved
        assert doc["project"]["name"] == "example-project"
        assert "ruff" in doc["tool"]
        assert "pytest" in doc["tool"]

    def test_real_constraints_file_merge(
        self,
        cli_runner: CliRunner,
        fixtures_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test importing from real example constraints.txt file with merge mode."""
        # Copy example pyproject.toml to temp directory
        example_pyproject = fixtures_dir / "example_pyproject.toml"
        target_pyproject = tmp_path / "pyproject.toml"
        target_pyproject.write_text(example_pyproject.read_text(), encoding="utf-8")

        # Use real constraints file
        constraints_file = fixtures_dir / "example_constraints.txt"

        # Run CLI with --merge
        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(target_pyproject),
            "--merge",
        ])

        assert result.exit_code == 0
        assert "Successfully" in result.output

        # Verify pyproject.toml was updated correctly
        doc = read_pyproject(target_pyproject)
        constraints = get_constraint_dependencies(doc)

        # Should have 12 constraints (10 new + 2 old that weren't replaced)
        assert len(constraints) == 12

        # Verify new constraints are present
        assert "requests==2.31.0" in constraints
        assert any("flask" in c for c in constraints)

        # Old constraints should be preserved (since they have different package names)
        assert any("old-package" in c for c in constraints)
        assert any("legacy-lib" in c for c in constraints)

        # Comments in pyproject.toml should be preserved
        content = target_pyproject.read_text()
        assert "# Example pyproject.toml for testing" in content
        assert "# Existing tool configurations" in content

    def test_real_constraints_to_new_pyproject(
        self,
        cli_runner: CliRunner,
        fixtures_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test importing from real constraints file to new pyproject.toml."""
        # Use real constraints file
        constraints_file = fixtures_dir / "example_constraints.txt"
        target_pyproject = tmp_path / "pyproject.toml"

        # pyproject.toml doesn't exist yet
        assert not target_pyproject.exists()

        # Run CLI
        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(target_pyproject),
        ])

        assert result.exit_code == 0
        assert target_pyproject.exists()

        # Verify constraints were imported
        doc = read_pyproject(target_pyproject)
        constraints = get_constraint_dependencies(doc)

        assert len(constraints) == 10
        assert "requests==2.31.0" in constraints

        # Constraints should be sorted alphabetically
        package_names = [c.split("==")[0].split(">=")[0].split("<")[0].split("[")[0].split(";")[0].strip()
                        for c in constraints]
        assert package_names == sorted(package_names, key=str.lower)
