"""Sitemap parsing and iteration utilities."""

import logging
from typing import Iterator, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from grokipedia.exceptions import ParseError
from grokipedia.http import HttpClient

logger = logging.getLogger(__name__)


def parse_sitemap_index(sitemap_xml: str) -> List[str]:
    """Parse a sitemap index XML and extract individual sitemap URLs.

    Args:
        sitemap_xml: Raw XML content of sitemap index

    Returns:
        List of sitemap URLs

    Raises:
        ParseError: If XML parsing fails
    """
    try:
        soup = BeautifulSoup(sitemap_xml, "xml")
        sitemap_urls = []

        # Find all <loc> elements within <sitemap> elements
        for sitemap in soup.find_all("sitemap"):
            loc = sitemap.find("loc")
            if loc and loc.text:
                sitemap_urls.append(loc.text.strip())

        return sitemap_urls
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise ParseError(f"Failed to parse sitemap index: {e}") from e


def parse_sitemap_part(sitemap_xml: str) -> List[str]:
    """Parse a sitemap part XML and extract article URLs.

    Args:
        sitemap_xml: Raw XML content of sitemap part

    Returns:
        List of article URLs

    Raises:
        ParseError: If XML parsing fails
    """
    try:
        soup = BeautifulSoup(sitemap_xml, "xml")
        urls = []

        # Find all <loc> elements (article URLs)
        for url in soup.find_all("url"):
            loc = url.find("loc")
            if loc and loc.text:
                urls.append(loc.text.strip())

        return urls
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise ParseError(f"Failed to parse sitemap part: {e}") from e


def iter_sitemap_urls(
    base_url: str, http_client: HttpClient, max_urls: Optional[int] = None
) -> Iterator[str]:
    """Iterate through all article URLs from the sitemap.

    Args:
        base_url: Base URL of the site
        http_client: HTTP client to use
        max_urls: Maximum number of URLs to yield (None for all)

    Yields:
        Article URLs

    Raises:
        ParseError: If sitemap parsing fails
    """
    # Fetch the main sitemap index
    sitemap_index_url = urljoin(base_url, "/sitemap.xml")
    try:
        sitemap_index_xml = http_client.get(sitemap_index_url)
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise ParseError(f"Failed to fetch sitemap index: {e}") from e

    # Parse the index to get part URLs
    part_urls = parse_sitemap_index(sitemap_index_xml)

    # Iterate through each part
    urls_yielded = 0
    for part_url in part_urls:
        if max_urls is not None and urls_yielded >= max_urls:
            break

        try:
            part_xml = http_client.get(part_url)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Log warning but continue with other parts
            logger.warning("Failed to fetch sitemap part %s: %s", part_url, e)
            continue

        # Parse the part to get article URLs
        article_urls = parse_sitemap_part(part_xml)

        # Yield URLs from this part
        for url in article_urls:
            if max_urls is not None and urls_yielded >= max_urls:
                return
            yield url
            urls_yielded += 1
