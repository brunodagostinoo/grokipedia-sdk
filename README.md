[![PyPI version](https://img.shields.io/pypi/v/grokipedia-sdk)](https://pypi.org/project/grokipedia-sdk/)
[![Python versions](https://img.shields.io/pypi/pyversions/grokipedia-sdk)](https://pypi.org/project/grokipedia-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/brunodagostinoo/grokipedia-sdk/actions/workflows/python-package.yml/badge.svg)](https://github.com/brunodagostinoo/grokipedia-sdk/actions/workflows/python-package.yml)

# Grokipedia SDK

A read-only Python SDK for [Grokipedia](https://grokipedia.com), an AI-generated online encyclopedia developed by xAI.

**Status**: ✅ **Fully functional and tested** - All features working with comprehensive test coverage

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Configuration](#configuration)
- [Caching & Rate Limiting](#caching--rate-limiting)
- [API Reference](#api-reference)
  - [Client](#client)
  - [Models](#models)
  - [Exceptions](#exceptions)
- [Compliance](#compliance)
- [Development](#development)
- [License](#license)

## Features

- **Dual Search Modes**: Sitemap-based search (default, robots.txt compliant) or API search with full-text pagination
- **Page Fetching**: Retrieve complete article content with structured sections, summaries, and infoboxes
- **Sitemap Access**: Iterate through all available article URLs for bulk operations
- **Rate Limiting**: Built-in rate limiting (30 requests/minute) with automatic retries
- **Caching**: Optional in-memory LRU cache with TTL support for improved performance
- **CLI Tools**: Command-line interface for searching and fetching articles

## Installation

Install the base package:

```bash
pip install grokipedia-sdk
```

For development with CLI tools:

```bash
pip install grokipedia-sdk[cli]
```

For development with testing and linting tools:

```bash
pip install grokipedia-sdk[dev]
```

Or install from source for development:

```bash
git clone https://github.com/brunodagostinoo/grokipedia-sdk.git
cd grokipedia-sdk
pip install -e ".[dev,cli]"
```

## Quick Start

```python
from grokipedia import GrokipediaClient

# Create a client (robots.txt compliant by default)
client = GrokipediaClient()

# Search for articles
# Default: Sitemap-based search (robots.txt compliant, limited to indexed articles)
results = client.search("elon musk", limit=5)
for result in results:
    print(f"{result.title}: {result.url}")

# API search: Full-text search with pagination and snippets (when robots.txt allows)
client_api = GrokipediaClient(enable_api_search=True)
results = client_api.search("elon musk", limit=5, page=1)
for result in results:
    snippet = result.snippet[:100] + "..." if result.snippet else "No snippet"
    print(f"{result.title}: {snippet}")

# Fetch a complete article
page = client.get_page("Mars")
print(f"Title: {page.title}")
print(f"Summary: {page.summary[:200] if page.summary else 'No summary'}...")
print(f"Sections: {len(page.sections)}")

# Access structured content
for section in page.sections[:3]:  # First 3 sections
    print(f"## {section.title}")
    print(f"{section.text[:150]}...")
```

## CLI Usage

The CLI provides command-line access to all SDK features.

### Global Options

- `--base-url URL`: Base URL for Grokipedia (default: https://grokipedia.com)
- `--user-agent STRING`: User agent string (default: grokipedia-sdk/VERSION)
- `--timeout FLOAT`: Request timeout in seconds (default: 10.0)
- `--rate-limit INT`: Requests per minute (default: 30)
- `--no-cache`: Disable HTTP caching
- `--enable-api-search`: Enable API-based search

### Commands

#### Search Articles

Search for articles using sitemap-based search (default):

```bash
grokipedia search "elon musk" --limit 10
```

Search with API for full-text results and pagination:

```bash
grokipedia --enable-api-search search "elon musk" --limit 10 --page 2
```

#### Fetch Page

Fetch and display an article:

```bash
grokipedia page "Mars"
```

Save article as HTML:

```bash
grokipedia page "Mars" --format html > mars.html
```

Save article as plain text:

```bash
grokipedia page "Mars" --format text > mars.txt
```

## Configuration

Customize the `GrokipediaClient` behavior with these parameters:

```python
client = GrokipediaClient(
    base_url="https://grokipedia.com",      # Base URL for Grokipedia
    respect_robots=True,                    # Check robots.txt compliance
    user_agent="my-app/1.0",                # Custom user agent string
    timeout=10.0,                           # Request timeout in seconds
    requests_per_minute=30,                 # Rate limiting
    cache_ttl=300.0,                        # Cache TTL in seconds (None to disable)
    max_cache_entries=None,                 # Max cache entries (None for unlimited)
    enable_api_search=False,                # Enable API-based search
    robots_strict=False,                    # Strict robots.txt compliance
)
```

### Key Parameters

- **`base_url`**: Change this to use a different Grokipedia instance
- **`respect_robots`**: Whether to check and respect robots.txt rules
- **`user_agent`**: Custom user agent for requests
- **`timeout`**: HTTP request timeout
- **`requests_per_minute`**: Rate limiting to avoid overwhelming servers
- **`cache_ttl`**: How long to cache responses (None disables caching)
- **`max_cache_entries`**: Cache size limit (None for unlimited)
- **`enable_api_search`**: Enable enhanced search via API endpoints
- **`robots_strict`**: Raise errors instead of warnings for robots.txt violations

## Caching & Rate Limiting

### HTTP Caching

The SDK includes an in-memory LRU cache to improve performance:

- **TTL-based expiration**: Cache entries expire after the configured TTL (default: 5 minutes)
- **LRU eviction**: Least recently used entries are removed when cache size limit is reached
- **Automatic cleanup**: Expired entries are cleaned up during cache operations

```python
# Configure caching
client = GrokipediaClient(cache_ttl=600.0, max_cache_entries=100)

# Manual cache management
client.clear_cache()           # Clear all cached responses
size = client.get_cache_size() # Get current cache size
```

### Rate Limiting

Built-in rate limiting prevents overwhelming the Grokipedia servers:

- **Configurable limits**: Default 30 requests per minute
- **Automatic throttling**: Requests are delayed to respect rate limits
- **Retry logic**: Failed requests are automatically retried with backoff
- **Thread-safe**: Rate limiting works correctly in multi-threaded applications

Rate limits are enforced per client instance and include automatic delays between requests.

## API Reference

### Client

#### `GrokipediaClient`

The main client class for accessing Grokipedia content.

**Methods:**

- `search(query, page=1, limit=10)` → `List[SearchResult]`: Search for articles
  - `query`: Search term
  - `page`: Page number for API search (1-based)
  - `limit`: Maximum results to return
- `get_page(title_or_url)` → `Page`: Fetch a complete article
  - `title_or_url`: Article title or full URL
- `iter_sitemap(max_urls=None)` → `Iterator[str]`: Iterate through article URLs
  - `max_urls`: Maximum URLs to yield (None for all)
- `clear_cache()` → `None`: Clear the HTTP cache
- `get_cache_size()` → `int`: Get current cache size

### Models

#### `SearchResult`

Represents a search result.

```python
@dataclass
class SearchResult:
    title: str                    # Article title
    url: str                      # Article URL
    thumbnail_url: Optional[str]  # Thumbnail image URL (if available)
    snippet: Optional[str]        # Search result snippet (API search only)
```

#### `Page`

Represents a complete article page.

```python
@dataclass
class Page:
    title: str                    # Article title
    url: str                      # Article URL
    summary: str                  # Article summary/introduction
    sections: List[Section]       # Article sections
    infobox: Optional[Dict[str, str]]  # Structured data (if available)
```

#### `Section`

Represents an article section.

```python
@dataclass
class Section:
    title: str                    # Section heading
    html: str                     # Section content as HTML
    text: str                     # Section content as plain text
```

### Exceptions

All SDK exceptions inherit from `GrokipediaError`. Handle exceptions appropriately in your application:

```python
from grokipedia import GrokipediaClient
from grokipedia.exceptions import NotFoundError, HttpError

client = GrokipediaClient()

try:
    page = client.get_page("Nonexistent Article")
except NotFoundError:
    print("Article not found")
except HttpError as e:
    print(f"HTTP error: {e}")
```

#### Exception Types

- **`HttpError`**: Raised for HTTP request failures
  - 4xx/5xx status codes from Grokipedia servers
  - Network connectivity issues
  - Invalid URLs or malformed requests

- **`ParseError`**: Raised when HTML/XML parsing fails
  - Malformed HTML responses from Grokipedia
  - Unexpected changes to page structure
  - Invalid XML in sitemap data

- **`RateLimitError`**: Raised when rate limits are exceeded
  - Too many requests per minute (default: 30)
  - Server-side rate limiting (HTTP 429 responses)

- **`NotFoundError`**: Raised when articles or resources don't exist
  - Article titles that don't match any pages
  - Invalid URLs or non-existent pages
  - Missing sitemap files

- **`RobotsError`**: Raised for robots.txt compliance violations
  - Accessing disallowed endpoints when `robots_strict=True`
  - Required public resources blocked by robots.txt
  - Robots.txt fetch failures

## Development

### Setup Development Environment

Install development dependencies:

```bash
pip install -e ".[dev,cli]"
```

### Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=grokipedia --cov-report=html

# Run only live tests (require internet connection)
pytest -m live
```

### Code Quality

#### Linting and Formatting

```bash
# Format code with Black
black src/

# Sort imports with isort
isort src/

# Lint with pylint
pylint src/grokipedia/
```

#### Type Checking

```bash
# Type check with mypy
mypy src/
```

### Development Workflow

1. **Setup**: `pip install -e ".[dev,cli]"`
2. **Test**: `pytest`
3. **Format**: `black src/ && isort src/`
4. **Type Check**: `mypy src/`
5. **Lint**: `pylint src/grokipedia/`

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass: `pytest`
5. Format code: `black src/ && isort src/`
6. Submit a pull request

## Compliance

This SDK is designed to be respectful of Grokipedia's `robots.txt` rules and only accesses publicly available resources. On client initialization, it automatically fetches and parses `robots.txt` to ensure compliance.

### Resource Usage

- **HTML Pages**: Parses article content from public `/page/*` URLs
- **XML Sitemaps**: Uses sitemap data for default search functionality
- **API Endpoints**: Optionally uses `/api/full-text-search` when `enable_api_search=True`

### Search Modes

- **Sitemap Search** (default): Scans article titles from XML sitemaps, performs client-side text matching. Limited to currently indexed articles but fully robots.txt compliant.
- **API Search**: Uses Grokipedia's full-text search API for comprehensive results with pagination support and search snippets.

### Robots.txt Compliance

By default (`respect_robots=True`), the SDK checks robots.txt compliance:

- **API Endpoints**: Checks if `/api/`, `/api/full-text-search`, and other API paths are allowed
- **Required Resources**: Verifies that essential public resources (`/`, `/page/Test`, `/sitemap.xml`) are accessible
- **Auto-Disabling**: If API endpoints are disallowed, API search is automatically disabled with a warning
- **Strict Mode**: Set `robots_strict=True` to raise a `RobotsError` instead of auto-disabling API search

The SDK never accesses robots.txt-disallowed resources in default operation.

## Requirements

- Python 3.10+
- `requests` for HTTP requests
- `beautifulsoup4` for HTML parsing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
