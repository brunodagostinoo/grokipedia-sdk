"""Grokipedia SDK - A read-only Python SDK for Grokipedia."""

from grokipedia.client import GrokipediaClient
from grokipedia.exceptions import (
    GrokipediaError,
    HttpError,
    NotFoundError,
    ParseError,
    RateLimitError,
    RobotsError,
)

__version__ = "0.1.1"
__all__ = [
    "GrokipediaClient",
    "GrokipediaError",
    "HttpError",
    "NotFoundError",
    "ParseError",
    "RateLimitError",
    "RobotsError",
]
