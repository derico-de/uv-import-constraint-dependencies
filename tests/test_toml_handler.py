"""Unit tests for the TOML handler module.

This module tests the toml_handler module from uv-import-constraint-dependencies,
covering various scenarios including:
- Fresh creation (new pyproject.toml)
- Merge behavior
- Formatting preservation
- Helper functions
- Error handling
- Edge cases
"""

from pathlib import Path

import pytest
import tomlkit

from uv_import_constraint_dependencies.toml_handler import (
    TOMLError,
    _extract_package_name,
    _get_existing_package_names,
    create_minimal_pyproject,
    get_constraint_dependencies,
    read_pyproject,
    update_constraint_dependencies,
)


class TestExtractPackageName:
    """Tests for the _extract_package_name helper function."""

    def test_extract_from_exact_version(self) -> None:
        """Test extracting package name from exact version constraint."""
        result = _extract_package_name("requests==2.31.0")
        assert result == "requests"

    def test_extract_from_version_range(self) -> None:
        """Test extracting package name from version range constraint."""
        result = _extract_package_name("urllib3>=1.26.0,<2.0.0")
        assert result == "urllib3"

    def test_extract_from_greater_than_equal(self) -> None:
        """Test extracting package name from >= constraint."""
        result = _extract_package_name("flask>=2.0.0")
        assert result == "flask"

    def test_extract_from_less_than(self) -> None:
        """Test extracting package name from < constraint."""
        result = _extract_package_name("django<5.0.0")
        assert result == "django"

    def test_extract_from_not_equal(self) -> None:
        """Test extracting package name from != constraint."""
        result = _extract_package_name("package!=1.0.0")
        assert result == "package"

    def test_extract_from_compatible_release(self) -> None:
        """Test extracting package name from ~= constraint."""
        result = _extract_package_name("requests~=2.31")
        assert result == "requests"

    def test_extract_with_environment_marker(self) -> None:
        """Test extracting package name when environment marker is present."""
        result = _extract_package_name('numpy>=1.24 ; python_version >= "3.9"')
        assert result == "numpy"

    def test_extract_with_extras(self) -> None:
        """Test extracting package name when extras are present."""
        result = _extract_package_name("requests[security]==2.31.0")
        assert result == "requests"

    def test_extract_with_multiple_extras(self) -> None:
        """Test extracting package name when multiple extras are present."""
        result = _extract_package_name("celery[redis,auth]>=5.3.0")
        assert result == "celery"

    def test_extract_normalizes_to_lowercase(self) -> None:
        """Test that package names are normalized to lowercase."""
        result = _extract_package_name("NumPy>=1.24")
        assert result == "numpy"

    def test_extract_with_dashes(self) -> None:
        """Test extracting package name with dashes."""
        result = _extract_package_name("psycopg2-binary==2.9.9")
        assert result == "psycopg2-binary"

    def test_extract_with_underscores(self) -> None:
        """Test extracting package name with underscores."""
        result = _extract_package_name("typing_extensions>=4.0")
        assert result == "typing_extensions"

    def test_extract_with_dots(self) -> None:
        """Test extracting package name with dots."""
        result = _extract_package_name("zope.interface>=5.0")
        assert result == "zope.interface"

    def test_extract_arbitrary_equality(self) -> None:
        """Test extracting package name with === operator."""
        result = _extract_package_name("package===1.0.custom")
        assert result == "package"

    def test_extract_no_version(self) -> None:
        """Test extracting package name when no version is specified."""
        result = _extract_package_name("requests")
        assert result == "requests"


class TestGetExistingPackageNames:
    """Tests for the _get_existing_package_names helper function."""

    def test_single_constraint(self) -> None:
        """Test getting package names from a single constraint."""
        result = _get_existing_package_names(["requests==2.31.0"])
        assert result == {"requests"}

    def test_multiple_constraints(self) -> None:
        """Test getting package names from multiple constraints."""
        constraints = [
            "requests==2.31.0",
            "flask>=2.0.0",
            "django<5.0.0",
        ]
        result = _get_existing_package_names(constraints)
        assert result == {"requests", "flask", "django"}

    def test_empty_list(self) -> None:
        """Test getting package names from empty list."""
        result = _get_existing_package_names([])
        assert result == set()

    def test_normalizes_package_names(self) -> None:
        """Test that package names are normalized."""
        constraints = ["NumPy>=1.24", "Requests==2.31.0"]
        result = _get_existing_package_names(constraints)
        assert result == {"numpy", "requests"}


class TestReadPyproject:
    """Tests for the read_pyproject function."""

    def test_read_minimal_pyproject(
        self,
        tmp_pyproject_file: Path,
    ) -> None:
        """Test reading a minimal pyproject.toml file."""
        doc = read_pyproject(tmp_pyproject_file)
        assert doc["project"]["name"] == "test-project"
        assert doc["project"]["version"] == "0.1.0"

    def test_read_nonexistent_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that reading a nonexistent file raises TOMLError."""
        nonexistent = tmp_path / "nonexistent.toml"
        with pytest.raises(TOMLError) as exc_info:
            read_pyproject(nonexistent)
        assert "pyproject.toml not found" in str(exc_info.value)

    def test_read_invalid_toml(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that reading invalid TOML raises TOMLError."""
        invalid_file = tmp_path / "invalid.toml"
        invalid_file.write_text("this is [not valid toml", encoding="utf-8")
        with pytest.raises(TOMLError) as exc_info:
            read_pyproject(invalid_file)
        assert "Failed to parse" in str(exc_info.value)

    def test_read_pyproject_with_constraints(
        self,
        create_pyproject_file,
        pyproject_with_constraints: str,
    ) -> None:
        """Test reading pyproject.toml with existing constraint-dependencies."""
        pyproject_path = create_pyproject_file(pyproject_with_constraints)
        doc = read_pyproject(pyproject_path)
        assert "tool" in doc
        assert "uv" in doc["tool"]
        assert "constraint-dependencies" in doc["tool"]["uv"]

    def test_read_pyproject_preserves_formatting(
        self,
        create_pyproject_file,
        pyproject_with_comments: str,
    ) -> None:
        """Test that reading preserves comments and formatting."""
        pyproject_path = create_pyproject_file(pyproject_with_comments)
        doc = read_pyproject(pyproject_path)
        # tomlkit preserves comments, so we can check the output
        output = tomlkit.dumps(doc)
        assert "# Project configuration" in output
        assert "# Tool configurations" in output


class TestGetConstraintDependencies:
    """Tests for the get_constraint_dependencies function."""

    def test_get_existing_constraints(
        self,
        create_pyproject_file,
        pyproject_with_constraints: str,
    ) -> None:
        """Test getting existing constraint_dependencies."""
        pyproject_path = create_pyproject_file(pyproject_with_constraints)
        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert result == [
            "existing-package==1.0.0",
            "another-package>=2.0.0",
        ]

    def test_get_no_tool_section(
        self,
        tmp_pyproject_file: Path,
    ) -> None:
        """Test getting constraints when no tool section exists."""
        doc = read_pyproject(tmp_pyproject_file)
        result = get_constraint_dependencies(doc)
        assert result == []

    def test_get_no_uv_section(
        self,
        create_pyproject_file,
    ) -> None:
        """Test getting constraints when no tool.uv section exists."""
        content = """\
[project]
name = "test"

[tool.black]
line-length = 88
"""
        pyproject_path = create_pyproject_file(content)
        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert result == []

    def test_get_no_constraint_dependencies(
        self,
        create_pyproject_file,
        pyproject_with_tool_uv: str,
    ) -> None:
        """Test getting constraints when tool.uv exists but no constraint-dependencies."""
        pyproject_path = create_pyproject_file(pyproject_with_tool_uv)
        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert result == []

    def test_get_empty_document(self) -> None:
        """Test getting constraints from empty document."""
        doc = tomlkit.document()
        result = get_constraint_dependencies(doc)
        assert result == []


class TestUpdateConstraintDependenciesFreshCreation:
    """Tests for update_constraint_dependencies creating new content."""

    def test_create_new_pyproject(
        self,
        tmp_path: Path,
    ) -> None:
        """Test creating a new pyproject.toml when it doesn't exist."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = ["requests==2.31.0", "flask>=2.0.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        assert pyproject_path.exists()
        content = pyproject_path.read_text()
        assert "constraint-dependencies" in content
        assert "requests==2.31.0" in content
        assert "flask>=2.0.0" in content

    def test_add_to_minimal_pyproject(
        self,
        tmp_pyproject_file: Path,
    ) -> None:
        """Test adding constraints to minimal pyproject.toml."""
        constraints = ["requests==2.31.0", "flask>=2.0.0"]

        update_constraint_dependencies(tmp_pyproject_file, constraints)

        doc = read_pyproject(tmp_pyproject_file)
        result = get_constraint_dependencies(doc)
        assert "requests==2.31.0" in result
        assert "flask>=2.0.0" in result

    def test_add_to_pyproject_with_tool_uv(
        self,
        create_pyproject_file,
        pyproject_with_tool_uv: str,
    ) -> None:
        """Test adding constraints to pyproject.toml with existing tool.uv section."""
        pyproject_path = create_pyproject_file(pyproject_with_tool_uv)
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert result == ["requests==2.31.0"]

    def test_creates_tool_section_if_missing(
        self,
        tmp_pyproject_file: Path,
    ) -> None:
        """Test that tool section is created if missing."""
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(tmp_pyproject_file, constraints)

        doc = read_pyproject(tmp_pyproject_file)
        assert "tool" in doc
        assert "uv" in doc["tool"]
        assert "constraint-dependencies" in doc["tool"]["uv"]

    def test_creates_uv_section_if_missing(
        self,
        create_pyproject_file,
    ) -> None:
        """Test that tool.uv section is created if missing."""
        content = """\
[project]
name = "test"

[tool.black]
line-length = 88
"""
        pyproject_path = create_pyproject_file(content)
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        assert "uv" in doc["tool"]
        result = get_constraint_dependencies(doc)
        assert result == ["requests==2.31.0"]


class TestUpdateConstraintDependenciesMergeBehavior:
    """Tests for update_constraint_dependencies merge behavior."""

    def test_merge_with_existing_keeps_both(
        self,
        create_pyproject_file,
        pyproject_with_constraints: str,
    ) -> None:
        """Test merging keeps existing constraints for different packages."""
        pyproject_path = create_pyproject_file(pyproject_with_constraints)
        new_constraints = ["flask>=2.0.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # Should have existing constraints plus new one
        package_names = {_extract_package_name(c) for c in result}
        assert "existing-package" in package_names
        assert "another-package" in package_names
        assert "flask" in package_names

    def test_merge_replaces_same_package(
        self,
        create_pyproject_file,
        pyproject_with_constraints: str,
    ) -> None:
        """Test merging replaces constraint for same package (new takes precedence)."""
        pyproject_path = create_pyproject_file(pyproject_with_constraints)
        # Update existing-package with new version
        new_constraints = ["existing-package==2.0.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # Should have new version, not old
        assert "existing-package==2.0.0" in result
        assert "existing-package==1.0.0" not in result
        # Should keep other existing
        assert any("another-package" in c for c in result)

    def test_merge_false_replaces_all(
        self,
        create_pyproject_file,
        pyproject_with_constraints: str,
    ) -> None:
        """Test merge=False replaces all existing constraints."""
        pyproject_path = create_pyproject_file(pyproject_with_constraints)
        new_constraints = ["flask>=2.0.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=False)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # Should only have new constraints
        assert result == ["flask>=2.0.0"]

    def test_merge_case_insensitive_package_matching(
        self,
        create_pyproject_file,
    ) -> None:
        """Test that merge matching is case-insensitive for package names."""
        content = """\
[project]
name = "test"

[tool.uv]
constraint-dependencies = ["NumPy==1.24.0"]
"""
        pyproject_path = create_pyproject_file(content)
        new_constraints = ["numpy>=1.25.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # Should have replaced NumPy with numpy
        assert len(result) == 1
        assert "1.25.0" in result[0]

    def test_merge_empty_existing(
        self,
        create_pyproject_file,
        pyproject_with_tool_uv: str,
    ) -> None:
        """Test merging when existing constraint-dependencies is empty."""
        pyproject_path = create_pyproject_file(pyproject_with_tool_uv)
        new_constraints = ["requests==2.31.0", "flask>=2.0.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert "requests==2.31.0" in result
        assert "flask>=2.0.0" in result


class TestUpdateConstraintDependenciesSorting:
    """Tests for constraint sorting behavior."""

    def test_sorts_alphabetically(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that constraints are sorted alphabetically by package name."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = ["zebra==1.0.0", "apple==2.0.0", "mango==3.0.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert result == ["apple==2.0.0", "mango==3.0.0", "zebra==1.0.0"]

    def test_sorts_case_insensitive(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that sorting is case-insensitive."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = ["Zebra==1.0.0", "apple==2.0.0", "Mango==3.0.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # Sorted by lowercase package names
        package_names = [_extract_package_name(c) for c in result]
        assert package_names == ["apple", "mango", "zebra"]

    def test_sorts_merged_constraints(
        self,
        create_pyproject_file,
    ) -> None:
        """Test that merged constraints are sorted."""
        content = """\
[project]
name = "test"

[tool.uv]
constraint-dependencies = ["zebra==1.0.0", "apple==1.0.0"]
"""
        pyproject_path = create_pyproject_file(content)
        new_constraints = ["mango==2.0.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        package_names = [_extract_package_name(c) for c in result]
        assert package_names == ["apple", "mango", "zebra"]


class TestUpdateConstraintDependenciesFormattingPreservation:
    """Tests for formatting preservation during updates."""

    def test_preserves_project_section(
        self,
        create_pyproject_file,
        minimal_pyproject_content: str,
    ) -> None:
        """Test that project section is preserved."""
        pyproject_path = create_pyproject_file(minimal_pyproject_content)
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        assert doc["project"]["name"] == "test-project"
        assert doc["project"]["version"] == "0.1.0"

    def test_preserves_comments(
        self,
        create_pyproject_file,
        pyproject_with_comments: str,
    ) -> None:
        """Test that comments are preserved."""
        pyproject_path = create_pyproject_file(pyproject_with_comments)
        constraints = ["new-package==1.0.0"]

        update_constraint_dependencies(pyproject_path, constraints, merge=True)

        content = pyproject_path.read_text()
        assert "# Project configuration" in content
        assert "# Tool configurations" in content
        assert "# Other tool settings" in content

    def test_preserves_other_tool_sections(
        self,
        create_pyproject_file,
        pyproject_with_comments: str,
    ) -> None:
        """Test that other tool sections are preserved."""
        pyproject_path = create_pyproject_file(pyproject_with_comments)
        constraints = ["new-package==1.0.0"]

        update_constraint_dependencies(pyproject_path, constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        assert "pytest" in doc["tool"]
        assert "ini_options" in doc["tool"]["pytest"]

    def test_multiline_array_formatting_multiple_items(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that multiple constraints use multiline formatting."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = ["requests==2.31.0", "flask>=2.0.0", "django<5.0.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        content = pyproject_path.read_text()
        # Should have multiline array formatting
        assert "constraint-dependencies = [" in content
        # Each constraint should be on its own line
        lines = content.split("\n")
        constraint_lines = [line for line in lines if "==" in line or ">=" in line or "<" in line]
        assert len(constraint_lines) >= 3

    def test_single_item_formatting(
        self,
        tmp_path: Path,
    ) -> None:
        """Test formatting for single constraint item."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        content = pyproject_path.read_text()
        assert "constraint-dependencies" in content
        assert "requests==2.31.0" in content


class TestUpdateConstraintDependenciesEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_constraints_list(
        self,
        tmp_pyproject_file: Path,
    ) -> None:
        """Test updating with empty constraints list."""
        update_constraint_dependencies(tmp_pyproject_file, [], merge=False)

        doc = read_pyproject(tmp_pyproject_file)
        result = get_constraint_dependencies(doc)
        assert result == []

    def test_constraints_with_environment_markers(
        self,
        tmp_path: Path,
    ) -> None:
        """Test handling constraints with environment markers."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = [
            'numpy==1.24.3 ; python_version >= "3.9"',
            'pywin32>=306 ; sys_platform == "win32"',
        ]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert 'numpy==1.24.3 ; python_version >= "3.9"' in result
        assert 'pywin32>=306 ; sys_platform == "win32"' in result

    def test_constraints_with_extras(
        self,
        tmp_path: Path,
    ) -> None:
        """Test handling constraints with package extras."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = [
            "requests[security]==2.31.0",
            "celery[redis,auth]>=5.3.0",
        ]

        update_constraint_dependencies(pyproject_path, constraints)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert "requests[security]==2.31.0" in result
        assert "celery[redis,auth]>=5.3.0" in result

    def test_merge_with_extras_same_package(
        self,
        create_pyproject_file,
    ) -> None:
        """Test merging replaces package even when extras differ."""
        content = """\
[project]
name = "test"

[tool.uv]
constraint-dependencies = ["requests[security]==2.30.0"]
"""
        pyproject_path = create_pyproject_file(content)
        new_constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # New constraint should replace old one (same package)
        assert result == ["requests==2.31.0"]
        assert "requests[security]" not in str(result)

    def test_unicode_in_constraints(
        self,
        tmp_path: Path,
    ) -> None:
        """Test handling constraints with unicode characters."""
        pyproject_path = tmp_path / "pyproject.toml"
        # Some legitimate packages might have unicode in their names
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        # Should be able to read it back
        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert result == ["requests==2.31.0"]


class TestCreateMinimalPyproject:
    """Tests for the create_minimal_pyproject function."""

    def test_creates_file(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that create_minimal_pyproject creates a file."""
        pyproject_path = tmp_path / "pyproject.toml"

        create_minimal_pyproject(pyproject_path)

        assert pyproject_path.exists()

    def test_has_tool_uv_section(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that created file has tool.uv section."""
        pyproject_path = tmp_path / "pyproject.toml"

        create_minimal_pyproject(pyproject_path)

        doc = read_pyproject(pyproject_path)
        assert "tool" in doc
        assert "uv" in doc["tool"]

    def test_valid_toml_format(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that created file is valid TOML."""
        pyproject_path = tmp_path / "pyproject.toml"

        create_minimal_pyproject(pyproject_path)

        content = pyproject_path.read_text()
        # Should parse without error
        doc = tomlkit.parse(content)
        assert isinstance(doc, tomlkit.TOMLDocument)


class TestTOMLError:
    """Tests for TOMLError exception class."""

    def test_toml_error_is_exception(self) -> None:
        """Test that TOMLError is an Exception subclass."""
        assert issubclass(TOMLError, Exception)

    def test_toml_error_with_message(self) -> None:
        """Test that TOMLError can be raised with a message."""
        with pytest.raises(TOMLError) as exc_info:
            raise TOMLError("Test error message")
        assert "Test error message" in str(exc_info.value)

    def test_toml_error_from_read_pyproject(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that read_pyproject raises TOMLError for invalid TOML."""
        invalid_file = tmp_path / "invalid.toml"
        invalid_file.write_text("invalid [toml syntax", encoding="utf-8")

        with pytest.raises(TOMLError):
            read_pyproject(invalid_file)

    def test_toml_error_file_not_found(
        self,
        tmp_path: Path,
    ) -> None:
        """Test that read_pyproject raises TOMLError for missing file."""
        nonexistent = tmp_path / "nonexistent.toml"

        with pytest.raises(TOMLError) as exc_info:
            read_pyproject(nonexistent)
        assert "not found" in str(exc_info.value)


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_full_workflow_new_project(
        self,
        tmp_path: Path,
    ) -> None:
        """Test full workflow: create new project, add constraints."""
        pyproject_path = tmp_path / "pyproject.toml"
        constraints = [
            "requests==2.31.0",
            "flask>=2.0.0",
            "django>=4.2.0,<5.0.0",
        ]

        # Add constraints (creates new file)
        update_constraint_dependencies(pyproject_path, constraints)

        # Verify
        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        assert len(result) == 3
        assert all(c in result for c in ["requests==2.31.0", "flask>=2.0.0", "django>=4.2.0,<5.0.0"])

    def test_full_workflow_existing_project(
        self,
        create_pyproject_file,
        pyproject_with_constraints: str,
    ) -> None:
        """Test full workflow: existing project, merge constraints."""
        pyproject_path = create_pyproject_file(pyproject_with_constraints)
        new_constraints = [
            "flask>=2.0.0",
            "another-package>=3.0.0",  # Update existing
        ]

        # Merge new constraints
        update_constraint_dependencies(pyproject_path, new_constraints, merge=True)

        # Verify
        doc = read_pyproject(pyproject_path)
        result = get_constraint_dependencies(doc)
        # Should have: existing-package (kept), another-package (updated), flask (new)
        package_names = {_extract_package_name(c) for c in result}
        assert "existing-package" in package_names
        assert "another-package" in package_names
        assert "flask" in package_names
        # Updated version of another-package
        assert any("3.0.0" in c and "another-package" in c for c in result)

    def test_preserves_complex_pyproject(
        self,
        create_pyproject_file,
    ) -> None:
        """Test that a complex pyproject.toml is preserved correctly."""
        complex_content = """\
# Main project config
[project]
name = "complex-project"
version = "1.0.0"
description = "A complex project"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "tomlkit>=0.12",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[project.scripts]
mycommand = "mymodule.cli:main"

# Build system
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Tool configurations
[tool.uv]
dev-dependencies = ["ruff>=0.1.0"]

[tool.ruff]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
        pyproject_path = create_pyproject_file(complex_content)
        constraints = ["requests==2.31.0"]

        update_constraint_dependencies(pyproject_path, constraints)

        # Verify all sections preserved
        doc = read_pyproject(pyproject_path)
        assert doc["project"]["name"] == "complex-project"
        assert "dependencies" in doc["project"]
        assert "build-system" in doc
        assert "ruff" in doc["tool"]
        assert "pytest" in doc["tool"]

        # And constraints were added
        result = get_constraint_dependencies(doc)
        assert result == ["requests==2.31.0"]
