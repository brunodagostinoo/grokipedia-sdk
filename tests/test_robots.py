"""Tests for robots.txt parsing and compliance."""

import logging
from unittest.mock import Mock, patch

import pytest

from grokipedia.exceptions import RobotsError
from grokipedia.http import HttpClient
from grokipedia.robots import RobotsParser, check_api_disallowed, fetch_robots_txt


class TestRobotsParser:
    """Test RobotsParser functionality."""

    def test_parse_robots_txt_allow_disallow(self):
        """Test parsing allow/disallow rules."""
        robots_txt = '''User-agent: *
Disallow: /api/
Allow: /page/
Allow: /

User-agent: test-bot
Disallow: /admin/
'''
        parser = RobotsParser(robots_txt, "*")

        assert parser.is_allowed("https://example.com/page/test") is True
        assert parser.is_allowed("https://example.com/api/search") is False
        assert parser.is_allowed("https://example.com/") is True

    def test_parse_robots_txt_wildcards(self):
        """Test parsing wildcard patterns."""
        robots_txt = '''User-agent: *
Disallow: /*.php$
Allow: /api/search
'''
        parser = RobotsParser(robots_txt, "*")

        assert parser.is_allowed("https://example.com/index.php") is False
        assert parser.is_allowed("https://example.com/index.html") is True
        assert parser.is_allowed("https://example.com/api/search") is True

    def test_parse_robots_txt_user_agent_matching(self):  # pylint: disable=unused-argument
        """Test user agent matching."""
        robots_txt = '''User-agent: *
Disallow: /

User-agent: allowed-bot
Allow: /
'''
        # Default user agent should be blocked
        parser_default = RobotsParser(robots_txt, "*")
        assert parser_default.is_allowed("https://example.com/") is False

        # Specific user agent should be allowed
        parser_allowed = RobotsParser(robots_txt, "allowed-bot")
        assert parser_allowed.is_allowed("https://example.com/") is True

    def test_parse_robots_txt_no_matching_user_agent(self):
        """Test behavior with no matching user agent rules."""
        robots_txt = '''User-agent: specific-bot
Disallow: /secret/
'''
        parser = RobotsParser(robots_txt, "other-bot")

        # No rules apply, should default to allow
        assert parser.is_allowed("https://example.com/secret/") is True
        assert parser.is_allowed("https://example.com/public/") is True

    def test_is_allowed_with_query_params(self):
        """Test URL checking includes query parameters."""
        robots_txt = '''User-agent: *
Disallow: /search
'''
        parser = RobotsParser(robots_txt, "*")

        assert parser.is_allowed("https://example.com/search") is False
        assert parser.is_allowed("https://example.com/search?q=test") is False


class TestFetchRobotsTxt:
    """Test robots.txt fetching."""

    @patch('grokipedia.robots.HttpClient')
    def test_fetch_robots_txt_success(self, mock_http_class):
        """Test successful robots.txt fetch."""
        mock_http = Mock()
        mock_http.get.return_value = "User-agent: *\nDisallow: /api/"
        mock_http_class.return_value = mock_http

        result = fetch_robots_txt("https://example.com", mock_http)

        assert result == "User-agent: *\nDisallow: /api/"
        mock_http.get.assert_called_once_with("https://example.com/robots.txt")

    @patch('grokipedia.robots.HttpClient')
    def test_fetch_robots_txt_failure(self, mock_http_class):
        """Test robots.txt fetch failure raises RobotsError."""
        mock_http = Mock()
        mock_http.get.side_effect = Exception("Connection failed")
        mock_http_class.return_value = mock_http

        with pytest.raises(RobotsError, match="Failed to fetch robots.txt"):
            fetch_robots_txt("https://example.com", mock_http)


class TestCheckApiDisallowed:
    """Test API compliance checking."""

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_allows_required_paths(self, mock_fetch):
        """Test that required public paths are allowed."""
        mock_fetch.return_value = '''User-agent: *
Allow: /
Allow: /page/
Allow: /sitemap.xml
Disallow: /api/
'''

        # Should not raise any exceptions
        check_api_disallowed("https://example.com", Mock(spec=HttpClient))

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_blocks_required_paths(self, mock_fetch):
        """Test that blocking required paths raises RobotsError."""
        mock_fetch.return_value = '''User-agent: *
Disallow: /
'''

        with pytest.raises(RobotsError, match="Required path / is disallowed"):
            check_api_disallowed("https://example.com", Mock(spec=HttpClient))

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_allows_api_paths(self, mock_fetch, caplog):
        """Test warning when API paths are allowed."""
        mock_fetch.return_value = '''User-agent: *
    Allow: /api/
    Allow: /
    '''

        check_api_disallowed("https://example.com", Mock(spec=HttpClient))

        assert "API path /api/ is allowed by robots.txt" in caplog.text

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_success_message(self, mock_fetch, caplog):
        """Test success message on compliant robots.txt."""
        caplog.set_level(logging.INFO)  # Capture INFO level logs
        mock_fetch.return_value = '''User-agent: *
Disallow: /api/
Allow: /
'''

        check_api_disallowed("https://example.com", Mock(spec=HttpClient))

        assert "Robots.txt compliance verified" in caplog.text

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_strict_mode_allows_api(self, mock_fetch):
        """Test strict mode raises error when API is allowed."""
        mock_fetch.return_value = '''User-agent: *
Allow: /api/
Allow: /
'''

        with pytest.raises(RobotsError, match="API endpoints are allowed"):
            check_api_disallowed("https://example.com", Mock(spec=HttpClient), strict=True)

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_non_strict_returns_true(self, mock_fetch, caplog):
        """Test non-strict mode returns True when API is allowed."""
        mock_fetch.return_value = '''User-agent: *
Allow: /api/
Allow: /
'''

        result = check_api_disallowed("https://example.com", Mock(spec=HttpClient), strict=False)

        assert result is True
        assert "API search will be disabled" in caplog.text

    @patch('grokipedia.robots.fetch_robots_txt')
    def test_check_api_disallowed_disallowed_returns_false(self, mock_fetch):
        """Test returns False when API is properly disallowed."""
        mock_fetch.return_value = '''User-agent: *
Disallow: /api/
Allow: /
'''

        result = check_api_disallowed("https://example.com", Mock(spec=HttpClient))

        assert result is False
