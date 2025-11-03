"""Custom exceptions for the Grokipedia SDK."""


class GrokipediaError(Exception):
    """Base exception for Grokipedia SDK errors."""
    pass


class HttpError(GrokipediaError):
    """Raised when HTTP requests fail."""
    pass


class ParseError(GrokipediaError):
    """Raised when HTML/XML parsing fails."""
    pass


class RateLimitError(GrokipediaError):
    """Raised when rate limit is exceeded."""
    pass


class NotFoundError(GrokipediaError):
    """Raised when a page or resource is not found."""
    pass


class RobotsError(GrokipediaError):
    """Raised when robots.txt rules are violated."""
    pass
