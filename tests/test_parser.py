"""Unit tests for the constraints parser module.

This module tests the parse_constraints function from the parser module,
covering various scenarios including:
- Basic constraints with version specifiers
- Version ranges and complex version constraints
- Comments (line and inline)
- Blank lines
- Include directives (-r, -c)
- Environment markers
- Package extras
- Edge cases
"""

import pytest

from uv_import_constraint_dependencies.parser import (
    extract_package_name,
    merge_constraints,
    parse_constraints,
)


class TestParseBasicConstraints:
    """Tests for parsing basic constraint specifications."""

    def test_parse_exact_version(self) -> None:
        """Test parsing a single exact version constraint."""
        content = "requests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_parse_multiple_exact_versions(self) -> None:
        """Test parsing multiple exact version constraints."""
        content = "requests==2.31.0\nflask==2.3.3\ndjango==4.2.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0", "flask==2.3.3", "django==4.2.0"]

    def test_parse_basic_content_fixture(
        self,
        basic_constraints_content: str,
        expected_basic_constraints: list[str],
    ) -> None:
        """Test parsing basic constraints using fixture."""
        result = parse_constraints(basic_constraints_content)
        assert result == expected_basic_constraints


class TestParseVersionRanges:
    """Tests for parsing version range constraints."""

    def test_parse_greater_than_equal(self) -> None:
        """Test parsing >= version constraint."""
        content = "requests>=2.0.0"
        result = parse_constraints(content)
        assert result == ["requests>=2.0.0"]

    def test_parse_less_than(self) -> None:
        """Test parsing < version constraint."""
        content = "requests<3.0.0"
        result = parse_constraints(content)
        assert result == ["requests<3.0.0"]

    def test_parse_version_range(self) -> None:
        """Test parsing combined >= and < version constraint."""
        content = "urllib3>=1.26.0,<2.0.0"
        result = parse_constraints(content)
        assert result == ["urllib3>=1.26.0,<2.0.0"]

    def test_parse_not_equal(self) -> None:
        """Test parsing != version constraint."""
        content = "requests!=2.30.0"
        result = parse_constraints(content)
        assert result == ["requests!=2.30.0"]

    def test_parse_compatible_release(self) -> None:
        """Test parsing ~= compatible release constraint."""
        content = "requests~=2.31"
        result = parse_constraints(content)
        assert result == ["requests~=2.31"]

    def test_parse_multiple_version_specifiers(self) -> None:
        """Test parsing multiple comma-separated version specifiers."""
        content = "requests>=2.0.0,<3.0.0,!=2.30.0"
        result = parse_constraints(content)
        assert result == ["requests>=2.0.0,<3.0.0,!=2.30.0"]


class TestParseComments:
    """Tests for handling comment lines."""

    def test_skip_comment_line(self) -> None:
        """Test that comment lines starting with # are skipped."""
        content = "# This is a comment\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_multiple_comment_lines(self) -> None:
        """Test that multiple comment lines are skipped."""
        content = """# Comment 1
# Comment 2
requests==2.31.0
# Comment 3
flask==2.3.3"""
        result = parse_constraints(content)
        assert result == ["requests==2.31.0", "flask==2.3.3"]

    def test_comment_only_content(
        self,
        comment_only_constraints: str,
    ) -> None:
        """Test that content with only comments returns empty list."""
        result = parse_constraints(comment_only_constraints)
        assert result == []

    def test_comment_with_leading_spaces(self) -> None:
        """Test that indented comment lines are still skipped."""
        content = "   # Indented comment\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_constraints_with_comments_fixture(
        self,
        constraints_with_comments: str,
    ) -> None:
        """Test parsing constraints with comments using fixture."""
        result = parse_constraints(constraints_with_comments)
        assert result == [
            "requests==2.31.0",
            "urllib3>=1.26.0,<2.0.0",
            "certifi>=2023.7.22",
            "flask==2.3.3",
        ]


class TestParseBlankLines:
    """Tests for handling blank lines."""

    def test_skip_blank_lines(self) -> None:
        """Test that empty lines are skipped."""
        content = "requests==2.31.0\n\nflask==2.3.3"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0", "flask==2.3.3"]

    def test_skip_whitespace_only_lines(self) -> None:
        """Test that lines with only whitespace are skipped."""
        content = "requests==2.31.0\n   \n\t\nflask==2.3.3"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0", "flask==2.3.3"]

    def test_leading_blank_lines(self) -> None:
        """Test that leading blank lines are handled."""
        content = "\n\n\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_trailing_blank_lines(self) -> None:
        """Test that trailing blank lines are handled."""
        content = "requests==2.31.0\n\n\n"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]


class TestParseIncludeDirectives:
    """Tests for handling include directives (-r, -c, etc.)."""

    def test_skip_requirement_directive(self) -> None:
        """Test that -r directive is skipped."""
        content = "-r requirements.txt\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_constraint_directive(self) -> None:
        """Test that -c directive is skipped."""
        content = "-c base-constraints.txt\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_long_form_requirement(self) -> None:
        """Test that --requirement directive is skipped."""
        content = "--requirement dev.txt\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_long_form_constraint(self) -> None:
        """Test that --constraint directive is skipped."""
        content = "--constraint other.txt\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_index_url_directive(self) -> None:
        """Test that -i/--index-url directive is skipped."""
        content = "-i https://pypi.example.com/simple/\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_extra_index_url_directive(self) -> None:
        """Test that --extra-index-url directive is skipped."""
        content = "--extra-index-url https://other.pypi.com/\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_editable_directive(self) -> None:
        """Test that -e/--editable directive is skipped."""
        content = "-e git+https://github.com/user/repo.git\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_skip_find_links_directive(self) -> None:
        """Test that -f/--find-links directive is skipped."""
        content = "-f https://download.pytorch.org/whl/torch_stable.html\nrequests==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_directives_fixture(
        self,
        constraints_with_directives: str,
    ) -> None:
        """Test parsing constraints with directives using fixture."""
        result = parse_constraints(constraints_with_directives)
        assert result == ["requests==2.31.0", "flask>=2.0.0"]


class TestParseEnvironmentMarkers:
    """Tests for handling environment markers."""

    def test_parse_python_version_marker(self) -> None:
        """Test parsing constraint with python_version marker."""
        content = 'numpy==1.24.3 ; python_version >= "3.9"'
        result = parse_constraints(content)
        assert result == ['numpy==1.24.3 ; python_version >= "3.9"']

    def test_parse_sys_platform_marker(self) -> None:
        """Test parsing constraint with sys_platform marker."""
        content = 'pywin32>=306 ; sys_platform == "win32"'
        result = parse_constraints(content)
        assert result == ['pywin32>=306 ; sys_platform == "win32"']

    def test_parse_platform_system_marker(self) -> None:
        """Test parsing constraint with platform_system marker."""
        content = 'pyobjc>=9.0 ; platform_system == "Darwin"'
        result = parse_constraints(content)
        assert result == ['pyobjc>=9.0 ; platform_system == "Darwin"']

    def test_parse_complex_marker(self) -> None:
        """Test parsing constraint with complex environment marker."""
        content = 'numpy>=1.20 ; python_version >= "3.8" and sys_platform != "win32"'
        result = parse_constraints(content)
        assert result == ['numpy>=1.20 ; python_version >= "3.8" and sys_platform != "win32"']

    def test_parse_marker_with_single_quotes(self) -> None:
        """Test parsing constraint with single-quoted marker values."""
        content = "numpy==1.24.3 ; python_version >= '3.9'"
        result = parse_constraints(content)
        assert result == ["numpy==1.24.3 ; python_version >= '3.9'"]

    def test_markers_fixture(
        self,
        constraints_with_markers: str,
    ) -> None:
        """Test parsing constraints with markers using fixture."""
        result = parse_constraints(constraints_with_markers)
        assert result == [
            'numpy==1.24.3 ; python_version >= "3.9"',
            'pandas>=2.0.0 ; sys_platform == "linux"',
            'pywin32>=306 ; sys_platform == "win32"',
        ]


class TestParseInlineComments:
    """Tests for handling inline comments."""

    def test_strip_inline_comment(self) -> None:
        """Test that inline comments are stripped from constraints."""
        content = "requests==2.31.0  # Main HTTP library"
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_strip_inline_comment_single_space(self) -> None:
        """Test that inline comment with single space before # is stripped."""
        content = "certifi>=2023.7.22 # SSL certificates"
        result = parse_constraints(content)
        assert result == ["certifi>=2023.7.22"]

    def test_inline_comments_fixture(
        self,
        constraints_with_inline_comments: str,
    ) -> None:
        """Test parsing constraints with inline comments using fixture."""
        result = parse_constraints(constraints_with_inline_comments)
        assert result == [
            "requests==2.31.0",
            "urllib3>=1.26.0,<2.0.0",
            "certifi>=2023.7.22",
        ]

    def test_preserve_hash_in_url(self) -> None:
        """Test that hash without preceding space is preserved (e.g., in URLs)."""
        # In real pip, this would be a hash for security, but we handle it correctly
        content = "package @ https://example.com/package.tar.gz#sha256=abc123"
        result = parse_constraints(content)
        assert result == ["package @ https://example.com/package.tar.gz#sha256=abc123"]


class TestParsePackageExtras:
    """Tests for handling package extras."""

    def test_parse_single_extra(self) -> None:
        """Test parsing constraint with single extra."""
        content = "requests[security]==2.31.0"
        result = parse_constraints(content)
        assert result == ["requests[security]==2.31.0"]

    def test_parse_multiple_extras(self) -> None:
        """Test parsing constraint with multiple extras."""
        content = "celery[redis,auth]>=5.3.0"
        result = parse_constraints(content)
        assert result == ["celery[redis,auth]>=5.3.0"]

    def test_extras_fixture(
        self,
        constraints_with_extras: str,
    ) -> None:
        """Test parsing constraints with extras using fixture."""
        result = parse_constraints(constraints_with_extras)
        assert result == [
            "requests[security]==2.31.0",
            "celery[redis,auth]>=5.3.0",
            "uvicorn[standard]>=0.23.0",
        ]


class TestParseEmptyContent:
    """Tests for handling empty or minimal content."""

    def test_empty_string(self) -> None:
        """Test that empty string returns empty list."""
        result = parse_constraints("")
        assert result == []

    def test_empty_fixture(
        self,
        empty_constraints_content: str,
    ) -> None:
        """Test that empty content fixture returns empty list."""
        result = parse_constraints(empty_constraints_content)
        assert result == []

    def test_newlines_only(self) -> None:
        """Test that content with only newlines returns empty list."""
        result = parse_constraints("\n\n\n")
        assert result == []

    def test_whitespace_only(self) -> None:
        """Test that content with only whitespace returns empty list."""
        result = parse_constraints("   \n\t\n   ")
        assert result == []


class TestParseComplexContent:
    """Tests for parsing complex, real-world content."""

    def test_complex_fixture(
        self,
        complex_constraints_content: str,
    ) -> None:
        """Test parsing complex constraints content using fixture."""
        result = parse_constraints(complex_constraints_content)
        # Note: parse_constraints does NOT sort - it maintains order
        expected = [
            "requests==2.31.0",
            "urllib3>=1.26.0,<2.0.0",
            "certifi>=2023.7.22",
            'numpy==1.24.3 ; python_version >= "3.9"',
            'pandas>=2.0.0,<3.0.0 ; python_version >= "3.10"',
            "psycopg2-binary==2.9.9",
            "flask[async]==2.3.3",
            "django>=4.2.0,<5.0.0",
        ]
        assert result == expected

    def test_mixed_content(self) -> None:
        """Test parsing content mixing all features."""
        content = """\
# Header comment
-r base.txt

requests==2.31.0  # HTTP client
urllib3>=1.26.0,<2.0.0

# Platform specific
pywin32>=306 ; sys_platform == "win32"

-c production.txt

flask[async]==2.3.3

"""
        result = parse_constraints(content)
        expected = [
            "requests==2.31.0",
            "urllib3>=1.26.0,<2.0.0",
            'pywin32>=306 ; sys_platform == "win32"',
            "flask[async]==2.3.3",
        ]
        assert result == expected


class TestParseEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_preserve_whitespace_in_marker(self) -> None:
        """Test that whitespace within marker expression is preserved."""
        content = 'package>=1.0 ; python_version >= "3.8"'
        result = parse_constraints(content)
        # Whitespace around semicolon should be preserved as-is
        assert result == ['package>=1.0 ; python_version >= "3.8"']

    def test_strip_leading_trailing_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped from lines."""
        content = "   requests==2.31.0   "
        result = parse_constraints(content)
        assert result == ["requests==2.31.0"]

    def test_package_name_with_dash(self) -> None:
        """Test parsing package names with dashes."""
        content = "psycopg2-binary==2.9.9"
        result = parse_constraints(content)
        assert result == ["psycopg2-binary==2.9.9"]

    def test_package_name_with_underscore(self) -> None:
        """Test parsing package names with underscores."""
        content = "typing_extensions>=4.0"
        result = parse_constraints(content)
        assert result == ["typing_extensions>=4.0"]

    def test_package_name_with_dots(self) -> None:
        """Test parsing package names with dots."""
        content = "zope.interface>=5.0"
        result = parse_constraints(content)
        assert result == ["zope.interface>=5.0"]

    def test_pre_release_version(self) -> None:
        """Test parsing pre-release version specifier."""
        content = "package==1.0.0a1"
        result = parse_constraints(content)
        assert result == ["package==1.0.0a1"]

    def test_post_release_version(self) -> None:
        """Test parsing post-release version specifier."""
        content = "package==1.0.0.post1"
        result = parse_constraints(content)
        assert result == ["package==1.0.0.post1"]

    def test_dev_release_version(self) -> None:
        """Test parsing dev release version specifier."""
        content = "package==1.0.0.dev1"
        result = parse_constraints(content)
        assert result == ["package==1.0.0.dev1"]

    def test_local_version(self) -> None:
        """Test parsing local version identifier."""
        content = "package==1.0.0+local.version"
        result = parse_constraints(content)
        assert result == ["package==1.0.0+local.version"]

    def test_epoch_version(self) -> None:
        """Test parsing version with epoch."""
        content = "package==1!2.0.0"
        result = parse_constraints(content)
        assert result == ["package==1!2.0.0"]

    def test_url_constraint(self) -> None:
        """Test parsing URL-based constraint (PEP 440 direct references)."""
        content = "package @ https://example.com/package-1.0.0.tar.gz"
        result = parse_constraints(content)
        assert result == ["package @ https://example.com/package-1.0.0.tar.gz"]

    def test_wildcard_version(self) -> None:
        """Test parsing wildcard version specifier."""
        content = "package==1.0.*"
        result = parse_constraints(content)
        assert result == ["package==1.0.*"]

    def test_arbitrary_equality(self) -> None:
        """Test parsing arbitrary equality operator."""
        content = "package===1.0.custom"
        result = parse_constraints(content)
        assert result == ["package===1.0.custom"]


class TestParseReturnType:
    """Tests for validating return type and structure."""

    def test_returns_list(self) -> None:
        """Test that parse_constraints returns a list."""
        result = parse_constraints("requests==1.0")
        assert isinstance(result, list)

    def test_returns_list_of_strings(self) -> None:
        """Test that parse_constraints returns a list of strings."""
        result = parse_constraints("requests==1.0\nflask==2.0")
        assert all(isinstance(item, str) for item in result)

    def test_order_preserved(self) -> None:
        """Test that the order of constraints is preserved."""
        content = "zebra==1.0\napple==2.0\nmango==3.0"
        result = parse_constraints(content)
        assert result == ["zebra==1.0", "apple==2.0", "mango==3.0"]


class TestExtractPackageName:
    """Tests for extracting package names from constraint strings."""

    def test_exact_version(self) -> None:
        """Test extracting package name from exact version constraint."""
        result = extract_package_name("requests==2.31.0")
        assert result == "requests"

    def test_greater_than_equal_version(self) -> None:
        """Test extracting package name from >= version constraint."""
        result = extract_package_name("flask>=2.0.0")
        assert result == "flask"

    def test_less_than_version(self) -> None:
        """Test extracting package name from < version constraint."""
        result = extract_package_name("django<5.0.0")
        assert result == "django"

    def test_version_range(self) -> None:
        """Test extracting package name from version range constraint."""
        result = extract_package_name("urllib3>=1.26.0,<2.0.0")
        assert result == "urllib3"

    def test_compatible_release(self) -> None:
        """Test extracting package name from ~= compatible release."""
        result = extract_package_name("requests~=2.31")
        assert result == "requests"

    def test_not_equal_version(self) -> None:
        """Test extracting package name from != version constraint."""
        result = extract_package_name("package!=1.0.0")
        assert result == "package"

    def test_arbitrary_equality(self) -> None:
        """Test extracting package name from === arbitrary equality."""
        result = extract_package_name("package===1.0.custom")
        assert result == "package"

    def test_with_environment_marker(self) -> None:
        """Test extracting package name with environment marker."""
        result = extract_package_name('numpy>=1.24 ; python_version >= "3.9"')
        assert result == "numpy"

    def test_with_single_extra(self) -> None:
        """Test extracting package name with single extra."""
        result = extract_package_name("requests[security]==2.31.0")
        assert result == "requests"

    def test_with_multiple_extras(self) -> None:
        """Test extracting package name with multiple extras."""
        result = extract_package_name("celery[redis,auth]>=5.3.0")
        assert result == "celery"

    def test_extra_and_marker(self) -> None:
        """Test extracting package name with both extra and marker."""
        result = extract_package_name('uvicorn[standard]>=0.23.0 ; python_version >= "3.8"')
        assert result == "uvicorn"

    def test_package_name_with_dash(self) -> None:
        """Test extracting package name containing dashes."""
        result = extract_package_name("psycopg2-binary==2.9.9")
        assert result == "psycopg2-binary"

    def test_package_name_with_underscore(self) -> None:
        """Test extracting package name containing underscores."""
        result = extract_package_name("typing_extensions>=4.0")
        assert result == "typing_extensions"

    def test_package_name_with_dots(self) -> None:
        """Test extracting package name containing dots."""
        result = extract_package_name("zope.interface>=5.0")
        assert result == "zope.interface"

    def test_lowercase_normalization(self) -> None:
        """Test that package name is normalized to lowercase."""
        result = extract_package_name("NumPy>=1.24.0")
        assert result == "numpy"

    def test_mixed_case_normalization(self) -> None:
        """Test normalization of mixed case package names."""
        result = extract_package_name("Flask==2.3.3")
        assert result == "flask"

    def test_url_constraint(self) -> None:
        """Test extracting package name from URL-based constraint."""
        result = extract_package_name("package @ https://example.com/package-1.0.0.tar.gz")
        assert result == "package"

    def test_pre_release_version(self) -> None:
        """Test extracting package name from pre-release version."""
        result = extract_package_name("package==1.0.0a1")
        assert result == "package"

    def test_post_release_version(self) -> None:
        """Test extracting package name from post-release version."""
        result = extract_package_name("package==1.0.0.post1")
        assert result == "package"

    def test_dev_release_version(self) -> None:
        """Test extracting package name from dev release version."""
        result = extract_package_name("package==1.0.0.dev1")
        assert result == "package"

    def test_local_version(self) -> None:
        """Test extracting package name from local version identifier."""
        result = extract_package_name("package==1.0.0+local.version")
        assert result == "package"

    def test_wildcard_version(self) -> None:
        """Test extracting package name from wildcard version."""
        result = extract_package_name("package==1.0.*")
        assert result == "package"

    def test_epoch_version(self) -> None:
        """Test extracting package name from version with epoch."""
        result = extract_package_name("package==1!2.0.0")
        assert result == "package"


class TestMergeConstraints:
    """Tests for merging base and custom constraint lists."""

    def test_basic_merge_disjoint_packages(self) -> None:
        """Test merging two lists with no overlapping packages."""
        base = ["flask==2.0.0"]
        custom = ["django==4.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["django==4.0.0", "flask==2.0.0"]

    def test_custom_overrides_base_same_package(self) -> None:
        """Test that custom constraint takes precedence for same package."""
        base = ["requests==1.0.0"]
        custom = ["requests==2.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["requests==2.0.0"]

    def test_merge_with_multiple_packages(self) -> None:
        """Test merging multiple packages with some overlap."""
        base = ["requests==1.0", "flask==2.0"]
        custom = ["requests==2.0", "django==4.0"]
        result = merge_constraints(base, custom)
        assert result == ["django==4.0", "flask==2.0", "requests==2.0"]

    def test_empty_custom_returns_base(self) -> None:
        """Test that empty custom list returns base constraints sorted."""
        base = ["flask==2.0.0", "django==4.0.0"]
        custom: list[str] = []
        result = merge_constraints(base, custom)
        assert result == ["django==4.0.0", "flask==2.0.0"]

    def test_empty_base_returns_custom(self) -> None:
        """Test that empty base list returns custom constraints sorted."""
        base: list[str] = []
        custom = ["flask==2.0.0", "django==4.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["django==4.0.0", "flask==2.0.0"]

    def test_both_empty_returns_empty(self) -> None:
        """Test that both empty lists returns empty list."""
        base: list[str] = []
        custom: list[str] = []
        result = merge_constraints(base, custom)
        assert result == []

    def test_case_insensitive_package_comparison(self) -> None:
        """Test that package names are compared case-insensitively."""
        base = ["Requests==1.0.0"]
        custom = ["requests==2.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["requests==2.0.0"]

    def test_case_insensitive_mixed_case(self) -> None:
        """Test case insensitivity with mixed case package names."""
        base = ["NumPy==1.24.0", "Flask==2.0.0"]
        custom = ["numpy==1.25.0"]
        result = merge_constraints(base, custom)
        assert result == ["Flask==2.0.0", "numpy==1.25.0"]

    def test_result_sorted_alphabetically(self) -> None:
        """Test that result is sorted alphabetically by package name."""
        base = ["zebra==1.0", "apple==2.0"]
        custom = ["mango==3.0"]
        result = merge_constraints(base, custom)
        assert result == ["apple==2.0", "mango==3.0", "zebra==1.0"]

    def test_override_with_different_version_specifier(self) -> None:
        """Test override when version specifiers differ."""
        base = ["requests==2.31.0"]
        custom = ["requests>=3.0.0,<4.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["requests>=3.0.0,<4.0.0"]

    def test_override_with_extras(self) -> None:
        """Test that package with extras overrides base."""
        base = ["requests==2.31.0"]
        custom = ["requests[security]==3.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["requests[security]==3.0.0"]

    def test_override_base_with_extras(self) -> None:
        """Test that custom overrides base when base has extras."""
        base = ["requests[security]==2.31.0"]
        custom = ["requests==3.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["requests==3.0.0"]

    def test_override_with_environment_marker(self) -> None:
        """Test override when custom has environment marker."""
        base = ["numpy==1.24.0"]
        custom = ['numpy>=1.25.0 ; python_version >= "3.10"']
        result = merge_constraints(base, custom)
        assert result == ['numpy>=1.25.0 ; python_version >= "3.10"']

    def test_override_base_with_environment_marker(self) -> None:
        """Test override when base has environment marker."""
        base = ['numpy==1.24.0 ; python_version >= "3.9"']
        custom = ["numpy>=1.25.0"]
        result = merge_constraints(base, custom)
        assert result == ["numpy>=1.25.0"]

    def test_merge_preserves_original_constraint_format(self) -> None:
        """Test that original constraint formatting is preserved."""
        base = ["flask[async]==2.3.3", "django>=4.2.0,<5.0.0"]
        custom = ['requests==2.31.0 ; python_version >= "3.8"']
        result = merge_constraints(base, custom)
        assert result == [
            "django>=4.2.0,<5.0.0",
            "flask[async]==2.3.3",
            'requests==2.31.0 ; python_version >= "3.8"',
        ]

    def test_merge_with_dash_underscore_packages(self) -> None:
        """Test merging packages with dashes and underscores."""
        base = ["psycopg2-binary==2.9.9"]
        custom = ["typing_extensions>=4.0"]
        result = merge_constraints(base, custom)
        assert result == ["psycopg2-binary==2.9.9", "typing_extensions>=4.0"]

    def test_merge_url_constraint(self) -> None:
        """Test merging URL-based constraints."""
        base = ["package==1.0.0"]
        custom = ["package @ https://example.com/package-2.0.0.tar.gz"]
        result = merge_constraints(base, custom)
        assert result == ["package @ https://example.com/package-2.0.0.tar.gz"]

    def test_merge_complex_scenario(self) -> None:
        """Test complex merge with various constraint types."""
        base = [
            "requests==2.31.0",
            "flask[async]==2.3.3",
            "numpy==1.24.3",
            "django>=4.0.0,<5.0.0",
            "urllib3>=1.26.0,<2.0.0",
        ]
        custom = [
            "requests>=3.0.0",  # Override
            "numpy>=1.25.0",  # Override
            "celery[redis,auth]>=5.3.0",  # New
            'pandas>=2.0.0 ; python_version >= "3.10"',  # New
        ]
        result = merge_constraints(base, custom)
        expected = [
            "celery[redis,auth]>=5.3.0",
            "django>=4.0.0,<5.0.0",
            "flask[async]==2.3.3",
            "numpy>=1.25.0",
            'pandas>=2.0.0 ; python_version >= "3.10"',
            "requests>=3.0.0",
            "urllib3>=1.26.0,<2.0.0",
        ]
        assert result == expected

    def test_single_package_in_both(self) -> None:
        """Test with just one package in both lists."""
        base = ["requests==1.0.0"]
        custom = ["requests==2.0.0"]
        result = merge_constraints(base, custom)
        assert len(result) == 1
        assert result[0] == "requests==2.0.0"

    def test_multiple_custom_overrides(self) -> None:
        """Test multiple packages being overridden by custom."""
        base = ["flask==2.0.0", "requests==1.0.0", "django==3.0.0"]
        custom = ["flask==3.0.0", "django==4.0.0"]
        result = merge_constraints(base, custom)
        assert result == ["django==4.0.0", "flask==3.0.0", "requests==1.0.0"]
