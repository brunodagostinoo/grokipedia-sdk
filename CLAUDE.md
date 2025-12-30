# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install for development (includes test/lint tools and CLI)
pip install -e ".[dev,cli]"

# Run tests
pytest                              # All tests
pytest -m live                      # Live integration tests only (requires internet)
pytest --cov=grokipedia             # With coverage

# Code quality
black src/                          # Format code
isort src/                          # Sort imports
mypy src/                           # Type check (strict mode)
pylint src/grokipedia/              # Lint
```

## Architecture

Read-only Python SDK for [Grokipedia](https://grokipedia.com), an AI-generated encyclopedia by xAI.

### Source Structure (`src/grokipedia/`)

- **client.py** - `GrokipediaClient`: main entry point with `search()`, `get_page()`, `iter_sitemap()` methods
- **http.py** - `HttpClient`: HTTP requests with LRU caching (TTL-based), rate limiting (30 req/min default), and retry logic
- **parser.py** - HTML parsing utilities for extracting articles, sections, and infoboxes
- **robots.py** - `RobotsParser`: robots.txt compliance checking
- **sitemap.py** - XML sitemap parsing for article URL iteration
- **models.py** - Data classes: `SearchResult`, `Page`, `Section`
- **exceptions.py** - Exception hierarchy: `GrokipediaError` → `HttpError`, `ParseError`, `RateLimitError`, `NotFoundError`, `RobotsError`
- **cli.py** - Click-based CLI (optional `[cli]` dependency)

### Key Patterns

- **Dual search modes**: Sitemap-based (default, robots.txt compliant) vs API-based (full-text with pagination via `enable_api_search=True`)
- **robots.txt compliance**: Enabled by default (`respect_robots=True`), auto-disables API search if disallowed
- **Thread-safe**: Rate limiting and caching work in multi-threaded applications
- **Type hints**: Full mypy strict mode coverage (except cli.py)
