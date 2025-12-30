"""HTML parsing utilities for Grokipedia pages."""

import re
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup, Tag

from grokipedia.exceptions import ParseError
from grokipedia.models import Page, SearchResult, Section


def parse_article_page(
    html: str, _base_url: str, url: str
) -> Page:  # pylint: disable=too-many-locals
    """Parse an article page HTML into a Page object.

    Args:
        html: Raw HTML content
        base_url: Base URL for resolving relative links
        url: The page URL

    Returns:
        Parsed Page object

    Raises:
        ParseError: If parsing fails
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Find the main article content
        article = soup.find("article")
        if not article or not isinstance(article, Tag):
            raise ParseError("No article element found in page")

        # Extract title
        title_elem = article.find("h1")
        if not title_elem or not isinstance(title_elem, Tag):
            raise ParseError("No title (h1) found in article")
        title = title_elem.get_text(strip=True)

        # Extract summary (content before first h2)
        summary_parts: List[str] = []
        current = title_elem.find_next_sibling()
        while current and current.name != "h2":
            if isinstance(current, Tag):
                # Skip navigation, buttons, scripts, styles, etc.
                if current.name not in ["button", "nav", "aside", "script", "style"]:
                    summary_parts.append(current.get_text(strip=True))
            current = current.find_next_sibling()

        summary = " ".join(summary_parts).strip()

        # Extract sections
        sections: List[Section] = []
        headings = article.find_all(["h2", "h3"])

        for heading in headings:
            section_title = heading.get_text(strip=True)

            # Collect content until next heading or end
            content_parts = []
            current = heading.find_next_sibling()

            while current and current.name not in ["h1", "h2", "h3"]:
                if isinstance(current, Tag):
                    # Skip certain elements
                    if current.name not in [
                        "button",
                        "nav",
                        "aside",
                        "script",
                        "style",
                    ]:
                        content_parts.append(str(current))
                current = current.find_next_sibling()

            # Extract text version for easier processing
            content_html = "".join(content_parts)
            content_soup = BeautifulSoup(content_html, "html.parser")
            content_text = content_soup.get_text(separator=" ", strip=True)

            sections.append(
                Section(title=section_title, html=content_html, text=content_text)
            )

        # Try to extract infobox (first table in article)
        infobox: Optional[Dict[str, str]] = None
        table = article.find("table")
        if table and isinstance(table, Tag):
            infobox = _parse_infobox_table(table)

        return Page(
            title=title, url=url, summary=summary, sections=sections, infobox=infobox
        )

    except Exception as e:  # pylint: disable=broad-exception-caught
        raise ParseError(f"Failed to parse article page: {e}") from e


def _parse_infobox_table(table: Tag) -> Dict[str, str]:
    """Parse an infobox table into a key-value dictionary.

    Args:
        table: BeautifulSoup table element

    Returns:
        Dictionary of key-value pairs from the table
    """
    infobox = {}

    try:
        rows = table.find_all("tr")
        # Skip the header row if it exists
        start_row = 1 if len(rows) > 0 and rows[0].find("th") else 0

        for row in rows[start_row:]:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(separator=" ", strip=True)
                if key and value and key != "Property":  # Skip header keys
                    infobox[key] = value
    except Exception:  # pylint: disable=broad-exception-caught
        # If parsing fails, return empty dict
        pass

    return infobox


def parse_search_results(
    html: str, base_url: str, _query: str
) -> List[
    SearchResult
]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Parse search results page HTML into SearchResult objects.

    Args:
        html: Raw HTML content of search page
        base_url: Base URL for resolving relative links
        query: Search query (for validation)

    Returns:
        List of SearchResult objects

    Raises:
        ParseError: If parsing fails
    """
    try:  # pylint: disable=too-many-nested-blocks
        soup = BeautifulSoup(html, "html.parser")
        results: List[SearchResult] = []

        # Find result containers - based on observed structure, they seem to be in divs
        # Look for containers that have clickable elements with titles
        main_elem = soup.find("main")
        if not main_elem or not isinstance(main_elem, Tag):
            return results

        # Find result items - they seem to be in containers within main
        result_containers = main_elem.find_all("div", recursive=False)
        for container in result_containers:
            # Look for clickable result items
            clickable_items = container.find_all(
                "div", {"role": "button"}
            ) or container.find_all("div", class_=lambda x: x and "cursor-pointer" in x)

            for item in clickable_items:
                title_elem = item.find(["h3", "h4", "span", "div"])
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not title:
                    continue

                # Try to find URL - may be in onclick, href, data attributes, or need to derive from title
                url = None

                # Check for explicit links
                link_elem = item.find("a", href=True)
                if link_elem:
                    url = urljoin(base_url, link_elem["href"])
                else:
                    # Check for data attributes or onclick handlers that might contain URLs
                    data_url = item.get("data-url") or item.get("data-href")
                    if data_url:
                        url = urljoin(base_url, data_url)
                    else:
                        # Look for onclick handlers with URL patterns
                        onclick = item.get("onclick", "")
                        if onclick and (
                            "/page/" in onclick or "window.location" in onclick
                        ):
                            # Try to extract URL from onclick - this is a simple heuristic
                            url_match = re.search(r'["\'](/page/[^"\']+)["\']', onclick)
                            if url_match:
                                url = urljoin(base_url, url_match.group(1))

                    # Final fallback: derive from title
                    if not url:
                        slug = _title_to_slug(title)
                        url = urljoin(base_url, f"/page/{slug}")

                # Try to find thumbnail - look in item and its children
                thumbnail_url = None
                img_elem = item.find("img", src=True)
                if img_elem:
                    thumbnail_url = urljoin(base_url, img_elem["src"])
                else:
                    # Look for images in child elements or background images
                    img_elem = item.find(
                        "img", {"data-src": True}
                    )  # Lazy-loaded images
                    if img_elem and img_elem.get("data-src"):
                        thumbnail_url = urljoin(base_url, img_elem["data-src"])
                    else:
                        # Check for background-image CSS in style attributes
                        style = item.get("style", "")
                        if "background-image" in style:
                            bg_match = re.search(
                                r'background-image:\s*url\(["\']?([^"\']+)["\']?\)',
                                style,
                            )
                            if bg_match:
                                thumbnail_url = urljoin(base_url, bg_match.group(1))

                # Try to find snippet/summary - look for dedicated description elements first
                snippet = None

                # Look for elements that might contain descriptions/summaries
                desc_selectors = [
                    ".description",
                    ".summary",
                    ".snippet",
                    ".excerpt",
                    "[data-description]",
                ]
                for selector in desc_selectors:
                    desc_elem = item.select_one(selector)
                    if desc_elem:
                        snippet = desc_elem.get_text(strip=True)
                        break

                # Fallback: extract from all text, excluding the title
                if not snippet:
                    text_elems = item.find_all(string=True, recursive=True)
                    if text_elems:
                        # Get text that's not in the title element
                        title_text = title_elem.get_text(strip=True)
                        all_text_parts = []
                        for elem in text_elems:
                            text = elem.strip()
                            if text and text != title_text and title_text not in text:
                                all_text_parts.append(text)

                        if all_text_parts:
                            snippet = " ".join(all_text_parts).strip()
                            # Clean up extra whitespace
                            snippet = re.sub(r"\s+", " ", snippet)

                        if snippet and len(snippet) > 200:
                            snippet = snippet[:200] + "..."

                if url:
                    results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            thumbnail_url=thumbnail_url,
                            snippet=snippet,
                        )
                    )

        return results

    except Exception as e:  # pylint: disable=broad-exception-caught
        raise ParseError(f"Failed to parse search results: {e}") from e


def _title_to_slug(title: str) -> str:
    """Convert a title to a URL slug.

    Args:
        title: Article title

    Returns:
        URL slug
    """
    # Replace spaces with underscores, then URL-encode all special characters
    slug = title.replace(" ", "_")
    # Always encode to handle all special characters (#, ?, &, %, Unicode, etc.)
    return quote(slug, safe="")
