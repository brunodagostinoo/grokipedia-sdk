"""Shared fixtures and helpers for Grokipedia SDK tests."""

from unittest.mock import Mock

import pytest

from grokipedia.http import HttpClient


@pytest.fixture
def sample_article_html():
    """Sample HTML for article parsing tests."""
    return '''
<!DOCTYPE html>
<html>
<body>
<article>
<h1>Test Article</h1>
<p>This is a test summary with some content.</p>
<h2>First Section</h2>
<p>Section content here.</p>
<h2>Second Section</h2>
<p>More section content.</p>
</article>
</body>
</html>
'''


@pytest.fixture
def sample_article_with_infobox_html():
    """Sample HTML with infobox table."""
    return '''
<!DOCTYPE html>
<html>
<body>
<article>
<h1>Mars</h1>
<p>Mars is a planet in our solar system.</p>
<table>
<tr><th>Property</th><th>Value</th></tr>
<tr><td>Diameter</td><td>6792 km</td></tr>
<tr><td>Moons</td><td>2</td></tr>
</table>
<h2>Geography</h2>
<p>Mars has volcanoes and craters.</p>
</article>
</body>
</html>
'''


@pytest.fixture
def sample_search_html():
    """Sample HTML for search results parsing."""
    return '''
<!DOCTYPE html>
<html>
<body>
<main>
<div>
<div role="button">
<h3>Mars</h3>
<p>A planet in our solar system with red soil.</p>
</div>
<div role="button">
<h3>Mars Rover</h3>
<p>A robotic vehicle exploring the surface of Mars.</p>
</div>
</div>
</main>
</body>
</html>
'''


@pytest.fixture
def sitemap_index_xml():
    """Sample sitemap index XML."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
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


@pytest.fixture
def sitemap_part_xml():
    """Sample sitemap part XML."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
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


@pytest.fixture
def robots_txt_allow_api_disallow():
    """Sample robots.txt that disallows API but allows public pages."""
    return '''User-agent: *
Disallow: /api/
Allow: /
Allow: /page/
Allow: /sitemap.xml

User-agent: grokipedia-sdk/0.1.0
Disallow: /api/
Allow: /
'''


@pytest.fixture
def robots_txt_block_public():
    """Sample robots.txt that blocks required public resources."""
    return '''User-agent: *
Disallow: /
'''


@pytest.fixture
def mock_http_get():
    """Helper to create a mock HttpClient.get method."""
    def _mock_get(url, **_kwargs):
        # Create a mock that returns different responses based on URL
        mock = Mock()
        if 'robots.txt' in url:
            mock.return_value = '''User-agent: *
Disallow: /api/
Allow: /
'''
        elif 'sitemap.xml' in url:
            mock.return_value = '''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://assets.grokipedia.com/sitemap/sitemap-00001.xml</loc>
  </sitemap>
</sitemapindex>'''
        elif 'sitemap-00001.xml' in url:
            mock.return_value = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://grokipedia.com/page/Mars</loc></url>
  <url><loc>https://grokipedia.com/page/Earth</loc></url>
</urlset>'''
        elif '/page/' in url:
            mock.return_value = '''
<!DOCTYPE html>
<html>
<body>
<article>
<h1>Test Page</h1>
<p>Summary content.</p>
<h2>Section</h2>
<p>Section text.</p>
</article>
</body>
</html>
'''
        elif '/api/full-text-search' in url:
            mock.return_value = '''[
{"title": "Mars", "slug": "Mars", "snippet": "A planet"},
{"title": "Earth", "slug": "Earth", "snippet": "Our home planet"}
]'''
        return mock
    return _mock_get


@pytest.fixture
def mock_http_client(get_mock):
    """Mock HttpClient instance."""
    client = Mock(spec=HttpClient)
    client.get = get_mock()
    client.clear_cache = Mock()
    client.get_cache_size = Mock(return_value=0)
    return client
