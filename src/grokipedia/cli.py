"""Command-line interface for Grokipedia SDK."""

import sys

try:
    import click
except ImportError:
    click = None

from grokipedia import GrokipediaClient
from grokipedia.exceptions import GrokipediaError


# Define CLI group conditionally
if click is not None:
    def _format_page_text(page_obj) -> str:
        """Format a page as plain text."""
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

    def _format_page_html(page_obj) -> str:
        """Format a page as HTML."""
        lines = []

        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append(f"<title>{page_obj.title}</title>")
        lines.append("<meta charset='utf-8'>")
        lines.append("</head>")
        lines.append("<body>")

        lines.append(f"<h1>{page_obj.title}</h1>")
        lines.append(f"<p><em>URL: {page_obj.url}</em></p>")

        if page_obj.summary:
            lines.append(f"<p>{page_obj.summary}</p>")

        if page_obj.infobox:
            lines.append("<h2>Properties</h2>")
            lines.append("<dl>")
            for key, value in page_obj.infobox.items():
                lines.append(f"<dt>{key}</dt>")
                lines.append(f"<dd>{value}</dd>")
            lines.append("</dl>")

        for section in page_obj.sections:
            lines.append(f"<h2>{section.title}</h2>")
            lines.append(section.html)

        lines.append("</body>")
        lines.append("</html>")

        return "\n".join(lines)

    @click.group()
    @click.option('--base-url', default='https://grokipedia.com',
                  help='Base URL for Grokipedia')
    @click.option('--user-agent', default='grokipedia-sdk/0.1.0',
                  help='User agent string')
    @click.option('--timeout', default=10.0, type=float,
                  help='Request timeout in seconds')
    @click.option('--rate-limit', default=30, type=int,
                  help='Requests per minute')
    @click.option('--no-cache', is_flag=True,
                  help='Disable HTTP caching')
    @click.option('--enable-api-search', is_flag=True,
                  help='Enable API-based search (uses /api/full-text-search)')
    @click.pass_context
    def cli(ctx, base_url, user_agent, timeout, rate_limit, no_cache, enable_api_search):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Grokipedia SDK command-line interface."""
        ctx.ensure_object(dict)
        ctx.obj['client'] = GrokipediaClient(
            base_url=base_url,
            user_agent=user_agent,
            timeout=timeout,
            requests_per_minute=rate_limit,
            cache_ttl=None if no_cache else 300.0,
            enable_api_search=enable_api_search,
        )

    @cli.command()
    @click.argument('query')
    @click.option('--limit', default=10, type=int,
                  help='Maximum number of results')
    @click.option('--page', default=1, type=int,
                  help='Page number')
    @click.pass_context
    def search(ctx, query, limit, page):
        """Search for articles."""
        client: GrokipediaClient = ctx.obj['client']

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
                    snippet = (result.snippet[:100] + '...'
                              if len(result.snippet) > 100 else result.snippet)
                    click.echo(f"   Summary: {snippet}")
                if result.thumbnail_url:
                    click.echo(f"   Thumbnail: {result.thumbnail_url}")
                click.echo()

        except GrokipediaError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    @cli.command(name='page')
    @click.argument('title')
    @click.option('--output-format', type=click.Choice(['text', 'html']),
                  default='text', help='Output format')
    @click.option('--output', type=click.Path(),
                  help='Output file (default: stdout)')
    @click.pass_context
    def page_cmd(ctx, title, output_format, output):
        """Fetch and display an article page."""
        client: GrokipediaClient = ctx.obj['client']

        try:
            page_obj = client.get_page(title)

            # Generate output
            if output_format == 'html':
                output_content = _format_page_html(page_obj)
            else:
                output_content = _format_page_text(page_obj)

            # Write to file or stdout
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(output_content)
                click.echo(f"Page saved to {output}")
            else:
                click.echo(output_content)

        except GrokipediaError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

else:
    cli = None  # pylint: disable=invalid-name


def main():
    """Main CLI entry point."""
    if click is None or cli is None:
        print("Error: click is required for CLI. Install with: pip install grokipedia-sdk[cli]")
        sys.exit(1)

    cli.main(standalone_mode=False)


if __name__ == '__main__':
    main()
