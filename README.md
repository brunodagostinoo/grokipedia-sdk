# Grokipedia SDK

A read-only Python SDK for [Grokipedia](https://grokipedia.com), an AI-generated online encyclopedia developed by xAI.

**Status**: ✅ **Fully functional and tested** - All features working with comprehensive test coverage (12/12 tests passing)

## Features

- **Search**: Find articles by query with pagination support
- **Fetch Pages**: Retrieve full article content with structured sections
- **Sitemap Access**: Iterate through all available article URLs
- **Rate Limiting**: Polite HTTP requests respecting rate limits
- **Caching**: Optional in-memory caching for repeated requests

## Installation

```bash
pip install grokipedia-sdk
```

Or for development:

```bash
git clone https://github.com/yourusername/grokipedia-sdk.git
cd grokipedia-sdk
pip install -e ".[dev,cli]"
```

## Quick Start

```python
from grokipedia import GrokipediaClient

# Create a client (robots.txt compliant by default)
client = GrokipediaClient()

# Search for articles
# Option 1: API search (requires enable_api_search=True and robots.txt compliance)
client = GrokipediaClient(enable_api_search=True)  # Enable API search for full results
results = client.search("elon musk", limit=5)  # Full-text search with pagination
for result in results:
    print(f"{result.title}: {result.snippet[:100] if result.snippet else 'No snippet'}...")

# Option 2: Sitemap-based search (default, limited to indexed articles)
client_default = GrokipediaClient()  # enable_api_search=False by default
results = client_default.search("example", limit=5)
for result in results:
    print(f"{result.title}: {result.url}")

# Get a full article by title or URL
page = client.get_page("Mars")  # Direct page access always works
print(f"Title: {page.title}")
print(f"Summary: {page.summary[:200] if page.summary else 'No summary'}...")
print(f"Sections: {len(page.sections)}")
```

## CLI Usage

Search for articles (sitemap-based by default):
```bash
grokipedia search "example" --limit 10
```

Search with API (requires robots.txt compliance):
```bash
grokipedia --enable-api-search search "elon musk" --limit 10 --page 2
```

Fetch a specific page:
```bash
grokipedia page "Mars" --format html > mars.html
grokipedia page "Mars" --format text > mars.txt
```

## Compliance

This SDK is compliant with Grokipedia's `robots.txt` and uses publicly available resources:

- **Default behavior**: Does not access `/api/*` endpoints (disallowed by robots.txt)
- **HTML pages**: Parses article content from public `/page/*` URLs
- **XML sitemaps**: Uses sitemap data for default search functionality
- **API search option**: When `enable_api_search=True`, uses the `/api/full-text-search` endpoint for enhanced search capabilities

Search functionality supports two modes:
- **Sitemap search** (default): Scans article titles from XML sitemaps, performs client-side text matching. Limited to currently indexed articles but fully robots.txt compliant.
- **API search**: Uses Grokipedia's full-text search API (`/api/full-text-search`) for comprehensive results with pagination support.

**Robots.txt Interaction**: When `respect_robots=True` (default) and `enable_api_search=True`, the SDK checks if API endpoints are allowed by robots.txt. If APIs are disallowed, API search is automatically disabled with a warning. Set `robots_strict=True` to raise an error instead of auto-disabling.

## Requirements

- Python 3.10+
- `requests` for HTTP requests
- `beautifulsoup4` for HTML parsing

## License

MIT License - see LICENSE file for details.
