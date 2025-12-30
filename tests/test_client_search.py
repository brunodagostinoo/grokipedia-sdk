"""Tests for GrokipediaClient search functionality."""

from unittest.mock import Mock, patch

from grokipedia.client import GrokipediaClient


class TestClientSitemapSearch:
    """Test sitemap-based search functionality."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch.object(GrokipediaClient, '_load_sitemap_index')
    def test_sitemap_search_basic(self, mock_load_sitemap, mock_http_class, _mock_check):
        """Test basic sitemap search functionality."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Mock sitemap index with some articles
        mock_load_sitemap.return_value = {
            "Mars": "https://grokipedia.com/page/Mars",
            "Earth": "https://grokipedia.com/page/Earth",
            "Mars Rover": "https://grokipedia.com/page/Mars_Rover",
        }

        client = GrokipediaClient(enable_api_search=False)
        results = client.search("mars", limit=10)

        assert len(results) == 2  # Mars and Mars Rover
        assert results[0].title == "Mars"
        assert results[0].url == "https://grokipedia.com/page/Mars"
        assert results[1].title == "Mars Rover"

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch.object(GrokipediaClient, '_load_sitemap_index')
    def test_sitemap_search_ranking(self, mock_load_sitemap, mock_http_class, _mock_check):
        """Test sitemap search result ranking."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Mock sitemap with various matches
        mock_load_sitemap.return_value = {
            "Mars Exploration": "https://grokipedia.com/page/Mars_Exploration",
            "Mars": "https://grokipedia.com/page/Mars",
            "Earth and Mars": "https://grokipedia.com/page/Earth_and_Mars",
            "Jupiter": "https://grokipedia.com/page/Jupiter",
        }

        client = GrokipediaClient(enable_api_search=False)
        results = client.search("mars", limit=10)

        # Should be ranked: exact prefix first, then substring matches, then by length
        assert len(results) == 3
        assert results[0].title == "Mars"  # Exact match, shortest
        assert results[1].title == "Mars Exploration"  # Prefix match
        assert results[2].title == "Earth and Mars"  # Contains "Mars"

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch.object(GrokipediaClient, '_load_sitemap_index')
    def test_sitemap_search_pagination_warning(self, mock_load_sitemap, mock_http_class, _mock_check, caplog):
        """Test pagination warning for sitemap search."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_load_sitemap.return_value = {"Mars": "https://grokipedia.com/page/Mars"}

        client = GrokipediaClient(enable_api_search=False)
        results = client.search("mars", page=2)

        assert "Sitemap search does not support pagination" in caplog.text
        assert len(results) == 1  # Still returns results

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch.object(GrokipediaClient, '_load_sitemap_index')
    def test_sitemap_search_no_results(self, mock_load_sitemap, mock_http_class, _mock_check):
        """Test sitemap search with no matching results."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_load_sitemap.return_value = {"Earth": "https://grokipedia.com/page/Earth"}

        client = GrokipediaClient(enable_api_search=False)
        results = client.search("mars")

        assert not results

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch.object(GrokipediaClient, '_load_sitemap_index')
    def test_sitemap_search_limit(self, mock_load_sitemap, mock_http_class, _mock_check):
        """Test sitemap search respects limit parameter."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Mock many results
        mock_load_sitemap.return_value = {
            f"Article{i}": f"https://grokipedia.com/page/Article{i}"
            for i in range(10)
        }

        client = GrokipediaClient(enable_api_search=False)
        results = client.search("article", limit=3)

        assert len(results) == 3


class TestClientApiSearch:
    """Test API-based search functionality."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_api_search_enabled(self, mock_http_class, mock_check):
        """Test that API search is used when enabled."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Mock check_api_disallowed to return False (API access allowed)
        mock_check.return_value = False

        # Mock API response
        mock_http.get.return_value = '''{"results": [
            {"title": "Mars", "slug": "Mars", "snippet": "A red planet"},
            {"title": "Earth", "slug": "Earth", "snippet": "Our home"}
        ]}'''

        client = GrokipediaClient(enable_api_search=True)
        results = client.search("planet", limit=10)

        assert len(results) == 2
        assert results[0].title == "Mars"
        assert results[0].url == "https://grokipedia.com/page/Mars"
        assert results[0].snippet == "A red planet"
        assert results[1].title == "Earth"

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_api_search_pagination(self, mock_http_class, mock_check):
        """Test API search pagination."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Mock check_api_disallowed to return False (API access allowed)
        mock_check.return_value = False
        mock_http.get.return_value = '{"results": [{"title": "Mars", "slug": "Mars", "snippet": "Planet"}]}'

        client = GrokipediaClient(enable_api_search=True)
        _results = client.search("mars", page=2, limit=5)

        # Check that offset is calculated correctly (page 2, limit 5 = offset 5)
        call_args = mock_http.get.call_args[0][0]
        assert "offset=5" in call_args
        assert "limit=5" in call_args

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_api_search_invalid_json(self, mock_http_class, _mock_check):
        """Test API search handles invalid JSON gracefully."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.get.return_value = "invalid json"

        client = GrokipediaClient(enable_api_search=True)
        results = client.search("test")

        assert not results  # Should return empty list on JSON error

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_api_search_http_error(self, mock_http_class, _mock_check):
        """Test API search handles HTTP errors gracefully."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        mock_http.get.side_effect = Exception("Connection failed")

        client = GrokipediaClient(enable_api_search=True)
        results = client.search("test")

        assert not results  # Should return empty list on HTTP error

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_api_search_missing_fields(self, mock_http_class, mock_check):
        """Test API search handles missing fields in response."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http
        # Mock check_api_disallowed to return False (API access allowed)
        mock_check.return_value = False
        mock_http.get.return_value = '''{"results": [
            {"title": "Mars", "slug": "Mars"},
            {"title": "Earth"}
        ]}'''

        client = GrokipediaClient(enable_api_search=True)
        results = client.search("planet")

        assert len(results) == 1  # Only results with both title and slug are included
        assert results[0].title == "Mars"
        assert results[0].snippet is None  # Missing snippet
        # Second result should be skipped due to missing slug
        assert len(results) == 1
