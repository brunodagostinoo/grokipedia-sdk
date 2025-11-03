"""Live integration tests for page fetching functionality."""

import pytest

from grokipedia import GrokipediaClient
from grokipedia.models import Page, Section


@pytest.mark.live
class TestLivePageFetching:
    """Test page fetching against real Grokipedia site."""

    def test_fetch_existing_page(self):
        """Test fetching a known existing page."""
        client = GrokipediaClient(respect_robots=False)

        page = client.get_page("Mars")

        assert isinstance(page, Page)
        assert page.title.lower() == "mars"
        assert page.url == "https://grokipedia.com/page/Mars"
        assert isinstance(page.summary, str)  # Should have a summary (may be empty)
        assert len(page.sections) > 0  # Should have sections

        # Check that sections have proper structure
        for section in page.sections:
            assert section.title
            assert section.html or section.text

    def test_fetch_page_with_infobox(self):
        """Test fetching a page that should have an infobox."""
        client = GrokipediaClient(respect_robots=False)

        page = client.get_page("Earth")

        assert isinstance(page, Page)
        assert page.title.lower() == "earth"
        # May or may not have infobox depending on the page content
        if page.infobox:
            assert isinstance(page.infobox, dict)

    def test_fetch_page_by_url(self):
        """Test fetching a page by full URL."""
        client = GrokipediaClient(respect_robots=False)

        page = client.get_page("https://grokipedia.com/page/Mars")

        assert isinstance(page, Page)
        assert page.title.lower() == "mars"
        assert page.url == "https://grokipedia.com/page/Mars"

    def test_fetch_nonexistent_page(self):
        """Test fetching a page that doesn't exist."""
        client = GrokipediaClient(respect_robots=False)

        with pytest.raises(Exception):  # Should raise NotFoundError or similar
            client.get_page("ThisPageDoesNotExist12345")

    def test_page_structure_validation(self):
        """Test that fetched pages have valid structure."""
        client = GrokipediaClient(respect_robots=False)

        page = client.get_page("Mars")

        # Validate page structure
        assert page.title
        assert page.url.startswith("https://grokipedia.com/")
        assert isinstance(page.summary, str)
        assert isinstance(page.sections, list)

        # Validate sections
        for section in page.sections:
            assert isinstance(section, Section)
            assert section.title
            assert isinstance(section.html, str)
            assert isinstance(section.text, str)

        # Validate infobox if present
        if page.infobox:
            assert isinstance(page.infobox, dict)
            for key, value in page.infobox.items():
                assert isinstance(key, str)
                assert isinstance(value, str)

    def test_sitemap_iteration(self):
        """Test sitemap URL iteration."""
        client = GrokipediaClient(respect_robots=False)

        urls = list(client.iter_sitemap(max_urls=10))

        assert len(urls) > 0
        assert all(url.startswith("https://grokipedia.com/page/") for url in urls)
        assert len(urls) <= 10  # Should respect max_urls
