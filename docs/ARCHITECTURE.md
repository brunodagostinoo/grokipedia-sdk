# Grokipedia SDK Architecture

This document provides a technical overview of the Grokipedia SDK architecture for developers looking to understand, contribute to, or extend the codebase.

For usage documentation, see the [README](../README.md).

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [Class Diagram](#class-diagram)
- [Sequence Diagrams](#sequence-diagrams)
- [Data Models](#data-models)
- [Module Reference](#module-reference)
- [Key Concepts](#key-concepts)
- [Exception Handling](#exception-handling)

---

## Overview

The Grokipedia SDK is a read-only Python client for accessing [Grokipedia](https://grokipedia.com), an AI-generated online encyclopedia. It provides:

- **Article fetching** with structured parsing (title, summary, sections, infobox)
- **Search** via sitemap (default) or API
- **Rate limiting** and **caching** for responsible usage
- **robots.txt compliance** built-in
- **CLI** for command-line access

### Quick Install

```bash
pip install grokipedia-sdk        # Base package
pip install grokipedia-sdk[cli]   # With CLI
pip install grokipedia-sdk[dev]   # With dev tools
```

---

## Architecture Diagram

The SDK follows a layered architecture with clear separation of concerns:

```mermaid
graph TB
    subgraph User["User Interface"]
        Code["Python Code"]
        CLI["CLI (click)"]
    end

    subgraph SDK["Grokipedia SDK"]
        Client["GrokipediaClient<br/><i>Orchestrator</i>"]

        subgraph Core["Core Layer"]
            HTTP["HttpClient<br/><i>HTTP + Cache + Rate Limit</i>"]
            Robots["RobotsParser<br/><i>robots.txt Compliance</i>"]
        end

        subgraph Parsing["Parsing Layer"]
            Parser["parser.py<br/><i>HTML Parsing</i>"]
            Sitemap["sitemap.py<br/><i>XML Sitemap</i>"]
        end

        subgraph Data["Data Layer"]
            Models["models.py<br/><i>Page, Section, SearchResult</i>"]
            Exceptions["exceptions.py<br/><i>Error Hierarchy</i>"]
        end
    end

    subgraph External["External Dependencies"]
        Requests["requests"]
        BS4["beautifulsoup4"]
        LXML["lxml"]
    end

    subgraph Remote["Remote Services"]
        Grokipedia["grokipedia.com"]
    end

    Code --> Client
    CLI --> Client
    Client --> HTTP
    Client --> Robots
    Client --> Parser
    Client --> Sitemap
    HTTP --> Requests
    Parser --> BS4
    Sitemap --> BS4
    BS4 --> LXML
    Parser --> Models
    HTTP -.-> Exceptions
    Client -.-> Exceptions
    HTTP --> Grokipedia
```

---

## Class Diagram

```mermaid
classDiagram
    class GrokipediaClient {
        -HttpClient http
        -Dict _sitemap_cache
        -float _sitemap_cache_time
        -bool enable_api_search
        +search(query, page, limit) List~SearchResult~
        +get_page(title_or_url) Page
        +iter_sitemap(max_urls) Iterator~str~
        +refresh_sitemap()
        +clear_cache()
        +get_cache_size() int
    }

    class HttpClient {
        -Session session
        -OrderedDict _cache
        -Lock _cache_lock
        -Lock _rate_limit_lock
        -float _last_request_time
        +get(url) str
        +clear_cache()
        +get_cache_size() int
        +close()
    }

    class RobotsParser {
        -List~tuple~ rules
        +is_allowed(url) bool
        -_matches_pattern(path, pattern) bool
    }

    class Page {
        +str title
        +str url
        +str summary
        +List~Section~ sections
        +Dict infobox
    }

    class Section {
        +str title
        +str html
        +str text
    }

    class SearchResult {
        +str title
        +str url
        +str thumbnail_url
        +str snippet
    }

    class GrokipediaError {
        <<exception>>
    }

    class HttpError {
        <<exception>>
    }

    class NotFoundError {
        <<exception>>
    }

    class ParseError {
        <<exception>>
    }

    class RateLimitError {
        <<exception>>
    }

    class RobotsError {
        <<exception>>
    }

    GrokipediaClient --> HttpClient : uses
    GrokipediaClient --> RobotsParser : uses
    GrokipediaClient ..> Page : returns
    GrokipediaClient ..> SearchResult : returns
    Page *-- Section : contains

    GrokipediaError <|-- HttpError
    GrokipediaError <|-- NotFoundError
    GrokipediaError <|-- ParseError
    GrokipediaError <|-- RateLimitError
    GrokipediaError <|-- RobotsError
```

---

## Sequence Diagrams

### Page Fetching

```mermaid
sequenceDiagram
    participant User
    participant Client as GrokipediaClient
    participant HTTP as HttpClient
    participant Cache as LRU Cache
    participant Remote as grokipedia.com
    participant Parser as parser.py

    User->>Client: get_page("Mars")
    Client->>Client: _title_to_slug("Mars")
    Note right of Client: URL: /page/Mars

    Client->>HTTP: get(url)
    HTTP->>HTTP: acquire _rate_limit_lock
    HTTP->>HTTP: check rate limit

    HTTP->>Cache: check cache
    alt Cache Hit (valid TTL)
        Cache-->>HTTP: cached HTML
    else Cache Miss
        HTTP->>Remote: HTTP GET /page/Mars
        Remote-->>HTTP: HTML response
        HTTP->>Cache: store with timestamp
    end

    HTTP-->>Client: HTML string

    Client->>Parser: parse_article_page(html)
    Parser->>Parser: BeautifulSoup parse
    Parser->>Parser: extract title (h1)
    Parser->>Parser: extract summary
    Parser->>Parser: extract sections (h2/h3)
    Parser->>Parser: extract infobox (table)
    Parser-->>Client: Page object

    Client-->>User: Page
```

### Search (Sitemap-based, Default)

```mermaid
sequenceDiagram
    participant User
    participant Client as GrokipediaClient
    participant HTTP as HttpClient
    participant Remote as grokipedia.com
    participant Sitemap as sitemap.py

    User->>Client: search("Mars", limit=5)

    Client->>Client: check _sitemap_cache
    alt Cache Valid
        Note right of Client: Use cached titles
    else Cache Invalid/Empty
        Client->>Sitemap: iter_sitemap_urls(max=1000)
        Sitemap->>HTTP: get(/sitemap.xml)
        HTTP->>Remote: HTTP GET
        Remote-->>HTTP: XML index
        HTTP-->>Sitemap: sitemap index

        loop For each sitemap part
            Sitemap->>HTTP: get(part_url)
            HTTP->>Remote: HTTP GET
            Remote-->>HTTP: XML part
            HTTP-->>Sitemap: article URLs
        end

        Sitemap-->>Client: URLs iterator
        Client->>Client: extract titles from URLs
        Client->>Client: cache in _sitemap_cache
    end

    Client->>Client: match query vs titles
    Client->>Client: sort (prefix first, then length)
    Client->>Client: limit results

    Client-->>User: List[SearchResult]
```

### Search (API-based)

```mermaid
sequenceDiagram
    participant User
    participant Client as GrokipediaClient
    participant HTTP as HttpClient
    participant API as grokipedia.com/api

    User->>Client: search("Mars", page=2, limit=10)
    Note right of Client: enable_api_search=True

    Client->>Client: calculate offset=(2-1)*10=10
    Client->>Client: build API URL
    Note right of Client: /api/full-text-search?query=Mars&limit=10&offset=10

    Client->>HTTP: get(api_url)
    HTTP->>API: HTTP GET
    API-->>HTTP: JSON response
    HTTP-->>Client: JSON string

    Client->>Client: json.loads()
    Client->>Client: extract results[]

    loop For each result
        Client->>Client: build URL from slug
        Client->>Client: create SearchResult
    end

    Client-->>User: List[SearchResult]
```

---

## Data Models

```mermaid
erDiagram
    Page {
        string title
        string url
        string summary
        dict infobox
    }

    Section {
        string title
        string html
        string text
    }

    SearchResult {
        string title
        string url
        string thumbnail_url
        string snippet
    }

    Page ||--o{ Section : "contains"
```

### Field Descriptions

#### Page
| Field | Type | Description |
|-------|------|-------------|
| `title` | str | Article title from `<h1>` |
| `url` | str | Full URL of the article |
| `summary` | str | Introduction text before first `<h2>` |
| `sections` | List[Section] | All article sections |
| `infobox` | Dict[str, str] | Key-value data from first table (optional) |

#### Section
| Field | Type | Description |
|-------|------|-------------|
| `title` | str | Section heading text |
| `html` | str | Raw HTML content |
| `text` | str | Plain text (whitespace normalized) |

#### SearchResult
| Field | Type | Description |
|-------|------|-------------|
| `title` | str | Article title |
| `url` | str | Article URL |
| `thumbnail_url` | str | Image URL (optional, API only) |
| `snippet` | str | Preview text (optional, API only) |

---

## Module Reference

| Module | File | Purpose |
|--------|------|---------|
| **Client** | `client.py` | Main SDK orchestrator, public API |
| **HTTP** | `http.py` | HTTP requests, caching, rate limiting |
| **Parser** | `parser.py` | HTML to data model conversion |
| **Models** | `models.py` | Data classes: Page, Section, SearchResult |
| **Robots** | `robots.py` | robots.txt parsing and compliance |
| **Sitemap** | `sitemap.py` | XML sitemap parsing |
| **Exceptions** | `exceptions.py` | Custom exception hierarchy |
| **CLI** | `cli.py` | Command-line interface (click) |

### Dependencies

```
grokipedia-sdk
├── requests >=2.32.0      # HTTP client
├── beautifulsoup4 >=4.12.0 # HTML/XML parsing
└── lxml >=4.9.0           # Parser backend

[cli]
└── click >=8.0.0          # CLI framework
```

---

## Key Concepts

### Rate Limiting

The SDK enforces rate limiting to be a good citizen:

```python
# Default: 30 requests per minute
client = GrokipediaClient(requests_per_minute=30)
```

- **Thread-safe**: Uses `threading.Lock` for concurrent access
- **Automatic delay**: Sleeps between requests if needed
- **Per-client**: Each client instance has its own limit

### Caching

In-memory LRU cache with TTL for improved performance:

```python
# Default: 5 minute TTL, unlimited entries
client = GrokipediaClient(
    cache_ttl=300.0,      # seconds
    max_cache_entries=100  # limit cache size
)

# Manual cache control
client.clear_cache()
size = client.get_cache_size()
```

- **Thread-safe**: Uses `threading.Lock`
- **LRU eviction**: Least recently used entries removed when limit reached
- **TTL-based expiration**: Entries expire after configured time

### robots.txt Compliance

The SDK respects robots.txt by default:

```python
# Default: check robots.txt
client = GrokipediaClient(respect_robots=True)

# Strict mode: raise error if API endpoints are allowed
client = GrokipediaClient(robots_strict=True)

# Skip robots.txt check (not recommended)
client = GrokipediaClient(respect_robots=False)
```

**Required paths** (must be allowed):
- `/` (homepage)
- `/page/*` (articles)
- `/sitemap.xml`

**API paths checked**:
- `/api/`, `/api/full-text-search`, etc.
- If allowed when `enable_api_search=True`: API search is auto-disabled

### Search Modes

| Mode | Default | Data Source | Features |
|------|---------|-------------|----------|
| **Sitemap** | Yes | XML sitemaps | robots.txt compliant, title-only matching |
| **API** | No | /api/full-text-search | Full-text search, snippets, pagination |

```python
# Sitemap search (default)
client = GrokipediaClient()
results = client.search("Mars")

# API search (when robots.txt allows)
client = GrokipediaClient(enable_api_search=True)
results = client.search("Mars", page=2, limit=20)
```

---

## Exception Handling

```mermaid
graph TB
    Base["GrokipediaError<br/><i>Base exception</i>"]

    Http["HttpError<br/><i>HTTP failures</i>"]
    NotFound["NotFoundError<br/><i>404 responses</i>"]
    RateLimit["RateLimitError<br/><i>429 responses</i>"]
    Parse["ParseError<br/><i>HTML/JSON parsing</i>"]
    Robots["RobotsError<br/><i>robots.txt violations</i>"]

    Base --> Http
    Base --> NotFound
    Base --> RateLimit
    Base --> Parse
    Base --> Robots
```

### When Exceptions Are Raised

| Exception | Raised When |
|-----------|-------------|
| `HttpError` | HTTP 4xx/5xx (except 404, 429), network errors |
| `NotFoundError` | HTTP 404, article not found |
| `RateLimitError` | HTTP 429 Too Many Requests |
| `ParseError` | Invalid HTML/XML/JSON, unexpected page structure |
| `RobotsError` | robots.txt fetch failed, strict mode violation |

### Example Error Handling

```python
from grokipedia import GrokipediaClient
from grokipedia.exceptions import (
    GrokipediaError,
    NotFoundError,
    HttpError,
    RateLimitError,
)

client = GrokipediaClient()

try:
    page = client.get_page("Nonexistent Article XYZ")
except NotFoundError:
    print("Article not found")
except RateLimitError:
    print("Too many requests, try again later")
except HttpError as e:
    print(f"HTTP error: {e}")
except GrokipediaError as e:
    print(f"SDK error: {e}")
```

---

## Contributing

See [README.md](../README.md#development) for development setup and workflow.

### Code Quality Standards

- **Tests**: `pytest` with 89%+ coverage
- **Types**: `mypy` strict mode
- **Format**: `black` + `isort`
- **Lint**: `pylint` (9.88/10)
