"""Main Grokipedia client."""

import json
import logging
import time
from importlib.metadata import version as get_version
from typing import Dict, Iterator, List, Optional
from urllib.parse import unquote, urlencode, urljoin

import requests

from grokipedia.exceptions import GrokipediaError, ParseError
from grokipedia.http import HttpClient
from grokipedia.models import Page, SearchResult
from grokipedia.parser import _title_to_slug, parse_article_page
from grokipedia.robots import check_api_disallowed
from grokipedia.sitemap import iter_sitemap_urls

logger = logging.getLogger(__name__)


class GrokipediaClient:
    """Client for accessing Grokipedia content."""

    # pylint: disable=too-many-arguments
    # Complex client initialization requires many parameters for full configuration

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        base_url: str = "https://grokipedia.com",
        respect_robots: bool = True,
        user_agent: str = "",  # Will be set to default in __init__
        timeout: float = 10.0,
        requests_per_minute: int = 30,
        cache_ttl: Optional[float] = 300.0,  # 5 minutes
        max_cache_entries: Optional[
            int
        ] = None,  # Max cache entries, None for unlimited
        enable_api_search: bool = False,  # Feature flag for future official API
        robots_strict: bool = False,  # Strict robots.txt compliance (raise on API allowed)
    ):
        """Initialize the Grokipedia client.

        Args:
            base_url: Base URL of Grokipedia
            respect_robots: Whether to check and respect robots.txt
            user_agent: User agent string
            timeout: Request timeout in seconds
            requests_per_minute: Rate limit
            cache_ttl: Cache TTL in seconds (None to disable)
            max_cache_entries: Maximum number of cache entries (None for unlimited)
            enable_api_search: Enable API-based search (for future official API support)
            robots_strict: Strict robots.txt compliance - raise error if API allowed when
                respect_robots=True
        """
        self.base_url = base_url.rstrip("/")
        self.respect_robots = respect_robots
        self.enable_api_search = enable_api_search
        self.robots_strict = robots_strict

        # Set default user agent if not provided
        if not user_agent:
            try:
                pkg_version = get_version("grokipedia-sdk")
            except Exception:  # pylint: disable=broad-exception-caught
                pkg_version = "0.2.0"
            user_agent = f"grokipedia-sdk/{pkg_version}"

        # Initialize HTTP client
        self.http = HttpClient(
            user_agent=user_agent,
            timeout=timeout,
            requests_per_minute=requests_per_minute,
            cache_ttl=cache_ttl,
            max_cache_entries=max_cache_entries,
        )

        # Cache for sitemap data (title -> url mapping)
        self._sitemap_cache: Optional[Dict[str, str]] = None
        self._sitemap_cache_time: Optional[float] = None
        self._sitemap_cache_ttl = cache_ttl  # Use same TTL as HTTP cache

        # Check robots.txt compliance if requested
        if respect_robots:
            api_disabled = check_api_disallowed(
                self.base_url, self.http, user_agent, robots_strict
            )
            if api_disabled and enable_api_search:
                logger.warning("Disabling API search due to robots.txt compliance")
                self.enable_api_search = False

    def _is_sitemap_cache_valid(self) -> bool:
        """Check if sitemap cache is still valid."""
        if self._sitemap_cache is None or self._sitemap_cache_time is None:
            return False
        if self._sitemap_cache_ttl is None:
            return True  # No TTL means cache forever
        return time.time() - self._sitemap_cache_time < self._sitemap_cache_ttl

    def refresh_sitemap(self) -> None:
        """Force refresh of the sitemap cache."""
        self._sitemap_cache = None
        self._sitemap_cache_time = None

    def _load_sitemap_index(self) -> Dict[str, str]:
        """Load and cache sitemap data for search functionality.

        Returns:
            Dictionary mapping article titles to URLs
        """
        if self._is_sitemap_cache_valid():
            return self._sitemap_cache  # type: ignore[return-value]

        self._sitemap_cache = {}

        try:
            # Load first 1000 URLs from sitemap (reasonable limit for search)
            for url in self.iter_sitemap(max_urls=1000):
                # Extract title from URL: /page/Title -> Title
                if "/page/" in url:
                    title_part = url.split("/page/")[-1]
                    # Decode URL-encoded characters and convert underscores to spaces
                    title = unquote(title_part).replace("_", " ")
                    self._sitemap_cache[title] = url

            self._sitemap_cache_time = time.time()

        except (GrokipediaError, requests.RequestException) as e:
            # Catch known error types to avoid sitemap loading failures breaking search
            logger.warning("Failed to load sitemap for search: %s", e)

        return self._sitemap_cache

    def search(
        self, query: str, page: int = 1, limit: Optional[int] = 10
    ) -> List[SearchResult]:
        """Search for articles on Grokipedia.

        By default, this method searches through available articles from the sitemap
        and performs client-side text matching. It's fully robots.txt compliant
        and only uses publicly available XML sitemaps.

        When enable_api_search=True, it uses the Grokipedia full-text search API
        which provides more comprehensive results with pagination support.

        Args:
            query: Search query
            page: Page number (1-based) - only supported with API search
            limit: Maximum number of results to return

        Returns:
            List of search results
        """
        # Future: if official API is available and enabled
        if self.enable_api_search:
            return self._search_with_api(query, page, limit or 10)

        # Robots.txt compliant search using sitemap
        if page > 1:
            logger.warning(
                "Sitemap search does not support pagination. "
                "Ignoring page=%d parameter.",
                page,
            )

        try:
            sitemap_index = self._load_sitemap_index()
            query_lower = query.lower()

            # Find matching articles
            matches = []
            for title, url in sitemap_index.items():
                if query_lower in title.lower():
                    matches.append((title, url))

            # Sort by relevance (exact matches first, then substring matches)
            matches.sort(
                key=lambda x: (
                    not x[0]
                    .lower()
                    .startswith(query_lower),  # Exact prefix matches first
                    len(x[0]),  # Shorter titles first
                )
            )

            # Convert to SearchResult objects
            results = []
            for title, url in matches[: limit or 10]:
                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        thumbnail_url=None,
                        snippet=None,  # No snippets available from sitemap
                    )
                )

            return results

        except (GrokipediaError, requests.RequestException) as e:
            # Return empty list on known error types - search should be resilient
            logger.warning("Search failed for '%s': %s", query, e)
            return []

    def _search_with_api(
        self, query: str, page: int, limit: int
    ) -> List[SearchResult]:  # pylint: disable=too-many-locals
        """Search using the Grokipedia full-text search API.

        Args:
            query: Search query
            page: Page number (1-based)
            limit: Maximum number of results per page

        Returns:
            List of search results for the specified page
        """
        # Calculate offset from page number (1-based to 0-based)
        offset = (page - 1) * limit

        try:
            # Build API URL with pagination
            params = {"query": query, "limit": limit, "offset": offset}
            api_url = urljoin(
                self.base_url, f"/api/full-text-search?{urlencode(params)}"
            )

            # Make API request
            response_text = self.http.get(api_url)

            # Parse JSON response
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ParseError(f"Failed to parse API response as JSON: {e}") from e

            # Extract results
            api_results = data.get("results", [])
            results = []

            # Convert API results to SearchResult objects
            for api_result in api_results:
                title = api_result.get("title", "")
                slug = api_result.get("slug", "")
                snippet = api_result.get("snippet", "")

                if title and slug:
                    # Build article URL from slug
                    url = urljoin(self.base_url, f"/page/{slug}")

                    # Create SearchResult - API doesn't provide thumbnails
                    search_result = SearchResult(
                        title=title,
                        url=url,
                        thumbnail_url=None,  # API doesn't provide thumbnails
                        snippet=snippet if snippet else None,
                    )
                    results.append(search_result)

        except (GrokipediaError, requests.RequestException) as e:
            # Return empty list on known error types - API search should fail gracefully
            logger.warning("API search failed for '%s' (page %d): %s", query, page, e)
            return []

        return results

    def get_page(self, title_or_url: str) -> Page:
        """Fetch a specific article page.

        Args:
            title_or_url: Article title or full URL

        Returns:
            Parsed Page object

        Raises:
            NotFoundError: If page is not found
        """
        # Determine the URL
        if title_or_url.startswith(("http://", "https://")):
            url = title_or_url
        else:
            # Assume it's a title, convert to URL
            slug = _title_to_slug(title_or_url)
            url = urljoin(self.base_url, f"/page/{slug}")

        html = self.http.get(url)
        return parse_article_page(html, self.base_url, url)

    def iter_sitemap(self, max_urls: Optional[int] = None) -> Iterator[str]:
        """Iterate through article URLs from the sitemap.

        Args:
            max_urls: Maximum number of URLs to yield

        Yields:
            Article URLs
        """
        return iter_sitemap_urls(self.base_url, self.http, max_urls)

    def clear_cache(self) -> None:
        """Clear the HTTP cache."""
        self.http.clear_cache()

    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return self.http.get_cache_size()
