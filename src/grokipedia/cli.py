"""Command-line interface for Grokipedia SDK."""

import html
import sys
from importlib.metadata import version
from typing import Optional

try:
    import click

    HAS_CLICK = True
except ImportError:
    click = None  # type: ignore[assignment]
    HAS_CLICK = False

from grokipedia import GrokipediaClient
from grokipedia.exceptions import GrokipediaError
from grokipedia.models import Page

# Get version dynamically
try:
    __version__ = version("grokipedia-sdk")
except Exception:  # pylint: disable=broad-exception-caught
    __version__ = "0.1.1"  # Fallback for development


# Define CLI group conditionally
if HAS_CLICK and click is not None:

    def _format_page_text(page_obj: Page) -> str:
        """Format a page as plain text (Markdown-style)."""
        lines = []

        lines.append(f"# {page_obj.title}")
        lines.append(f"URL: {page_obj.url}")
        lines.append("")

        if page_obj.summary:
            lines.append(page_obj.summary)
            lines.append("")

        if page_obj.infobox:
            lines.append("## Properties")
            for key, value in page_obj.infobox.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        for section in page_obj.sections:
            lines.append(f"## {section.title}")
            lines.append(section.text)
            lines.append("")

        return "\n".join(lines)

    def _format_page_html(page_obj: Page) -> str:
        """Format a page as HTML."""
        lines = []

        # Escape all user-controlled content to prevent XSS
        title = html.escape(page_obj.title)
        url = html.escape(page_obj.url)

        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append(f"<title>{title}</title>")
        lines.append("<meta charset='utf-8'>")
        lines.append("</head>")
        lines.append("<body>")

        lines.append(f"<h1>{title}</h1>")
        lines.append(f"<p><em>URL: {url}</em></p>")

        if page_obj.summary:
            lines.append(f"<p>{html.escape(page_obj.summary)}</p>")

        if page_obj.infobox:
            lines.append("<h2>Properties</h2>")
            lines.append("<dl>")
            for key, value in page_obj.infobox.items():
                # Ensure values are strings before escaping
                lines.append(f"<dt>{html.escape(str(key))}</dt>")
                lines.append(f"<dd>{html.escape(str(value))}</dd>")
            lines.append("</dl>")

        for section in page_obj.sections:
            lines.append(f"<h2>{html.escape(section.title)}</h2>")
            # section.html is already HTML from the source, keep as-is
            # Note: This is trusted content from Grokipedia's API
            lines.append(section.html)

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    @click.group()
    @click.version_option(version=__version__, prog_name="grokipedia")
    @click.option(
        "--base-url", default="https://grokipedia.com", help="Base URL for Grokipedia"
    )
    @click.option(
        "--user-agent",
        default=f"grokipedia-sdk/{__version__}",
        help="User agent string",
    )
    @click.option(
        "--timeout",
        default=10.0,
        type=click.FloatRange(min=0.1, max=300.0),
        help="Request timeout in seconds (0.1-300)",
    )
    @click.option(
        "--rate-limit",
        default=30,
        type=click.IntRange(min=1, max=120),
        help="Requests per minute (1-120)",
    )
    @click.option("--no-cache", is_flag=True, help="Disable HTTP caching")
    @click.option(
        "--enable-api-search",
        is_flag=True,
        help="Enable API-based search (uses /api/full-text-search)",
    )
    @click.pass_context
    def cli(
        ctx: click.Context,
        base_url: str,
        user_agent: str,
        timeout: float,
        rate_limit: int,
        no_cache: bool,
        enable_api_search: bool,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Grokipedia SDK command-line interface."""
        ctx.ensure_object(dict)
        ctx.obj["client"] = GrokipediaClient(
            base_url=base_url,
            user_agent=user_agent,
            timeout=timeout,
            requests_per_minute=rate_limit,
            cache_ttl=None if no_cache else 300.0,
            enable_api_search=enable_api_search,
        )

    @cli.command()
    @click.argument("query")
    @click.option(
        "--limit",
        default=10,
        type=click.IntRange(min=1, max=100),
        help="Maximum number of results (1-100)",
    )
    @click.option(
        "--page",
        default=1,
        type=click.IntRange(min=1),
        help="Page number (starts at 1)",
    )
    @click.pass_context
    def search(ctx: click.Context, query: str, limit: int, page: int) -> None:
        """Search for articles."""
        client: GrokipediaClient = ctx.obj["client"]

        try:
            results = client.search(query, page=page, limit=limit)

            if not results:
                click.echo(f"No results found for '{query}'")
                return

            click.echo(f"Search results for '{query}' (page {page}):")
            click.echo()

            for i, result in enumerate(results, 1):
                click.echo(f"{i}. {result.title}")
                click.echo(f"   URL: {result.url}")
                if result.snippet:
                    # Truncate snippet if too long
                    snippet = (
                        result.snippet[:100] + "..."
                        if len(result.snippet) > 100
                        else result.snippet
                    )
                    click.echo(f"   Summary: {snippet}")
                if result.thumbnail_url:
                    click.echo(f"   Thumbnail: {result.thumbnail_url}")
                click.echo()

        except GrokipediaError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:  # pylint: disable=broad-exception-caught
            click.echo(f"Unexpected error: {e}", err=True)
            sys.exit(2)

    @cli.command(name="page")
    @click.argument("title")
    @click.option(
        "--output-format",
        type=click.Choice(["text", "html"]),
        default="text",
        help="Output format",
    )
    @click.option("--output", type=click.Path(), help="Output file (default: stdout)")
    @click.pass_context
    def page_cmd(
        ctx: click.Context, title: str, output_format: str, output: Optional[str]
    ) -> None:
        """Fetch and display an article page."""
        client: GrokipediaClient = ctx.obj["client"]

        try:
            page_obj = client.get_page(title)

            # Generate output
            if output_format == "html":
                output_content = _format_page_html(page_obj)
            else:
                output_content = _format_page_text(page_obj)

            # Write to file or stdout
            if output:
                try:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(output_content)
                    click.echo(f"Page saved to {output}")
                except OSError as e:
                    click.echo(f"Error writing to {output}: {e}", err=True)
                    sys.exit(1)
            else:
                click.echo(output_content)

        except GrokipediaError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:  # pylint: disable=broad-exception-caught
            click.echo(f"Unexpected error: {e}", err=True)
            sys.exit(2)

else:
    cli = None  # type: ignore[assignment]  # pylint: disable=invalid-name


def main() -> None:
    """Main CLI entry point."""
    if not HAS_CLICK or click is None or cli is None:
        print(
            "Error: click is required for CLI. "
            "Install with: pip install grokipedia-sdk[cli]"
        )
        sys.exit(1)

    try:
        cli.main(standalone_mode=True)
    except SystemExit:  # pylint: disable=try-except-raise
        raise
    except Exception as e:  # pylint: disable=broad-exception-caught
        click.echo(f"Fatal error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
