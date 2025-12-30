"""Tests for CLI functionality."""

import os
from unittest.mock import Mock, patch

import pytest

pytest.importorskip("click")
from click.testing import CliRunner

from grokipedia.cli import cli, __version__
from grokipedia.exceptions import GrokipediaError
from grokipedia.models import Page, SearchResult, Section


class TestCliSearch:
    """Test CLI search command."""

    @patch('grokipedia.cli.GrokipediaClient')
    def test_search_command_success(self, mock_client_class):
        """Test successful search command."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_results = [
            SearchResult(
                title="Mars",
                url="https://grokipedia.com/page/Mars",
                snippet="A planet in our solar system",
                thumbnail_url=None,
            ),
            SearchResult(
                title="Earth",
                url="https://grokipedia.com/page/Earth",
                snippet="Our home planet",
                thumbnail_url="https://example.com/thumb.jpg",
            ),
        ]
        mock_client.search.return_value = mock_results

        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'mars', '--limit', '5'])

        assert result.exit_code == 0
        assert "Search results for 'mars'" in result.output
        assert "Mars" in result.output
        assert "Earth" in result.output
        assert "A planet in our solar system" in result.output
        assert "Our home planet" in result.output
        assert "https://grokipedia.com/page/Mars" in result.output
        assert "Thumbnail: https://example.com/thumb.jpg" in result.output

        mock_client.search.assert_called_once_with('mars', page=1, limit=5)

    @patch('grokipedia.cli.GrokipediaClient')
    def test_search_command_no_results(self, mock_client_class):
        """Test search command with no results."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'nonexistent'])

        assert result.exit_code == 0
        assert "No results found for 'nonexistent'" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_search_command_grokipedia_error(self, mock_client_class):
        """Test search command handles GrokipediaError with exit code 1."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.side_effect = GrokipediaError("Search failed")

        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test'])

        assert result.exit_code == 1
        assert "Error: Search failed" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_search_command_unexpected_error(self, mock_client_class):
        """Test search command handles unexpected errors with exit code 2."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.side_effect = RuntimeError("Unexpected failure")

        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test'])

        assert result.exit_code == 2
        assert "Unexpected error: Unexpected failure" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_search_command_with_page(self, mock_client_class):
        """Test search command with page parameter."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test', '--page', '2'])

        assert result.exit_code == 0
        mock_client.search.assert_called_once_with('test', page=2, limit=10)


class TestCliPage:
    """Test CLI page command."""

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_text_format(self, mock_client_class):
        """Test page command with text format."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Test Article",
            url="https://grokipedia.com/page/Test_Article",
            summary="This is a summary",
            sections=[
                Section(title="Section 1", html="<p>Content</p>", text="Content"),
                Section(title="Section 2", html="<p>More content</p>", text="More content"),
            ],
            infobox={"Key": "Value", "Another": "Data"},
        )
        mock_client.get_page.return_value = mock_page

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test Article', '--output-format', 'text'])

        assert result.exit_code == 0
        assert "# Test Article" in result.output
        assert "URL: https://grokipedia.com/page/Test_Article" in result.output
        assert "This is a summary" in result.output
        assert "- **Key**: Value" in result.output  # Infobox
        assert "## Section 1" in result.output
        assert "Content" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_html_format(self, mock_client_class):
        """Test page command with HTML format."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Test Article",
            url="https://grokipedia.com/page/Test_Article",
            summary="Summary text",
            sections=[Section(title="Section", html="<p>HTML content</p>", text="Text content")],
            infobox={"Property": "Value"},
        )
        mock_client.get_page.return_value = mock_page

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test Article', '--output-format', 'html'])

        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output
        assert "<title>Test Article</title>" in result.output
        assert "<h1>Test Article</h1>" in result.output
        assert "<p>Summary text</p>" in result.output
        assert "<h2>Properties</h2>" in result.output
        assert "<h2>Section</h2>" in result.output
        assert "<p>HTML content</p>" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_output_to_file(self, mock_client_class, tmp_path):
        """Test page command output to file."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Test",
            url="https://example.com/page/Test",
            summary="Summary",
            sections=[],
        )
        mock_client.get_page.return_value = mock_page

        output_file = tmp_path / "output.txt"
        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test', '--output', str(output_file)])

        assert result.exit_code == 0
        assert "Page saved to" in result.output
        assert output_file.exists()

        content = output_file.read_text()
        assert "# Test" in content

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_grokipedia_error(self, mock_client_class):
        """Test page command handles GrokipediaError with exit code 1."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_page.side_effect = GrokipediaError("Page not found")

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'NonExistent'])

        assert result.exit_code == 1
        assert "Error: Page not found" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_unexpected_error(self, mock_client_class):
        """Test page command handles unexpected errors with exit code 2."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_page.side_effect = RuntimeError("Unexpected failure")

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'NonExistent'])

        assert result.exit_code == 2
        assert "Unexpected error: Unexpected failure" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_default_format(self, mock_client_class):
        """Test page command defaults to text format."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Test",
            url="https://example.com/page/Test",
            summary="Summary",
            sections=[],
        )
        mock_client.get_page.return_value = mock_page

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test'])

        assert result.exit_code == 0
        assert "# Test" in result.output  # Text format marker

    @patch('grokipedia.cli.GrokipediaClient')
    def test_page_command_file_write_error(self, mock_client_class, tmp_path):
        """Test page command handles file write errors gracefully."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Test",
            url="https://example.com/page/Test",
            summary="Summary",
            sections=[],
        )
        mock_client.get_page.return_value = mock_page

        # Create a directory where we try to write a file (will fail)
        bad_path = tmp_path / "readonly_dir"
        bad_path.mkdir()
        os.chmod(bad_path, 0o444)  # Read-only

        try:
            output_file = bad_path / "output.txt"
            runner = CliRunner()
            result = runner.invoke(cli, ['page', 'Test', '--output', str(output_file)])

            assert result.exit_code == 1
            assert "Error writing to" in result.output
        finally:
            os.chmod(bad_path, 0o755)  # Restore permissions for cleanup


class TestCliOptions:
    """Test CLI option handling."""

    @patch('grokipedia.cli.GrokipediaClient')
    def test_cli_base_url_option(self, mock_client_class):
        """Test base URL option is passed to client."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, [
            '--base-url', 'https://custom.com',
            'search', 'test'
        ])

        assert result.exit_code == 0
        mock_client_class.assert_called_once_with(
            base_url='https://custom.com',
            user_agent=f'grokipedia-sdk/{__version__}',
            timeout=10.0,
            requests_per_minute=30,
            cache_ttl=300.0,
            enable_api_search=False,
        )

    @patch('grokipedia.cli.GrokipediaClient')
    def test_cli_user_agent_option(self, mock_client_class):
        """Test user agent option."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, [
            '--user-agent', 'custom-agent',
            'search', 'test'
        ])

        assert result.exit_code == 0
        mock_client_class.assert_called_once_with(
            base_url='https://grokipedia.com',
            user_agent='custom-agent',
            timeout=10.0,
            requests_per_minute=30,
            cache_ttl=300.0,
            enable_api_search=False,
        )

    @patch('grokipedia.cli.GrokipediaClient')
    def test_cli_no_cache_option(self, mock_client_class):
        """Test no-cache option disables caching."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, [
            '--no-cache',
            'search', 'test'
        ])

        assert result.exit_code == 0
        mock_client_class.assert_called_once_with(
            base_url='https://grokipedia.com',
            user_agent=f'grokipedia-sdk/{__version__}',
            timeout=10.0,
            requests_per_minute=30,
            cache_ttl=None,
            enable_api_search=False,
        )

    @patch('grokipedia.cli.GrokipediaClient')
    def test_cli_enable_api_search_option(self, mock_client_class):
        """Test --enable-api-search option."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, [
            '--enable-api-search',
            'search', 'test'
        ])

        assert result.exit_code == 0
        mock_client_class.assert_called_once_with(
            base_url='https://grokipedia.com',
            user_agent=f'grokipedia-sdk/{__version__}',
            timeout=10.0,
            requests_per_minute=30,
            cache_ttl=300.0,
            enable_api_search=True,
        )


class TestCliInputValidation:
    """Test CLI input validation."""

    def test_invalid_timeout_negative(self):
        """Test that negative timeout is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--timeout', '-1', 'search', 'test'])

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "Error" in result.output

    def test_invalid_timeout_too_large(self):
        """Test that timeout > 300 is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--timeout', '500', 'search', 'test'])

        assert result.exit_code != 0

    def test_invalid_rate_limit_zero(self):
        """Test that zero rate limit is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--rate-limit', '0', 'search', 'test'])

        assert result.exit_code != 0

    def test_invalid_limit_zero(self):
        """Test that zero limit is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test', '--limit', '0'])

        assert result.exit_code != 0

    def test_invalid_limit_negative(self):
        """Test that negative limit is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test', '--limit', '-5'])

        assert result.exit_code != 0

    def test_invalid_page_zero(self):
        """Test that page 0 is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test', '--page', '0'])

        assert result.exit_code != 0

    def test_invalid_page_negative(self):
        """Test that negative page is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test', '--page', '-1'])

        assert result.exit_code != 0


class TestCliHtmlEscaping:
    """Test HTML output escaping for XSS prevention."""

    @patch('grokipedia.cli.GrokipediaClient')
    def test_html_escapes_xss_in_title(self, mock_client_class):
        """Test that XSS payloads in title are escaped."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="<script>alert('xss')</script>",
            url="https://example.com/page/Test",
            summary="Safe summary",
            sections=[],
        )
        mock_client.get_page.return_value = mock_page

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test', '--output-format', 'html'])

        assert result.exit_code == 0
        assert "<script>" not in result.output
        assert "&lt;script&gt;" in result.output

    @patch('grokipedia.cli.GrokipediaClient')
    def test_html_escapes_xss_in_summary(self, mock_client_class):
        """Test that XSS payloads in summary are escaped."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Safe Title",
            url="https://example.com/page/Test",
            summary="<img src=x onerror=alert('xss')>",
            sections=[],
        )
        mock_client.get_page.return_value = mock_page

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test', '--output-format', 'html'])

        assert result.exit_code == 0
        # html.escape converts < to &lt; which prevents the tag from being parsed
        assert "<img src=x" not in result.output  # Raw tag should not appear
        assert "&lt;img" in result.output  # Escaped version should appear

    @patch('grokipedia.cli.GrokipediaClient')
    def test_html_escapes_xss_in_infobox(self, mock_client_class):
        """Test that XSS payloads in infobox are escaped."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_page = Page(
            title="Safe Title",
            url="https://example.com/page/Test",
            summary="Safe summary",
            sections=[],
            infobox={"<script>bad</script>": "<script>worse</script>"},
        )
        mock_client.get_page.return_value = mock_page

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'Test', '--output-format', 'html'])

        assert result.exit_code == 0
        assert "<script>bad</script>" not in result.output
        assert "&lt;script&gt;" in result.output


class TestCliVersion:
    """Test CLI version flag."""

    def test_version_flag(self):
        """Test --version displays version."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])

        assert result.exit_code == 0
        assert "grokipedia" in result.output
        assert __version__ in result.output
