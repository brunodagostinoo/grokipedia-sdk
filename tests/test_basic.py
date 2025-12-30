"""Basic tests for Grokipedia SDK."""

from unittest.mock import Mock, patch

from grokipedia.client import GrokipediaClient
from grokipedia.parser import _title_to_slug, parse_article_page, parse_search_results
from grokipedia.sitemap import parse_sitemap_index, parse_sitemap_part


class TestTitleToSlug:
    """Test title to slug conversion."""

    def test_simple_title(self):
        """Test simple title conversion."""
        assert _title_to_slug("Mars") == "Mars"

    def test_title_with_spaces(self):
        """Test title with spaces."""
        assert _title_to_slug("Mars Exploration") == "Mars_Exploration"

    def test_title_with_special_chars(self):
        """Test title with special characters."""
        assert _title_to_slug("Mars (planet)") == "Mars_%28planet%29"  # Should be URL encoded

    def test_title_with_punctuation(self):
        """Test title with punctuation (now always URL-encoded)."""
        assert _title_to_slug("Mars: The Red Planet") == "Mars%3A_The_Red_Planet"


class TestSitemapTitleDecoding:  # pylint: disable=too-few-public-methods
    """Test sitemap title decoding in client."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    @patch('grokipedia.client.iter_sitemap_urls')
    def test_sitemap_title_url_decoding(self, mock_iter_urls, mock_http_class, _mock_check):
        """Test that sitemap titles are properly URL-decoded."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        # Mock sitemap URLs with encoded titles
        mock_iter_urls.return_value = [
            "https://grokipedia.com/page/Mars_%28planet%29",  # Encoded parentheses
            "https://grokipedia.com/page/Earth_%26_Moon",     # Encoded ampersand
        ]

        client = GrokipediaClient()
        sitemap_index = client._load_sitemap_index()

        # Should decode the titles properly
        assert "Mars (planet)" in sitemap_index
        assert "Earth & Moon" in sitemap_index
        assert sitemap_index["Mars (planet)"] == "https://grokipedia.com/page/Mars_%28planet%29"


class TestSitemapParsing:
    """Test sitemap parsing."""

    def test_parse_sitemap_index(self):
        """Test parsing sitemap index XML."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://assets.grokipedia.com/sitemap/sitemap-00001.xml</loc>
    <lastmod>2025-10-27</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://assets.grokipedia.com/sitemap/sitemap-00002.xml</loc>
    <lastmod>2025-10-27</lastmod>
  </sitemap>
</sitemapindex>'''

        urls = parse_sitemap_index(xml)
        expected = [
            "https://assets.grokipedia.com/sitemap/sitemap-00001.xml",
            "https://assets.grokipedia.com/sitemap/sitemap-00002.xml"
        ]
        assert urls == expected

    def test_parse_sitemap_part(self):
        """Test parsing sitemap part XML."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://grokipedia.com/page/Mars</loc>
    <lastmod>2025-10-27</lastmod>
  </url>
  <url>
    <loc>https://grokipedia.com/page/Earth</loc>
    <lastmod>2025-10-27</lastmod>
  </url>
</urlset>'''

        urls = parse_sitemap_part(xml)
        expected = [
            "https://grokipedia.com/page/Mars",
            "https://grokipedia.com/page/Earth"
        ]
        assert urls == expected


class TestArticleParsing:
    """Test article page parsing."""

    def test_parse_article_minimal(self):
        """Test parsing minimal article HTML."""
        html = '''
<!DOCTYPE html>
<html>
<body>
<article>
<h1>Test Article</h1>
<p>This is a test summary.</p>
<h2>First Section</h2>
<p>Section content.</p>
</article>
</body>
</html>
'''
        page = parse_article_page(html, "https://example.com", "https://example.com/page/Test")

        assert page.title == "Test Article"
        assert "test summary" in page.summary.lower()
        assert len(page.sections) == 1
        assert page.sections[0].title == "First Section"
        assert "Section content" in page.sections[0].text

    def test_parse_article_with_infobox(self):
        """Test parsing article with infobox table."""
        html = '''
<!DOCTYPE html>
<html>
<body>
<article>
<h1>Mars</h1>
<p>Mars is a planet.</p>
<table>
<tr><th>Property</th><th>Value</th></tr>
<tr><td>Diameter</td><td>6792 km</td></tr>
<tr><td>Moons</td><td>2</td></tr>
</table>
<h2>Geography</h2>
<p>Mars has volcanoes.</p>
</article>
</body>
</html>
'''
        page = parse_article_page(html, "https://example.com", "https://example.com/page/Mars")

        assert page.title == "Mars"
        assert page.infobox == {"Diameter": "6792 km", "Moons": "2"}
        assert len(page.sections) == 1
        assert page.sections[0].title == "Geography"

    def test_parse_article_with_classed_paragraphs(self):
        """Test parsing article with CSS classes on summary paragraphs."""
        html = '''
<!DOCTYPE html>
<html>
<body>
<article>
<h1>Test Article</h1>
<p class="summary-text">This is a summary with CSS class.</p>
<p class="description">Another summary paragraph.</p>
<h2>First Section</h2>
<p>Section content.</p>
</article>
</body>
</html>
'''
        page = parse_article_page(html, "https://example.com", "https://example.com/page/Test")

        assert page.title == "Test Article"
        # Should include paragraphs even with CSS classes
        assert "summary with css class" in page.summary.lower()
        assert "another summary paragraph" in page.summary.lower()


class TestSearchParsing:  # pylint: disable=too-few-public-methods
    """Test search results parsing."""

    def test_parse_search_results(self):
        """Test parsing search results HTML."""
        html = '''
<!DOCTYPE html>
<html>
<body>
<main>
<div>
<div role="button">
<h3>Mars</h3>
<p>A planet in our solar system.</p>
</div>
<div role="button">
<h3>Mars Rover</h3>
<p>A vehicle that explores Mars.</p>
</div>
</div>
</main>
</body>
</html>
'''
        results = parse_search_results(html, "https://grokipedia.com", "mars")

        assert len(results) == 2
        assert results[0].title == "Mars"
        assert "planet" in results[0].snippet.lower()
        assert results[0].url == "https://grokipedia.com/page/Mars"
        assert results[1].title == "Mars Rover"
        assert results[1].url == "https://grokipedia.com/page/Mars_Rover"


class TestClient:
    """Test client functionality."""

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_client_initialization(self, mock_http_class, _mock_check_robots):
        """Test client initializes with correct parameters."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        client = GrokipediaClient(
            base_url="https://test.com",
            user_agent="test-agent",
            timeout=5.0,
            requests_per_minute=10,
            cache_ttl=60.0,
            enable_api_search=False
        )

        mock_http_class.assert_called_once_with(
            user_agent="test-agent",
            timeout=5.0,
            requests_per_minute=10,
            cache_ttl=60.0,
            max_cache_entries=None
        )

        assert client.base_url == "https://test.com"

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_client_respects_robots(self, mock_http_class, _mock_check):
        """Test client checks robots.txt when respect_robots=True."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        GrokipediaClient(respect_robots=True)

        _mock_check.assert_called_once()

    @patch('grokipedia.client.check_api_disallowed')
    @patch('grokipedia.client.HttpClient')
    def test_client_skips_robots_check(self, mock_http_class, _mock_check):
        """Test client skips robots.txt check when respect_robots=False."""
        mock_http = Mock()
        mock_http_class.return_value = mock_http

        GrokipediaClient(respect_robots=False)

        _mock_check.assert_not_called()
