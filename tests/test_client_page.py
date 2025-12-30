"""Tests for GrokipediaClient page and sitemap functionality."""

from unittest.mock import Mock, patch

import pytest

from grokipedia.client import GrokipediaClient
from grokipedia.exceptions import NotFoundError, ParseError
from grokipedia.models import Page, Section


class TestClientGetPage:
    """Test page fetching functionality."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch('grokipedia.client.parse_article_page')
    def test_get_page_by_title(self, mock_parse, mock_http_class, _mock_check):
        """Test fetching page by title."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_page = Page(
            title="Mars",
            url="https://grokipedia.com/page/Mars",
            summary="A planet",
            sections=[Section(title="Geography", html="<p>Content</p>", text="Content")],
        )
        mock_parse.return_value = mock_page
        mock_http.get.return_value = "<html>...</html>"

        client = GrokipediaClient()
        result = client.get_page("Mars")

        assert result == mock_page
        mock_http.get.assert_called_once_with("https://grokipedia.com/page/Mars")

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch('grokipedia.client.parse_article_page')
    def test_get_page_by_url(self, mock_parse, mock_http_class, _mock_check):
        """Test fetching page by full URL."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_page = Page(
            title="Mars",
            url="https://example.com/page/Mars",
            summary="A planet",
            sections=[],
        )
        mock_parse.return_value = mock_page
        mock_http.get.return_value = "<html>...</html>"

        client = GrokipediaClient()
        result = client.get_page("https://example.com/page/Mars")

        assert result == mock_page
        mock_http.get.assert_called_once_with("https://example.com/page/Mars")

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_get_page_title_encoding(self, mock_http_class, _mock_check):
        """Test title encoding for URLs."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.get.return_value = '''<!DOCTYPE html>
<html>
<body>
<article>
<h1>Test Article</h1>
<p>Summary content.</p>
</article>
</body>
</html>'''

        client = GrokipediaClient()
        try:
            client.get_page("Mars (planet)")
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # We just want to check the URL was called correctly

        # Should URL encode special characters
        expected_url = "https://grokipedia.com/page/Mars_%28planet%29"
        mock_http.get.assert_called_once_with(expected_url)

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_get_page_http_error(self, mock_http_class, _mock_check):
        """Test HTTP NotFoundError propagates correctly."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.get.side_effect = NotFoundError("Not found: https://grokipedia.com/page/NonExistent")

        client = GrokipediaClient()

        with pytest.raises(NotFoundError, match="Not found"):
            client.get_page("NonExistent")

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch('grokipedia.client.parse_article_page')
    def test_get_page_parse_error(self, mock_parse, mock_http_class, _mock_check):
        """Test parse errors propagate correctly."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.get.return_value = "<html>...</html>"
        mock_parse.side_effect = ParseError("Failed to parse article page")

        client = GrokipediaClient()

        with pytest.raises(ParseError, match="Failed to parse"):
            client.get_page("BadPage")


class TestClientIterSitemap:  # pylint: disable=too-few-public-methods
    """Test sitemap iteration functionality."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch('grokipedia.client.iter_sitemap_urls')
    def test_iter_sitemap_delegates(self, mock_iter_urls, mock_http_class, _mock_check):
        """Test iter_sitemap delegates to iter_sitemap_urls."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        mock_iter_urls.return_value = iter(["url1", "url2", "url3"])

        client = GrokipediaClient()
        urls = list(client.iter_sitemap(max_urls=10))

        assert urls == ["url1", "url2", "url3"]
        mock_iter_urls.assert_called_once_with(
            "https://grokipedia.com", mock_http, 10
        )


class TestClientCacheUtils:
    """Test cache utility methods."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_clear_cache_delegates(self, mock_http_class, _mock_check):
        """Test clear_cache delegates to HTTP client."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        client = GrokipediaClient()
        client.clear_cache()

        mock_http.clear_cache.assert_called_once()

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_get_cache_size_delegates(self, mock_http_class, _mock_check):
        """Test get_cache_size delegates to HTTP client."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.get_cache_size.return_value = 42

        client = GrokipediaClient()
        size = client.get_cache_size()

        assert size == 42
        mock_http.get_cache_size.assert_called_once()


class TestClientInitialization:
    """Test client initialization and configuration."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_client_initialization_parameters(self, mock_http_class, mock_check):
        """Test client passes parameters to HTTP client."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Mock check_api_disallowed to return False (API access allowed)
        mock_check.return_value = False

        client = GrokipediaClient(
            base_url="https://test.com",
            user_agent="test-agent",
            timeout=5.0,
            requests_per_minute=10,
            cache_ttl=60.0,
            enable_api_search=True,
        )

        assert client.base_url == "https://test.com"
        assert client.enable_api_search is True
        mock_http_class.assert_called_once_with(
            user_agent="test-agent",
            timeout=5.0,
            requests_per_minute=10,
            cache_ttl=60.0,
            max_cache_entries=None,
        )

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_client_respects_robots_by_default(self, mock_http_class, _mock_check):
        """Test client checks robots.txt by default."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        GrokipediaClient()

        _mock_check.assert_called_once()

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_client_can_skip_robots_check(self, mock_http_class, _mock_check):
        """Test client can skip robots.txt check."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        GrokipediaClient(respect_robots=False)

        _mock_check.assert_not_called()
