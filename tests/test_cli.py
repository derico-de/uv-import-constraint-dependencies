"""Integration tests for the CLI module.

This module tests the command-line interface for uv-import-constraint-dependencies,
covering various scenarios including:
- Local file processing
- Error handling for missing files
- pyproject.toml updates
- Remote URI processing (with mocking)
- CLI help and version output
- Various error scenarios and edge cases
"""

import os
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from uv_import_constraint_dependencies import __version__
from uv_import_constraint_dependencies.cli import (
    ConstraintsError,
    _read_constraints,
    main,
)
from uv_import_constraint_dependencies.toml_handler import (
    get_constraint_dependencies,
    read_pyproject,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def isolated_runner() -> CliRunner:
    """Create a Click CLI runner with isolated filesystem."""
    return CliRunner()


# =============================================================================
# Test CLI Help and Version
# =============================================================================


class TestCLIHelpAndVersion:
    """Tests for CLI help and version output."""

    def test_help_output(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that --help shows usage information."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--constraints" in result.output or "-c" in result.output
        assert "pyproject.toml" in result.output

    def test_short_help_flag(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that -h does not work (Click default, --help required)."""
        result = cli_runner.invoke(main, ["-h"])
        # -h is not a recognized option by default in Click
        assert result.exit_code != 0

    def test_version_output(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that --version shows correct version."""
        result = cli_runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "uv-import-constraint-dependencies" in result.output

    def test_help_includes_examples(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that help includes usage examples."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        # Check for example patterns
        assert "constraints.txt" in result.output

    def test_help_includes_merge_flag(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that help includes --merge flag documentation."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--merge" in result.output


# =============================================================================
# Test Local File Processing
# =============================================================================


class TestLocalFileProcessing:
    """Tests for processing local constraints files."""

    def test_basic_local_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test processing a basic local constraints file."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert "Successfully" in result.output
        assert "constraint" in result.output.lower()

        # Verify pyproject.toml was updated
        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        assert "requests==2.31.0" in constraints
        assert any("urllib3" in c for c in constraints)
        assert any("certifi" in c for c in constraints)

    def test_local_file_with_complex_constraints(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        complex_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test processing a constraints file with complex content."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(complex_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        # Should have parsed all valid constraints
        assert len(constraints) == 8  # 8 valid constraints in complex content

    def test_local_file_relative_path(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test processing with relative file paths."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        # Change to tmp_path and use relative paths
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = cli_runner.invoke(main, [
                "-c", "constraints.txt",
                "-p", "pyproject.toml",
            ])
            assert result.exit_code == 0
        finally:
            os.chdir(original_dir)

    def test_local_file_creates_pyproject_if_missing(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
    ) -> None:
        """Test that pyproject.toml is created if it doesn't exist."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        assert not pyproject_file.exists()

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert pyproject_file.exists()

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        assert len(constraints) == 3

    def test_short_option_for_constraints(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that -c short option works."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

    def test_short_option_for_pyproject(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that -p short option works."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "--constraints", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0


# =============================================================================
# Test Missing File Errors
# =============================================================================


class TestMissingFileErrors:
    """Tests for error handling when files are missing."""

    def test_missing_constraints_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test error message for missing constraints file."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        nonexistent = tmp_path / "nonexistent.txt"

        result = cli_runner.invoke(main, [
            "-c", str(nonexistent),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 1
        assert "Error" in result.stderr or "error" in result.stderr.lower()
        assert "not found" in result.stderr.lower() or "nonexistent" in result.stderr

    def test_constraints_path_is_directory(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test error message when constraints path is a directory."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        dir_path = tmp_path / "some_dir"
        dir_path.mkdir()

        result = cli_runner.invoke(main, [
            "-c", str(dir_path),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 1
        assert "Error" in result.stderr or "error" in result.stderr.lower()

    def test_missing_required_option(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test error when required -c option is missing."""
        result = cli_runner.invoke(main, [])

        assert result.exit_code != 0
        # Click shows an error about missing option
        assert "constraints" in result.stderr.lower() or "required" in result.stderr.lower()


# =============================================================================
# Test pyproject.toml Updates
# =============================================================================


class TestPyprojectUpdates:
    """Tests for pyproject.toml update behavior."""

    def test_default_replaces_all(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        pyproject_with_constraints: str,
    ) -> None:
        """Test that default behavior replaces all existing constraints."""
        constraints_content = "requests==2.31.0\nflask>=2.0.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_with_constraints, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should only have new constraints (default is replace)
        assert len(constraints) == 2
        assert any("requests" in c for c in constraints)
        assert any("flask" in c for c in constraints)
        assert not any("existing-package" in c for c in constraints)

    def test_merge_with_existing_constraints(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        pyproject_with_constraints: str,
    ) -> None:
        """Test that --merge merges new constraints with existing ones."""
        constraints_content = "requests==2.31.0\nflask>=2.0.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_with_constraints, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
            "--merge",
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have existing + new (total 4: existing-package, another-package, requests, flask)
        assert len(constraints) == 4
        assert any("existing-package" in c for c in constraints)
        assert any("another-package" in c for c in constraints)
        assert any("requests" in c for c in constraints)
        assert any("flask" in c for c in constraints)

    def test_preserves_pyproject_formatting(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        pyproject_with_comments: str,
    ) -> None:
        """Test that pyproject.toml formatting and comments are preserved."""
        constraints_content = "requests==2.31.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_with_comments, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        # Check that comments are preserved
        content = pyproject_file.read_text()
        assert "# Project configuration" in content
        assert "# Tool configurations" in content
        assert "# Other tool settings" in content

    def test_constraints_sorted_alphabetically(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that constraints are sorted alphabetically."""
        constraints_content = "zebra==1.0.0\napple==2.0.0\nmango==3.0.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should be sorted
        assert constraints == ["apple==2.0.0", "mango==3.0.0", "zebra==1.0.0"]

    def test_merge_updates_same_package(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        pyproject_with_constraints: str,
    ) -> None:
        """Test that merging updates version for same package."""
        # Update existing-package to new version
        constraints_content = "existing-package==2.0.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_with_constraints, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
            "--merge",
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have new version
        assert "existing-package==2.0.0" in constraints
        assert "existing-package==1.0.0" not in constraints


# =============================================================================
# Test Empty and Edge Cases
# =============================================================================


class TestEmptyAndEdgeCases:
    """Tests for empty content and edge cases."""

    def test_empty_constraints_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test handling of empty constraints file."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text("", encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        # Should exit cleanly (exit code 0) with a message
        assert result.exit_code == 0
        assert "No constraints found" in result.stderr

    def test_comments_only_constraints_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
        comment_only_constraints: str,
    ) -> None:
        """Test handling of constraints file with only comments."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(comment_only_constraints, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert "No constraints found" in result.stderr

    def test_constraints_with_environment_markers(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
        constraints_with_markers: str,
    ) -> None:
        """Test handling of constraints with environment markers."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_with_markers, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Environment markers should be preserved
        assert any('python_version >= "3.9"' in c for c in constraints)
        assert any('sys_platform == "linux"' in c for c in constraints)

    def test_constraints_with_extras(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
        constraints_with_extras: str,
    ) -> None:
        """Test handling of constraints with package extras."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_with_extras, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Extras should be preserved
        assert any("[security]" in c for c in constraints)
        assert any("[redis,auth]" in c for c in constraints)


# =============================================================================
# Test Remote URI Processing (with mocking)
# =============================================================================


class TestRemoteURIProcessing:
    """Tests for processing remote constraints files via URI."""

    def test_http_uri_processing(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test processing constraints from HTTP URI."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        mock_content = b"requests==2.31.0\nflask>=2.0.0"

        with patch("uv_import_constraint_dependencies.cli.is_uri") as mock_is_uri, \
             patch("uv_import_constraint_dependencies.cli.fetch_constraints") as mock_fetch:
            mock_is_uri.return_value = True
            mock_fetch.return_value = mock_content.decode("utf-8")

            result = cli_runner.invoke(main, [
                "-c", "http://example.com/constraints.txt",
                "-p", str(pyproject_file),
            ])

            assert result.exit_code == 0
            mock_is_uri.assert_called_once_with("http://example.com/constraints.txt")
            mock_fetch.assert_called_once_with("http://example.com/constraints.txt")

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        assert any("requests" in c for c in constraints)
        assert any("flask" in c for c in constraints)

    def test_https_uri_processing(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test processing constraints from HTTPS URI."""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        mock_content = "django>=4.2.0"

        with patch("uv_import_constraint_dependencies.cli.is_uri") as mock_is_uri, \
             patch("uv_import_constraint_dependencies.cli.fetch_constraints") as mock_fetch:
            mock_is_uri.return_value = True
            mock_fetch.return_value = mock_content

            result = cli_runner.invoke(main, [
                "-c", "https://example.com/constraints.txt",
                "-p", str(pyproject_file),
            ])

            assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        assert any("django" in c for c in constraints)

    def test_uri_fetch_error(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test error handling when URI fetch fails."""
        from uv_import_constraint_dependencies.uri_handler import URIError

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        with patch("uv_import_constraint_dependencies.cli.is_uri") as mock_is_uri, \
             patch("uv_import_constraint_dependencies.cli.fetch_constraints") as mock_fetch:
            mock_is_uri.return_value = True
            mock_fetch.side_effect = URIError("Connection refused")

            result = cli_runner.invoke(main, [
                "-c", "https://example.com/constraints.txt",
                "-p", str(pyproject_file),
            ])

            assert result.exit_code == 1
            assert "Error" in result.stderr or "error" in result.stderr.lower()


# =============================================================================
# Test Invalid TOML Handling
# =============================================================================


class TestInvalidTOMLHandling:
    """Tests for handling invalid pyproject.toml files."""

    def test_invalid_pyproject_toml(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test error handling for invalid pyproject.toml."""
        constraints_content = "requests==2.31.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("invalid [toml syntax", encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 1
        assert "Error" in result.stderr or "error" in result.stderr.lower()


# =============================================================================
# Test _read_constraints Helper
# =============================================================================


class TestReadConstraintsHelper:
    """Tests for the _read_constraints helper function."""

    def test_read_local_file(
        self,
        tmp_path: Path,
        basic_constraints_content: str,
    ) -> None:
        """Test reading local constraints file."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        content = _read_constraints(str(constraints_file))

        assert "requests==2.31.0" in content
        assert "urllib3" in content

    def test_read_local_file_not_found(
        self,
        tmp_path: Path,
    ) -> None:
        """Test error when local file not found."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(ConstraintsError) as exc_info:
            _read_constraints(str(nonexistent))

        assert "not found" in str(exc_info.value)

    def test_read_local_file_is_directory(
        self,
        tmp_path: Path,
    ) -> None:
        """Test error when path is a directory."""
        dir_path = tmp_path / "some_dir"
        dir_path.mkdir()

        with pytest.raises(ConstraintsError) as exc_info:
            _read_constraints(str(dir_path))

        assert "not a file" in str(exc_info.value)

    def test_read_remote_uri(self) -> None:
        """Test reading from remote URI."""
        mock_content = "requests==2.31.0"

        with patch("uv_import_constraint_dependencies.cli.is_uri") as mock_is_uri, \
             patch("uv_import_constraint_dependencies.cli.fetch_constraints") as mock_fetch:
            mock_is_uri.return_value = True
            mock_fetch.return_value = mock_content

            content = _read_constraints("https://example.com/constraints.txt")

            assert content == mock_content

    def test_read_remote_uri_error(self) -> None:
        """Test error when remote URI fetch fails."""
        from uv_import_constraint_dependencies.uri_handler import URIError

        with patch("uv_import_constraint_dependencies.cli.is_uri") as mock_is_uri, \
             patch("uv_import_constraint_dependencies.cli.fetch_constraints") as mock_fetch:
            mock_is_uri.return_value = True
            mock_fetch.side_effect = URIError("Network error")

            with pytest.raises(ConstraintsError) as exc_info:
                _read_constraints("https://example.com/constraints.txt")

            assert "Network error" in str(exc_info.value)


# =============================================================================
# Test ConstraintsError Exception
# =============================================================================


class TestConstraintsError:
    """Tests for ConstraintsError exception class."""

    def test_constraints_error_is_exception(self) -> None:
        """Test that ConstraintsError is an Exception subclass."""
        assert issubclass(ConstraintsError, Exception)

    def test_constraints_error_with_message(self) -> None:
        """Test that ConstraintsError can be raised with a message."""
        with pytest.raises(ConstraintsError) as exc_info:
            raise ConstraintsError("Test error message")

        assert "Test error message" in str(exc_info.value)


# =============================================================================
# Test Success Output Messages
# =============================================================================


class TestSuccessOutput:
    """Tests for success output messages."""

    def test_success_message_single_constraint(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test success message for single constraint."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text("requests==2.31.0", encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert "1 constraint" in result.output
        assert "Successfully" in result.output

    def test_success_message_multiple_constraints(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test success message for multiple constraints."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text("requests==2.31.0\nflask>=2.0.0\ndjango<5.0.0", encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert "3 constraints" in result.output


# =============================================================================
# Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """End-to-end integration test scenarios."""

    def test_full_workflow_new_project(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow for a new project."""
        # Create constraints file
        constraints_content = """\
# Production dependencies
requests==2.31.0
urllib3>=1.26.0,<2.0.0

# Data processing
numpy==1.24.3 ; python_version >= "3.9"
"""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(constraints_content, encoding="utf-8")

        # pyproject.toml doesn't exist yet
        pyproject_file = tmp_path / "pyproject.toml"

        # Run CLI
        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        # Verify
        assert result.exit_code == 0
        assert pyproject_file.exists()

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        assert len(constraints) == 3
        assert any("requests" in c for c in constraints)
        assert any("urllib3" in c for c in constraints)
        assert any("numpy" in c for c in constraints)

    def test_full_workflow_existing_project_merge(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow for merging into existing project."""
        # Create initial pyproject.toml with constraints
        initial_pyproject = """\
[project]
name = "my-project"
version = "1.0.0"

[tool.uv]
constraint-dependencies = [
    "existing-package==1.0.0",
]

[tool.black]
line-length = 88
"""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(initial_pyproject, encoding="utf-8")

        # Create new constraints
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text("requests==2.31.0\nflask>=2.0.0", encoding="utf-8")

        # Run CLI with --merge
        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
            "--merge",
        ])

        # Verify
        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have all constraints
        assert len(constraints) == 3
        assert any("existing-package" in c for c in constraints)
        assert any("requests" in c for c in constraints)
        assert any("flask" in c for c in constraints)

        # Other sections should be preserved
        assert doc["project"]["name"] == "my-project"
        assert "black" in doc["tool"]

    def test_full_workflow_replace_all(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow with default replace behavior."""
        # Create initial pyproject.toml with constraints
        initial_pyproject = """\
[project]
name = "my-project"

[tool.uv]
constraint-dependencies = [
    "old-package==1.0.0",
    "another-old==2.0.0",
]
"""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(initial_pyproject, encoding="utf-8")

        # Create new constraints
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text("requests==2.31.0", encoding="utf-8")

        # Run CLI (default is replace)
        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        # Verify
        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should only have new constraint
        assert constraints == ["requests==2.31.0"]

    def test_idempotent_multiple_runs(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that running CLI multiple times is idempotent."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text("requests==2.31.0", encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        # Run twice
        for _ in range(2):
            result = cli_runner.invoke(main, [
                "-c", str(constraints_file),
                "-p", str(pyproject_file),
            ])
            assert result.exit_code == 0

        # Should still have exactly one constraint
        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        assert constraints == ["requests==2.31.0"]


# =============================================================================
# Test Default Pyproject Path
# =============================================================================


class TestDefaultPyprojectPath:
    """Tests for default pyproject.toml path behavior."""

    def test_default_pyproject_in_current_dir(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that default pyproject.toml path is current directory."""
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        # Change to tmp_path directory
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Run without -p option
            result = cli_runner.invoke(main, [
                "-c", "constraints.txt",
            ])

            assert result.exit_code == 0

            # Verify pyproject.toml was updated
            doc = read_pyproject(pyproject_file)
            constraints = get_constraint_dependencies(doc)
            assert len(constraints) == 3

        finally:
            os.chdir(original_dir)


# =============================================================================
# Test Custom Constraints
# =============================================================================


class TestCustomConstraints:
    """Tests for custom constraints file merging via CLI."""

    def test_help_includes_custom_constraints_option(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test that help includes --custom-constraints flag documentation."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--custom-constraints" in result.output or "--cc" in result.output
        assert "custom" in result.output.lower()

    def test_cli_with_custom_constraints_basic_merge(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_basic: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test full workflow with both base and custom constraint files.

        Both files have different packages, so result should be union of both.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_basic, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert "Successfully" in result.output

        # Verify pyproject.toml contains union of both constraint sets
        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # From basic_constraints_content: requests, urllib3, certifi
        assert any("requests" in c for c in constraints)
        assert any("urllib3" in c for c in constraints)
        assert any("certifi" in c for c in constraints)

        # From custom_constraints_basic: django, celery, redis
        assert any("django" in c for c in constraints)
        assert any("celery" in c for c in constraints)
        assert any("redis" in c for c in constraints)

    def test_cli_custom_constraints_override(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_override: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that custom constraints override base constraints for same package.

        Base has requests==2.31.0, custom has requests==2.32.0.
        Result should have requests==2.32.0.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file that overrides some packages
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_override, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # requests should be the custom version (2.32.0), not base (2.31.0)
        assert "requests==2.32.0" in constraints
        assert "requests==2.31.0" not in constraints

        # urllib3 should be the custom version (>=2.0.0), not base (>=1.26.0,<2.0.0)
        assert "urllib3>=2.0.0" in constraints
        assert "urllib3>=1.26.0,<2.0.0" not in constraints

        # certifi should be from base (not in custom)
        assert any("certifi" in c for c in constraints)

    def test_cli_custom_constraints_missing_file_error(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test error handling when custom constraints file doesn't exist."""
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        # Reference a non-existent custom constraints file
        nonexistent_custom = tmp_path / "nonexistent-custom.txt"

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(nonexistent_custom),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 1
        assert "Error" in result.stderr or "error" in result.stderr.lower()
        assert "not found" in result.stderr.lower() or "nonexistent" in result.stderr

    def test_cli_custom_constraints_is_directory_error(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test error handling when custom constraints path is a directory."""
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        # Create a directory instead of a file
        custom_dir = tmp_path / "custom-dir"
        custom_dir.mkdir()

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_dir),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 1
        assert "Error" in result.stderr or "error" in result.stderr.lower()

    def test_cli_merge_plus_custom_constraints(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        custom_constraints_basic: str,
    ) -> None:
        """Test combined --merge and --custom-constraints behavior.

        pyproject.toml has existing-package and another-package.
        Base constraints has new packages.
        Custom constraints has additional packages.
        Result should have all packages merged.
        """
        # Create base constraints file
        base_content = "flask==2.3.0\nrequests==2.31.0"
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(base_content, encoding="utf-8")

        # Create custom constraints file
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_basic, encoding="utf-8")

        # Create pyproject.toml with existing constraints using correct key format
        # Note: tool.uv uses 'constraint-dependencies' (hyphen), not 'constraint_dependencies'
        pyproject_content = """\
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
constraint-dependencies = [
    "existing-package==1.0.0",
    "another-package>=2.0.0",
]
"""
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
            "--merge",  # Explicitly merge with existing pyproject.toml constraints
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # From existing pyproject.toml: existing-package, another-package
        assert any("existing-package" in c for c in constraints)
        assert any("another-package" in c for c in constraints)

        # From base constraints: flask, requests
        assert any("flask" in c for c in constraints)
        assert any("requests" in c for c in constraints)

        # From custom constraints: django, celery, redis
        assert any("django" in c for c in constraints)
        assert any("celery" in c for c in constraints)
        assert any("redis" in c for c in constraints)

    def test_cli_custom_constraints_short_option(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_basic: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that --cc short option works for custom constraints."""
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_basic, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--cc", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0
        assert "Successfully" in result.output

        # Verify merge happened
        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)
        assert any("django" in c for c in constraints)

    def test_cli_custom_constraints_empty_file(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_empty: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test handling when custom constraints file is empty.

        Result should only contain base constraints.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create empty custom constraints file
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_empty, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have only base constraints
        assert len(constraints) == 3
        assert any("requests" in c for c in constraints)
        assert any("urllib3" in c for c in constraints)
        assert any("certifi" in c for c in constraints)

    def test_cli_custom_constraints_comments_only(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_comments_only: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test handling when custom constraints file has only comments.

        Result should only contain base constraints.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file with only comments
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_comments_only, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have only base constraints
        assert len(constraints) == 3

    def test_cli_custom_constraints_case_insensitive_override(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_case_mismatch: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test case-insensitive package name matching during merge.

        Base has 'requests', custom has 'Requests'. Custom should override.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file with different case
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_case_mismatch, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have the custom version (2.32.0), not base (2.31.0)
        # Package name case is preserved from custom
        assert any("Requests==2.32.0" in c for c in constraints) or \
               any("requests==2.32.0" in c.lower() for c in constraints)
        assert not any("requests==2.31.0" in c.lower() for c in constraints)

        # Django from custom
        assert any("django" in c.lower() for c in constraints)

    def test_cli_custom_constraints_mixed_merge(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_mixed: str,
        minimal_pyproject_content: str,
        expected_mixed_merge: list[str],
    ) -> None:
        """Test mixed merge with both override and new packages.

        - requests: overrides base version
        - django, celery: new packages unique to custom
        - urllib3, certifi: from base (not in custom)
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_mixed, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Verify expected result
        assert constraints == expected_mixed_merge

    def test_cli_custom_constraints_with_extras(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        custom_constraints_with_extras: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test custom constraints with package extras override base packages.

        Base has 'requests==2.31.0', custom has 'requests[security]==2.32.0'.
        Custom should override, treating them as same package by name.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create custom constraints file with extras
        custom_file = tmp_path / "custom-constraints.txt"
        custom_file.write_text(custom_constraints_with_extras, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "--custom-constraints", str(custom_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Custom version with extras should be present
        assert "requests[security]==2.32.0" in constraints
        # Base version should not be present
        assert "requests==2.31.0" not in constraints
        # Celery with extras from custom
        assert any("celery[redis,auth]" in c for c in constraints)

    def test_cli_no_custom_constraints_uses_base_only(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        basic_constraints_content: str,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that not providing --custom-constraints uses only base constraints.

        This ensures backward compatibility.
        """
        # Create base constraints file
        constraints_file = tmp_path / "constraints.txt"
        constraints_file.write_text(basic_constraints_content, encoding="utf-8")

        # Create pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text(minimal_pyproject_content, encoding="utf-8")

        result = cli_runner.invoke(main, [
            "-c", str(constraints_file),
            "-p", str(pyproject_file),
        ])

        assert result.exit_code == 0

        doc = read_pyproject(pyproject_file)
        constraints = get_constraint_dependencies(doc)

        # Should have exactly the base constraints
        assert len(constraints) == 3
        assert "requests==2.31.0" in constraints
        assert "urllib3>=1.26.0,<2.0.0" in constraints
        assert "certifi>=2023.7.22" in constraints
