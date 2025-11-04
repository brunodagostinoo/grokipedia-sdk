"""Custom exceptions for the Grokipedia SDK."""


class GrokipediaError(Exception):
    """Base exception for Grokipedia SDK errors."""


class HttpError(GrokipediaError):
    """Raised when HTTP requests fail."""


class ParseError(GrokipediaError):
    """Raised when HTML/XML parsing fails."""


class RateLimitError(GrokipediaError):
    """Raised when rate limit is exceeded."""


class NotFoundError(GrokipediaError):
    """Raised when a page or resource is not found."""


class RobotsError(GrokipediaError):
    """Raised when robots.txt rules are violated."""
