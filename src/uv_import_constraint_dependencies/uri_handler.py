"""URI handler for remote constraints files.

This module provides functionality to detect URIs (HTTP/HTTPS) and
download constraints files from remote locations.
"""

import urllib.request
import urllib.error
from urllib.parse import urlparse
from typing import Optional


class URIError(Exception):
    """Exception raised for URI-related errors."""

    pass


def is_uri(path: str) -> bool:
    """
    Check if a given path is a URI (http:// or https://).

    This function checks if the provided path starts with http:// or https://
    (case-sensitive). This represents a remote resource accessible via HTTP
    or HTTPS protocols.

    Args:
        path: A string that could be either a local file path or a URI.

    Returns:
        True if the path starts with http:// or https:// (lowercase), False otherwise.

    Examples:
        >>> is_uri('https://example.com/constraints.txt')
        True

        >>> is_uri('http://example.com/constraints.txt')
        True

        >>> is_uri('constraints.txt')
        False

        >>> is_uri('/path/to/local/file.txt')
        False

        >>> is_uri('file:///path/to/file.txt')
        False

        >>> is_uri('HTTPS://example.com/file.txt')
        False
    """
    # Use string prefix check for case-sensitive scheme detection
    # (urlparse normalizes schemes to lowercase, which we don't want)
    return path.startswith('http://') or path.startswith('https://')


def fetch_constraints(uri: str, timeout: int = 30) -> str:
    """
    Download constraints file from a URI and return its content.

    This function fetches a constraints file from a remote HTTP/HTTPS URL
    using the standard library's urllib. It handles common network errors
    and provides meaningful error messages.

    Args:
        uri: The full URI to the constraints file (must be http:// or https://).
        timeout: Maximum time in seconds to wait for the download.
            Defaults to 30 seconds.

    Returns:
        The content of the constraints file as a UTF-8 decoded string.

    Raises:
        URIError: If the download fails due to network issues, HTTP errors,
            invalid URL, timeout, or decoding errors.

    Examples:
        >>> content = fetch_constraints('https://example.com/constraints.txt')
        >>> print(content)
        'requests==2.31.0\\nflask>=2.0.0'

        >>> fetch_constraints('https://example.com/missing.txt')
        URIError: Failed to fetch constraints from URI: HTTP Error 404: Not Found
    """
    if not is_uri(uri):
        raise URIError(f"Invalid URI: {uri}. Must be an http:// or https:// URL.")

    try:
        with urllib.request.urlopen(uri, timeout=timeout) as response:
            # Read the response content
            content_bytes = response.read()

            # Determine encoding from response headers, default to UTF-8
            charset = _get_charset_from_response(response)

            try:
                return content_bytes.decode(charset)
            except UnicodeDecodeError as e:
                raise URIError(
                    f"Failed to decode content from {uri} as {charset}: {e}"
                ) from e

    except urllib.error.HTTPError as e:
        raise URIError(
            f"Failed to fetch constraints from URI: HTTP Error {e.code}: {e.reason}"
        ) from e

    except urllib.error.URLError as e:
        raise URIError(f"Failed to fetch constraints from URI: {e.reason}") from e

    except TimeoutError:
        raise URIError(
            f"Timeout while fetching constraints from {uri}. "
            f"Consider increasing the timeout (current: {timeout}s)."
        )

    except Exception as e:
        raise URIError(f"Unexpected error fetching constraints from {uri}: {e}") from e


def _get_charset_from_response(
    response: urllib.request.http.client.HTTPResponse,
) -> str:
    """
    Extract charset from HTTP response headers.

    Args:
        response: The HTTP response object.

    Returns:
        The charset string, defaulting to 'utf-8' if not specified.
    """
    content_type = response.headers.get('Content-Type', '')

    # Parse Content-Type header for charset
    # Example: "text/plain; charset=utf-8"
    for part in content_type.split(';'):
        part = part.strip()
        if part.lower().startswith('charset='):
            return part.split('=', 1)[1].strip().strip('"\'')

    return 'utf-8'
