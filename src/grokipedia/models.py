"""Data models for Grokipedia SDK."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SearchResult:
    """Represents a search result from Grokipedia."""

    title: str
    url: str
    thumbnail_url: Optional[str] = None
    snippet: Optional[str] = None


@dataclass
class Section:
    """Represents a section of a Grokipedia article."""

    title: str
    html: str
    text: str


@dataclass
class Page:
    """Represents a complete Grokipedia article page."""

    title: str
    url: str
    summary: str
    sections: List[Section]
    infobox: Optional[Dict[str, str]] = None
