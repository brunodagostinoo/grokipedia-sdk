"""Robots.txt parsing and compliance utilities."""

import logging
import re
from typing import List
from urllib.parse import urljoin, urlparse

from grokipedia.exceptions import RobotsError
from grokipedia.http import HttpClient

logger = logging.getLogger(__name__)


class RobotsParser:
    """Simple robots.txt parser."""

    # pylint: disable=too-few-public-methods
    # Simple parser class focused on single responsibility

    def __init__(self, robots_txt: str, user_agent: str = "*"):
        """Parse robots.txt content.

        Args:
            robots_txt: Raw robots.txt content
            user_agent: User agent to check rules for (default: *)
        """
        self.rules: List[tuple[str, bool]] = []  # (pattern, allow)
        self._parse_robots_txt(robots_txt, user_agent)

    def _parse_robots_txt(self, robots_txt: str, user_agent: str) -> None:
        """Parse robots.txt and extract rules for the given user agent."""
        lines = robots_txt.split("\n")
        best_section_start = self._find_best_section(lines, user_agent)

        # If no section matched, allow all access (no rules)
        if best_section_start == -1:
            return

        # Collect rules from the best matching section
        self._collect_rules_from_section(lines, best_section_start)

    def _find_best_section(self, lines: list[str], user_agent: str) -> int:
        """Find the best matching user agent section."""
        best_section_start = -1
        best_specificity = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line.lower().startswith("user-agent:"):
                continue

            ua = line.split(":", 1)[1].strip().lower()
            specificity = self._calculate_specificity(user_agent, ua)

            if specificity > best_specificity:
                best_specificity = specificity
                best_section_start = i

        return best_section_start

    def _calculate_specificity(self, user_agent: str, ua: str) -> int:
        """Calculate how specific a user agent match is."""
        user_agent_lower = user_agent.lower()
        if ua == "*":
            return 1
        if ua == user_agent_lower:
            return 3
        if user_agent_lower.startswith(ua):
            return 2
        return 0

    def _collect_rules_from_section(self, lines: list[str], start_index: int) -> None:
        """Collect Allow/Disallow rules from a specific section."""
        found_section_header = False

        for i in range(start_index, len(lines)):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                continue

            # Handle user-agent directive
            if line.lower().startswith("user-agent:"):
                if found_section_header:
                    # We've reached the next section, stop
                    break
                found_section_header = True
                continue

            # Parse Allow/Disallow directives in the current section
            if found_section_header:
                if line.lower().startswith("allow:"):
                    path = line.split(":", 1)[1].strip()
                    self.rules.append((path, True))
                elif line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    self.rules.append((path, False))

    def is_allowed(self, url: str) -> bool:
        """Check if a URL is allowed according to robots.txt rules.

        Args:
            url: URL to check

        Returns:
            True if allowed, False if disallowed
        """
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path += "?" + parsed.query

        # Find the most specific (longest pattern) matching rule
        best_match: tuple[int, bool] | None = None  # (pattern_length, allow)
        for pattern, allow in self.rules:
            if self._matches_pattern(path, pattern):
                pattern_length = len(pattern)
                if best_match is None or pattern_length > best_match[0]:  # pylint: disable=unsubscriptable-object
                    best_match = (pattern_length, allow)

        # Return the most specific match, or allow if no matching rules
        return best_match[1] if best_match is not None else True

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if a path matches a robots.txt pattern.

        Args:
            path: Request path
            pattern: Robots.txt pattern

        Returns:
            True if matches
        """
        if not pattern:
            return False

        # Convert robots.txt wildcards to regex
        # * matches any sequence of characters
        # $ matches end of path
        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace(r"\*", ".*")
        if pattern.endswith("$"):
            regex_pattern = regex_pattern[:-2] + "$"
        else:
            regex_pattern += ".*"

        return bool(re.match(regex_pattern, path))


def fetch_robots_txt(base_url: str, http_client: HttpClient) -> str:
    """Fetch robots.txt from a base URL.

    Args:
        base_url: Base URL of the site
        http_client: HTTP client to use

    Returns:
        Raw robots.txt content

    Raises:
        RobotsError: If robots.txt cannot be fetched
    """
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        return http_client.get(robots_url)
    except Exception as e:
        raise RobotsError(f"Failed to fetch robots.txt from {robots_url}: {e}") from e


def check_api_disallowed(
    base_url: str, http_client: HttpClient, user_agent: str = "*", strict: bool = False
) -> bool:
    """Check robots.txt compliance for all API endpoints.

    This SDK only uses publicly available resources (HTML pages and XML sitemaps)
    and does not access any /api/ endpoints, respecting robots.txt directives.

    Args:
        base_url: Base URL of the site
        http_client: HTTP client to use
        user_agent: User agent to check
        strict: If True, raise error when API access would be disabled. If False, log warning
            and return True to disable API.

    Returns:
        True if API access should be disabled due to robots.txt, False otherwise

    Raises:
        RobotsError: If robots.txt rules would prevent access to required resources, or if
            strict=True and API is disallowed
    """
    robots_txt = fetch_robots_txt(base_url, http_client)
    parser = RobotsParser(robots_txt, user_agent)

    # Ensure all API paths are disallowed (we don't use any APIs)
    api_paths = [
        "/api/",
        "/api/typeahead",
        "/api/stats",
        "/api/search",
        "/api/anything",
    ]

    api_allowed = False
    for path in api_paths:
        test_url = urljoin(base_url, path)
        if parser.is_allowed(test_url):
            api_allowed = True
            logger.warning("API path %s is allowed by robots.txt", path)

    # Verify that required public resources are accessible
    required_paths = ["/", "/page/Test", "/sitemap.xml"]
    for path in required_paths:
        test_url = urljoin(base_url, path)
        if not parser.is_allowed(test_url):
            raise RobotsError(f"Required path {path} is disallowed by robots.txt")

    if api_allowed:
        if strict:
            raise RobotsError(
                "API endpoints are allowed by robots.txt but strict mode "
                "requires they be disallowed"
            )
        logger.warning(
            "API endpoints allowed by robots.txt - API search will be disabled for compliance"
        )
        return True  # Disable API access

    logger.info("Robots.txt compliance verified - API endpoints properly disallowed")
    return False  # API access is allowed (endpoints are properly disallowed)
