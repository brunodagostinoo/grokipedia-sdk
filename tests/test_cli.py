"""Tests for CLI functionality."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from grokipedia.cli import cli
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
    def test_search_command_error(self, mock_client_class):
        """Test search command error handling."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.search.side_effect = Exception("Search failed")

        runner = CliRunner()
        result = runner.invoke(cli, ['search', 'test'])

        assert result.exit_code == 1
        # Error messages may be in output or exception
        assert "Search failed" in result.output or "Search failed" in str(result.exception)

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
    def test_page_command_error(self, mock_client_class):
        """Test page command error handling."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_page.side_effect = Exception("Page not found")

        runner = CliRunner()
        result = runner.invoke(cli, ['page', 'NonExistent'])

        assert result.exit_code == 1
        # Error messages may be in output or exception
        assert "Page not found" in result.output or "Page not found" in str(result.exception)

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
            user_agent='grokipedia-sdk/0.1.0',
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
            user_agent='grokipedia-sdk/0.1.0',
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
            user_agent='grokipedia-sdk/0.1.0',
            timeout=10.0,
            requests_per_minute=30,
            cache_ttl=300.0,
            enable_api_search=True,
        )
