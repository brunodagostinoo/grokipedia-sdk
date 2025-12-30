"""HTTP client with rate limiting, caching, and retry logic."""

import threading
import time
from collections import OrderedDict
from importlib.metadata import version as get_version
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from grokipedia.exceptions import HttpError, NotFoundError, RateLimitError


class HttpClient:
    """HTTP client with rate limiting, caching, and retry logic."""

    # pylint: disable=too-many-instance-attributes,too-many-arguments
    # HTTP client requires many attributes for comprehensive configuration

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        user_agent: str = "",  # Will be set to default in __init__
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        requests_per_minute: int = 30,
        cache_ttl: Optional[float] = None,  # TTL in seconds, None to disable
        max_cache_entries: Optional[
            int
        ] = None,  # Max cache entries, None for unlimited
    ):
        """Initialize the HTTP client.

        Args:
            user_agent: User-Agent string for requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
            backoff_factor: Backoff factor for retries
            requests_per_minute: Maximum requests per minute
            cache_ttl: Cache TTL in seconds (None to disable caching)
            max_cache_entries: Maximum number of cache entries (None for unlimited)
        """
        # Set default user agent if not provided
        if not user_agent:
            try:
                pkg_version = get_version("grokipedia-sdk")
            except Exception:  # pylint: disable=broad-exception-caught
                pkg_version = "0.2.0"
            user_agent = f"grokipedia-sdk/{pkg_version}"

        self.user_agent = user_agent
        self.timeout = timeout
        self.requests_per_minute = requests_per_minute
        self.cache_ttl = cache_ttl
        self.max_cache_entries = max_cache_entries

        # Rate limiting
        self._last_request_time: float = 0.0
        self._min_interval = 60.0 / requests_per_minute
        self._rate_limit_lock = threading.Lock()

        # Simple in-memory LRU cache: url -> (timestamp, response_text)
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._cache_lock = threading.Lock()

        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=backoff_factor,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def _check_rate_limit(self) -> None:
        """Enforce rate limiting before making a request."""
        with self._rate_limit_lock:
            now = time.time()
            time_since_last = now - self._last_request_time
            if time_since_last < self._min_interval:
                sleep_time = self._min_interval - time_since_last
                time.sleep(sleep_time)

    def _update_rate_limit_time(self) -> None:
        """Update the last request time after completing a request."""
        with self._rate_limit_lock:
            self._last_request_time = time.time()

    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from URL and params."""
        # For simplicity, just use the URL for now
        # Could be extended to include relevant query params
        return url

    def _is_cache_valid(self, cache_entry: tuple[float, str]) -> bool:
        """Check if cache entry is still valid."""
        if self.cache_ttl is None:
            return False
        timestamp, _ = cache_entry
        return time.time() - timestamp < self.cache_ttl

    def get(self, url: str, **kwargs: Any) -> str:
        """Make a GET request with rate limiting and caching.

        Args:
            url: URL to request
            **kwargs: Additional requests parameters

        Returns:
            Response text

        Raises:
            HttpError: On HTTP errors
            RateLimitError: On rate limit violations
        """
        # Check cache first
        cache_key = self._get_cache_key(url)
        with self._cache_lock:
            if cache_key in self._cache and self._is_cache_valid(
                self._cache[cache_key]
            ):
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                _, cached_response = self._cache[cache_key]
                return cached_response

        # Enforce rate limiting
        self._check_rate_limit()

        try:
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()

            # Update rate limit timing after successful request
            self._update_rate_limit_time()

            # Cache the response
            if self.cache_ttl is not None:
                with self._cache_lock:
                    self._cache[cache_key] = (time.time(), response.text)
                    self._cache.move_to_end(cache_key)  # Mark as most recently used

                    # Enforce cache size limit (LRU eviction)
                    if (
                        self.max_cache_entries is not None
                        and len(self._cache) > self.max_cache_entries
                    ):
                        self._cache.popitem(
                            last=False
                        )  # Remove oldest (least recently used)

            return response.text

        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code == 404:
                    raise NotFoundError(f"Not found: {url}") from e
                if e.response.status_code == 429:
                    raise RateLimitError(f"Rate limit exceeded for {url}") from e
                raise HttpError(
                    f"HTTP {e.response.status_code} for {url}: " f"{e.response.text}"
                ) from e
            raise HttpError(f"Request failed for {url}: {str(e)}") from e

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        with self._cache_lock:
            self._cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of valid (non-expired) cached entries."""
        with self._cache_lock:
            if self.cache_ttl is None:
                return len(self._cache)
            now = time.time()
            return sum(
                1
                for timestamp, _ in self._cache.values()
                if now - timestamp < self.cache_ttl
            )

    def close(self) -> None:
        """Close the HTTP session and release resources."""
        self.session.close()

    def __enter__(self) -> "HttpClient":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close session."""
        self.close()
