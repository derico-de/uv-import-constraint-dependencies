"""Unit tests for the URI handler module.

This module tests the URI handling functions from the uri_handler module,
covering various scenarios including:
- URI detection for HTTP and HTTPS
- Detection of non-URI paths (local files)
- Fetching constraints from remote URIs
- Error handling for network issues
- Charset detection from response headers
"""

from unittest.mock import MagicMock, Mock, patch
import urllib.error
import urllib.request

import pytest

from uv_import_constraint_dependencies.uri_handler import (
    URIError,
    _get_charset_from_response,
    fetch_constraints,
    is_uri,
)


class TestIsUriHttps:
    """Tests for detecting HTTPS URIs."""

    def test_https_uri_detected(self) -> None:
        """Test that HTTPS URIs are correctly identified."""
        assert is_uri("https://example.com/constraints.txt") is True

    def test_https_uri_with_port(self) -> None:
        """Test that HTTPS URI with port is detected."""
        assert is_uri("https://example.com:8443/constraints.txt") is True

    def test_https_uri_with_path(self) -> None:
        """Test that HTTPS URI with path segments is detected."""
        assert is_uri("https://example.com/path/to/constraints.txt") is True

    def test_https_uri_with_query_string(self) -> None:
        """Test that HTTPS URI with query string is detected."""
        assert is_uri("https://example.com/constraints.txt?version=latest") is True

    def test_https_uri_with_fragment(self) -> None:
        """Test that HTTPS URI with fragment is detected."""
        assert is_uri("https://example.com/constraints.txt#section") is True

    def test_https_uri_fixture(self, valid_https_uri: str) -> None:
        """Test HTTPS URI detection using fixture."""
        assert is_uri(valid_https_uri) is True


class TestIsUriHttp:
    """Tests for detecting HTTP URIs."""

    def test_http_uri_detected(self) -> None:
        """Test that HTTP URIs are correctly identified."""
        assert is_uri("http://example.com/constraints.txt") is True

    def test_http_uri_with_port(self) -> None:
        """Test that HTTP URI with port is detected."""
        assert is_uri("http://example.com:8080/constraints.txt") is True

    def test_http_uri_with_path(self) -> None:
        """Test that HTTP URI with path segments is detected."""
        assert is_uri("http://example.com/path/to/constraints.txt") is True

    def test_http_uri_fixture(self, valid_http_uri: str) -> None:
        """Test HTTP URI detection using fixture."""
        assert is_uri(valid_http_uri) is True


class TestIsUriLocalPaths:
    """Tests for correctly rejecting local file paths."""

    def test_relative_path_not_uri(self) -> None:
        """Test that relative paths are not detected as URIs."""
        assert is_uri("constraints.txt") is False

    def test_absolute_path_not_uri(self) -> None:
        """Test that absolute paths are not detected as URIs."""
        assert is_uri("/path/to/constraints.txt") is False

    def test_relative_path_with_dot_not_uri(self) -> None:
        """Test that relative paths with ./ are not detected as URIs."""
        assert is_uri("./relative/path.txt") is False

    def test_relative_path_with_double_dot_not_uri(self) -> None:
        """Test that relative paths with ../ are not detected as URIs."""
        assert is_uri("../parent/constraints.txt") is False

    def test_windows_path_not_uri(self) -> None:
        """Test that Windows-style paths are not detected as URIs."""
        assert is_uri("C:\\Users\\test\\constraints.txt") is False


class TestIsUriOtherSchemes:
    """Tests for correctly rejecting non-HTTP/HTTPS schemes."""

    def test_file_uri_not_detected(self) -> None:
        """Test that file:// URIs are not detected as HTTP/HTTPS."""
        assert is_uri("file:///local/file.txt") is False

    def test_ftp_uri_not_detected(self) -> None:
        """Test that ftp:// URIs are not detected as HTTP/HTTPS."""
        assert is_uri("ftp://server.com/file.txt") is False

    def test_sftp_uri_not_detected(self) -> None:
        """Test that sftp:// URIs are not detected as HTTP/HTTPS."""
        assert is_uri("sftp://server.com/file.txt") is False

    def test_ssh_uri_not_detected(self) -> None:
        """Test that ssh:// URIs are not detected as HTTP/HTTPS."""
        assert is_uri("ssh://git@github.com/repo.git") is False

    def test_git_uri_not_detected(self) -> None:
        """Test that git:// URIs are not detected as HTTP/HTTPS."""
        assert is_uri("git://github.com/user/repo.git") is False

    def test_mailto_uri_not_detected(self) -> None:
        """Test that mailto: URIs are not detected as HTTP/HTTPS."""
        assert is_uri("mailto:user@example.com") is False

    def test_data_uri_not_detected(self) -> None:
        """Test that data: URIs are not detected as HTTP/HTTPS."""
        assert is_uri("data:text/plain;base64,SGVsbG8=") is False


class TestIsUriEdgeCases:
    """Tests for edge cases in URI detection."""

    def test_empty_string_not_uri(self) -> None:
        """Test that empty string is not detected as URI."""
        assert is_uri("") is False

    def test_whitespace_not_uri(self) -> None:
        """Test that whitespace is not detected as URI."""
        assert is_uri("   ") is False

    def test_scheme_only_not_valid_uri(self) -> None:
        """Test that scheme without path is still detected (urlparse behavior)."""
        # https:// alone has scheme 'https' and empty netloc
        assert is_uri("https://") is True

    def test_case_sensitive_scheme(self) -> None:
        """Test that scheme detection is case-sensitive (only lowercase accepted)."""
        # Only lowercase http:// and https:// are recognized
        # This is intentional for predictable behavior
        assert is_uri("HTTPS://example.com/file.txt") is False
        assert is_uri("Http://example.com/file.txt") is False

    def test_uri_with_authentication(self) -> None:
        """Test that URIs with user authentication are detected."""
        assert is_uri("https://user:pass@example.com/constraints.txt") is True

    def test_uri_with_ipv4(self) -> None:
        """Test that URIs with IPv4 addresses are detected."""
        assert is_uri("https://192.168.1.1/constraints.txt") is True

    def test_uri_with_ipv6(self) -> None:
        """Test that URIs with IPv6 addresses are detected."""
        assert is_uri("https://[::1]/constraints.txt") is True

    def test_invalid_uris_fixture(self, invalid_uris: list[str]) -> None:
        """Test that invalid URIs from fixture are not detected."""
        for uri in invalid_uris:
            assert is_uri(uri) is False


class TestFetchConstraintsSuccess:
    """Tests for successful constraint fetching."""

    def test_fetch_returns_content(self) -> None:
        """Test that fetch_constraints returns the response content."""
        mock_content = b"requests==2.31.0\nflask>=2.0.0"
        mock_response = MagicMock()
        mock_response.read.return_value = mock_content
        mock_response.headers = {"Content-Type": "text/plain; charset=utf-8"}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_constraints("https://example.com/constraints.txt")

        assert result == "requests==2.31.0\nflask>=2.0.0"

    def test_fetch_decodes_utf8_by_default(self) -> None:
        """Test that content is decoded as UTF-8 when no charset specified."""
        mock_content = "requests==2.31.0\nflask>=2.0.0".encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = mock_content
        mock_response.headers = {}  # No Content-Type header
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_constraints("https://example.com/constraints.txt")

        assert result == "requests==2.31.0\nflask>=2.0.0"

    def test_fetch_respects_charset_header(self) -> None:
        """Test that content is decoded using charset from Content-Type header."""
        mock_content = "requests==2.31.0".encode("latin-1")
        mock_response = MagicMock()
        mock_response.read.return_value = mock_content
        mock_response.headers = {"Content-Type": "text/plain; charset=latin-1"}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_constraints("https://example.com/constraints.txt")

        assert result == "requests==2.31.0"

    def test_fetch_with_custom_timeout(self) -> None:
        """Test that custom timeout is passed to urlopen."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"requests==2.31.0"
        mock_response.headers = {}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response) as mock_urlopen:
            fetch_constraints("https://example.com/constraints.txt", timeout=60)

        mock_urlopen.assert_called_once_with("https://example.com/constraints.txt", timeout=60)

    def test_fetch_with_empty_content(self) -> None:
        """Test fetching empty content returns empty string."""
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.headers = {}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_constraints("https://example.com/constraints.txt")

        assert result == ""

    def test_fetch_unicode_content(self) -> None:
        """Test fetching content with Unicode characters."""
        mock_content = "# Comments with unicode: äöü\nrequests==2.31.0".encode("utf-8")
        mock_response = MagicMock()
        mock_response.read.return_value = mock_content
        mock_response.headers = {"Content-Type": "text/plain; charset=utf-8"}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = fetch_constraints("https://example.com/constraints.txt")

        assert "äöü" in result
        assert "requests==2.31.0" in result


class TestFetchConstraintsInvalidUri:
    """Tests for invalid URI handling in fetch_constraints."""

    def test_raises_for_local_path(self) -> None:
        """Test that URIError is raised for local paths."""
        with pytest.raises(URIError, match="Invalid URI"):
            fetch_constraints("constraints.txt")

    def test_raises_for_file_uri(self) -> None:
        """Test that URIError is raised for file:// URIs."""
        with pytest.raises(URIError, match="Invalid URI"):
            fetch_constraints("file:///local/file.txt")

    def test_raises_for_ftp_uri(self) -> None:
        """Test that URIError is raised for ftp:// URIs."""
        with pytest.raises(URIError, match="Invalid URI"):
            fetch_constraints("ftp://server.com/file.txt")

    def test_raises_for_empty_string(self) -> None:
        """Test that URIError is raised for empty string."""
        with pytest.raises(URIError, match="Invalid URI"):
            fetch_constraints("")

    def test_error_message_contains_uri(self) -> None:
        """Test that error message includes the invalid URI."""
        with pytest.raises(URIError) as exc_info:
            fetch_constraints("invalid/path.txt")
        assert "invalid/path.txt" in str(exc_info.value)


class TestFetchConstraintsHttpErrors:
    """Tests for HTTP error handling in fetch_constraints."""

    def test_raises_for_404_error(self) -> None:
        """Test that URIError is raised for 404 Not Found."""
        http_error = urllib.error.HTTPError(
            url="https://example.com/missing.txt",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        with patch.object(urllib.request, "urlopen", side_effect=http_error):
            with pytest.raises(URIError, match="HTTP Error 404"):
                fetch_constraints("https://example.com/missing.txt")

    def test_raises_for_403_error(self) -> None:
        """Test that URIError is raised for 403 Forbidden."""
        http_error = urllib.error.HTTPError(
            url="https://example.com/forbidden.txt",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None,
        )
        with patch.object(urllib.request, "urlopen", side_effect=http_error):
            with pytest.raises(URIError, match="HTTP Error 403"):
                fetch_constraints("https://example.com/forbidden.txt")

    def test_raises_for_500_error(self) -> None:
        """Test that URIError is raised for 500 Server Error."""
        http_error = urllib.error.HTTPError(
            url="https://example.com/error.txt",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        with patch.object(urllib.request, "urlopen", side_effect=http_error):
            with pytest.raises(URIError, match="HTTP Error 500"):
                fetch_constraints("https://example.com/error.txt")

    def test_error_includes_reason(self) -> None:
        """Test that HTTP error message includes the reason."""
        http_error = urllib.error.HTTPError(
            url="https://example.com/test.txt",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        with patch.object(urllib.request, "urlopen", side_effect=http_error):
            with pytest.raises(URIError, match="Not Found"):
                fetch_constraints("https://example.com/test.txt")


class TestFetchConstraintsNetworkErrors:
    """Tests for network error handling in fetch_constraints."""

    def test_raises_for_connection_refused(self) -> None:
        """Test that URIError is raised when connection is refused."""
        url_error = urllib.error.URLError("Connection refused")
        with patch.object(urllib.request, "urlopen", side_effect=url_error):
            with pytest.raises(URIError, match="Connection refused"):
                fetch_constraints("https://example.com/constraints.txt")

    def test_raises_for_dns_failure(self) -> None:
        """Test that URIError is raised for DNS resolution failure."""
        url_error = urllib.error.URLError("Name or service not known")
        with patch.object(urllib.request, "urlopen", side_effect=url_error):
            with pytest.raises(URIError, match="Name or service not known"):
                fetch_constraints("https://nonexistent.example.com/file.txt")

    def test_raises_for_ssl_error(self) -> None:
        """Test that URIError is raised for SSL/TLS errors."""
        url_error = urllib.error.URLError("SSL: CERTIFICATE_VERIFY_FAILED")
        with patch.object(urllib.request, "urlopen", side_effect=url_error):
            with pytest.raises(URIError, match="SSL"):
                fetch_constraints("https://example.com/file.txt")

    def test_raises_for_timeout(self) -> None:
        """Test that URIError is raised on timeout."""
        with patch.object(urllib.request, "urlopen", side_effect=TimeoutError):
            with pytest.raises(URIError, match="Timeout"):
                fetch_constraints("https://example.com/constraints.txt")

    def test_timeout_error_includes_timeout_value(self) -> None:
        """Test that timeout error message includes the timeout value."""
        with patch.object(urllib.request, "urlopen", side_effect=TimeoutError):
            with pytest.raises(URIError, match="30s"):
                fetch_constraints("https://example.com/constraints.txt", timeout=30)


class TestFetchConstraintsDecodingErrors:
    """Tests for content decoding error handling."""

    def test_raises_for_invalid_utf8(self) -> None:
        """Test that URIError is raised for invalid UTF-8 content."""
        # Invalid UTF-8 byte sequence
        mock_content = b"\xff\xfe invalid utf-8"
        mock_response = MagicMock()
        mock_response.read.return_value = mock_content
        mock_response.headers = {"Content-Type": "text/plain; charset=utf-8"}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            with pytest.raises(URIError, match="Failed to decode"):
                fetch_constraints("https://example.com/constraints.txt")

    def test_error_includes_charset(self) -> None:
        """Test that decoding error message includes the charset."""
        mock_content = b"\xff\xfe"
        mock_response = MagicMock()
        mock_response.read.return_value = mock_content
        mock_response.headers = {"Content-Type": "text/plain; charset=utf-8"}
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            with pytest.raises(URIError, match="utf-8"):
                fetch_constraints("https://example.com/constraints.txt")


class TestFetchConstraintsUnexpectedErrors:
    """Tests for unexpected error handling."""

    def test_catches_unexpected_exceptions(self) -> None:
        """Test that unexpected exceptions are caught and re-raised as URIError."""
        with patch.object(urllib.request, "urlopen", side_effect=RuntimeError("Unexpected")):
            with pytest.raises(URIError, match="Unexpected error"):
                fetch_constraints("https://example.com/constraints.txt")

    def test_original_exception_preserved(self) -> None:
        """Test that original exception is chained to URIError."""
        original_error = RuntimeError("Original error")
        with patch.object(urllib.request, "urlopen", side_effect=original_error):
            with pytest.raises(URIError) as exc_info:
                fetch_constraints("https://example.com/constraints.txt")
            assert exc_info.value.__cause__ is original_error


class TestGetCharsetFromResponse:
    """Tests for the _get_charset_from_response helper function."""

    def test_extracts_charset_from_content_type(self) -> None:
        """Test charset extraction from Content-Type header."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain; charset=utf-8"}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-8"

    def test_extracts_charset_with_quotes(self) -> None:
        """Test charset extraction when value is quoted."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": 'text/plain; charset="utf-8"'}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-8"

    def test_extracts_charset_with_single_quotes(self) -> None:
        """Test charset extraction when value has single quotes."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain; charset='utf-8'"}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-8"

    def test_extracts_charset_case_insensitive(self) -> None:
        """Test that charset parameter name matching is case-insensitive."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain; CHARSET=utf-8"}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-8"

    def test_defaults_to_utf8_no_content_type(self) -> None:
        """Test that UTF-8 is returned when Content-Type header is missing."""
        mock_response = MagicMock()
        mock_response.headers = {}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-8"

    def test_defaults_to_utf8_no_charset(self) -> None:
        """Test that UTF-8 is returned when charset is not in Content-Type."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain"}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-8"

    def test_extracts_charset_with_multiple_params(self) -> None:
        """Test charset extraction when Content-Type has multiple parameters."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain; boundary=something; charset=iso-8859-1"}

        result = _get_charset_from_response(mock_response)

        assert result == "iso-8859-1"

    def test_extracts_charset_from_complex_content_type(self) -> None:
        """Test charset extraction from complex Content-Type header."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain; charset=utf-16; format=flowed"}

        result = _get_charset_from_response(mock_response)

        assert result == "utf-16"


class TestURIError:
    """Tests for the URIError exception class."""

    def test_uri_error_is_exception(self) -> None:
        """Test that URIError is an Exception subclass."""
        assert issubclass(URIError, Exception)

    def test_uri_error_can_be_raised(self) -> None:
        """Test that URIError can be raised and caught."""
        with pytest.raises(URIError):
            raise URIError("Test error message")

    def test_uri_error_preserves_message(self) -> None:
        """Test that URIError preserves the error message."""
        try:
            raise URIError("Test error message")
        except URIError as e:
            assert str(e) == "Test error message"

    def test_uri_error_with_empty_message(self) -> None:
        """Test that URIError can be created with empty message."""
        error = URIError("")
        assert str(error) == ""
