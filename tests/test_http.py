"""Tests for HttpClient functionality."""

import time
from collections import OrderedDict
from unittest.mock import Mock, patch

import pytest
import requests

from grokipedia.exceptions import HttpError, NotFoundError, RateLimitError
from grokipedia.http import HttpClient


class TestHttpClient:
    """Test HttpClient functionality."""

    def test_initialization(self):
        """Test HttpClient initializes with correct parameters."""
        client = HttpClient(
            user_agent="test-agent",
            timeout=5.0,
            requests_per_minute=10,
            cache_ttl=60.0,
        )

        assert client.user_agent == "test-agent"
        assert client.timeout == 5.0
        assert client.requests_per_minute == 10
        assert client.cache_ttl == 60.0
        assert client._min_interval == 6.0  # 60 / 10

    @patch('grokipedia.http.requests.Session.get')
    def test_caching_disabled(self, mock_get):
        """Test no caching when cache_ttl is None."""
        mock_response = Mock()
        mock_response.text = "response"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = HttpClient(cache_ttl=None)
        result1 = client.get("http://example.com")
        result2 = client.get("http://example.com")

        assert result1 == "response"
        assert result2 == "response"
        assert mock_get.call_count == 2  # Called twice, no caching

    @patch('grokipedia.http.requests.Session.get')
    def test_caching_enabled(self, mock_get):
        """Test caching when cache_ttl is set."""
        mock_response = Mock()
        mock_response.text = "response"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = HttpClient(cache_ttl=300.0)
        result1 = client.get("http://example.com")
        result2 = client.get("http://example.com")

        assert result1 == "response"
        assert result2 == "response"
        assert mock_get.call_count == 1  # Called once, cached

    @patch('grokipedia.http.time.time')
    @patch('grokipedia.http.time.sleep')
    @patch('grokipedia.http.requests.Session.get')
    def test_rate_limiting(self, mock_get, mock_sleep, mock_time):
        """Test rate limiting enforces minimum interval."""
        # Mock time to simulate rapid requests
        call_times = [0, 0.1, 0.2, 2.1, 2.2, 2.3]  # Requests at 0s, 0.1s, 0.2s, 2.1s, 2.2s, 2.3s
        mock_time.side_effect = call_times

        mock_response = Mock()
        mock_response.text = "response"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = HttpClient(requests_per_minute=30)  # 2 second intervals
        client._min_interval = 2.0

        client.get("http://example.com/1")
        client.get("http://example.com/2")
        client.get("http://example.com/3")

        # Should sleep to enforce rate limiting
        assert mock_sleep.call_count >= 1  # At least one sleep call for rate limiting

    @patch('grokipedia.http.requests.Session.get')
    def test_http_error_mapping_404(self, mock_get):
        """Test 404 errors map to NotFoundError."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error", response=mock_response
        )
        mock_get.return_value = mock_response

        client = HttpClient()
        with pytest.raises(NotFoundError, match="Not found"):
            client.get("http://example.com")

    @patch('grokipedia.http.requests.Session.get')
    def test_rate_limit_error_mapping_429(self, mock_get):
        """Test 429 errors map to RateLimitError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limited"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Client Error", response=mock_response
        )
        mock_get.return_value = mock_response

        client = HttpClient()
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            client.get("http://example.com")

    @patch('grokipedia.http.requests.Session.get')
    def test_network_error_mapping(self, mock_get):
        """Test network errors map to HttpError."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = HttpClient()
        with pytest.raises(HttpError, match="Request failed"):
            client.get("http://example.com")

    def test_clear_cache(self):
        """Test cache clearing."""
        client = HttpClient(cache_ttl=300.0)
        client._cache = {"key": (time.time(), "value")}

        client.clear_cache()
        assert client._cache == {}

    @patch('grokipedia.http.time.time')
    def test_get_cache_size_with_expiration(self, mock_time):
        """Test cache size calculation with expired entries."""
        mock_time.return_value = 1000.0

        client = HttpClient(cache_ttl=100.0)
        # Add entries: one expired, one valid
        client._cache = OrderedDict([
            ("expired", (800.0, "old")),  # 200s ago, expired
            ("valid", (950.0, "new")),    # 50s ago, still valid
        ])

        size = client.get_cache_size()
        assert size == 1  # Only valid entry remains

    @patch('grokipedia.http.requests.Session.get')
    def test_lru_cache_bounded(self, mock_get):
        """Test LRU cache respects max_cache_entries limit."""
        mock_response = Mock()
        mock_response.text = "response"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = HttpClient(cache_ttl=300.0, max_cache_entries=2)

        # Make 3 different requests
        client.get("http://example.com/1")
        client.get("http://example.com/2")
        client.get("http://example.com/3")

        # Cache should only have 2 entries (LRU eviction)
        assert len(client._cache) == 2
        # Most recently used should be at the end
        assert list(client._cache.keys())[-1] == "http://example.com/3"
        # Oldest should be evicted
        assert "http://example.com/1" not in client._cache

    @patch('grokipedia.http.requests.Session.get')
    def test_lru_cache_access_order(self, mock_get):
        """Test LRU cache maintains access order."""
        mock_response = Mock()
        mock_response.text = "response"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = HttpClient(cache_ttl=300.0, max_cache_entries=3)

        # Make requests in order
        client.get("http://example.com/1")
        client.get("http://example.com/2")
        client.get("http://example.com/3")

        # Access middle item again (should move to end)
        client.get("http://example.com/2")

        # Order should now be: 1, 3, 2
        keys = list(client._cache.keys())
        assert keys == ["http://example.com/1", "http://example.com/3", "http://example.com/2"]

    def test_get_cache_size_no_ttl(self):
        """Test cache size when caching is disabled."""
        client = HttpClient(cache_ttl=None)
        client._cache = {"key": (1000.0, "value")}

        size = client.get_cache_size()
        assert size == 1  # Cache exists but TTL is None, so entries are still counted
