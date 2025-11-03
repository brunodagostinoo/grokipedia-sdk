"""Live integration tests for API search functionality."""

import pytest

from grokipedia import GrokipediaClient


@pytest.mark.live
class TestLiveApiSearch:
    """Test API search against real Grokipedia site."""

    def test_api_search_basic(self):
        """Test basic API search functionality."""
        client = GrokipediaClient(enable_api_search=True, respect_robots=False)

        results = client.search("elon musk", limit=5)

        assert len(results) > 0
        assert all(isinstance(result, dict) for result in results) or all(hasattr(result, 'title') for result in results)

        # If results are SearchResult objects, check basic structure
        if results and hasattr(results[0], 'title'):
            assert results[0].title
            assert results[0].url
            assert "grokipedia.com" in results[0].url

    def test_api_search_pagination(self):
        """Test API search pagination."""
        client = GrokipediaClient(enable_api_search=True, respect_robots=False)

        results_page1 = client.search("elon musk", limit=3, page=1)
        results_page2 = client.search("elon musk", limit=3, page=2)

        # Results should be different or page 2 might have fewer results
        assert len(results_page1) >= 0
        assert len(results_page2) >= 0

        # If both pages have results, they should be different
        if results_page1 and results_page2:
            titles_page1 = {r.title if hasattr(r, 'title') else str(r.get('title', '')) for r in results_page1}
            titles_page2 = {r.title if hasattr(r, 'title') else str(r.get('title', '')) for r in results_page2}
            # Allow some overlap but they shouldn't be identical
            assert titles_page1 != titles_page2

    def test_api_search_empty_query(self):
        """Test API search with empty or very short query."""
        client = GrokipediaClient(enable_api_search=True, respect_robots=False)

        results = client.search("", limit=5)
        # Empty query might return no results or default results
        assert isinstance(results, list)

    def test_api_search_limit_parameter(self):
        """Test API search respects limit parameter."""
        client = GrokipediaClient(enable_api_search=True, respect_robots=False)

        results = client.search("mars", limit=2)
        assert len(results) <= 2

        results_larger = client.search("mars", limit=5)
        assert len(results_larger) <= 5

    def test_api_search_no_results(self):
        """Test API search with query that should return no results."""
        client = GrokipediaClient(enable_api_search=True, respect_robots=False)

        results = client.search("xyzabc123nonexistent", limit=5)
        # Should return empty list, not fail
        assert results == [] or len(results) == 0
