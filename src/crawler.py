from __future__ import annotations
from collections import deque
import logging
import re
import time
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
import requests
from bs4 import BeautifulSoup
from bs4.element import Comment


logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_DELAY_SECONDS = 6.0


# Return True if candidate_netloc is inside the allowed domain.
def _is_same_domain(candidate_netloc: str, allowed_netloc: str) -> bool:
    candidate = candidate_netloc.lower()
    allowed = allowed_netloc.lower()
    return candidate == allowed or candidate.endswith(f".{allowed}")


# Normalize and canonicalize a URL.
# Returns None for malformed/unsupported URLs.
def normalize_url(url: str, base_url: str | None = None) -> str | None:
    if not url:
        return None

    try:
        joined = urljoin(base_url, url) if base_url else url
        defragmented, _ = urldefrag(joined)
        parsed = urlparse(defragmented)
    except Exception as exc:
        logger.warning("Failed to parse URL '%s': %s", url, exc)
        return None

    if parsed.scheme not in {"http", "https"}:
        return None

    if not parsed.netloc:
        return None

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    path = parsed.path or "/"
    path = re.sub(r"/{2,}", "/", path)

    is_file_like = bool(re.search(r"/[^/]+\.[^/]+$", path))
    if path != "/" and not path.endswith("/") and not is_file_like:
        path += "/"

    normalized = parsed._replace(
        scheme=scheme,
        netloc=netloc,
        path=path,
        params="",
        query="",
        fragment="",
    )

    return urlunparse(normalized)


# Fetch an HTML page and return response text, or None on failure.
def fetch_page(
    url: str,
    session: requests.Session | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str | None:
    client = session or requests

    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("Request timed out: %s", url)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("Failed request for %s: %s", url, exc)
        return None

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type.lower():
        logger.warning("Skipping non-HTML response for %s (Content-Type: %s)", url, content_type)
        return None

    if not response.text:
        logger.warning("Empty response body for %s", url)
        return None

    return response.text


# Extract normalized internal links from HTML.
# Only links in the same domain as `base_url` are returned.
def extract_links(html: str, base_url: str) -> set[str]:
    if not html:
        return set()

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("Failed to parse HTML for link extraction (%s): %s", base_url, exc)
        return set()

    base_parsed = urlparse(base_url)
    allowed_netloc = base_parsed.netloc.lower()
    extracted: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue

        normalized = normalize_url(href, base_url=base_url)
        if not normalized:
            logger.info("Skipping malformed/unsupported URL '%s' from %s", href, base_url)
            continue

        parsed = urlparse(normalized)
        if not _is_same_domain(parsed.netloc, allowed_netloc):
            continue

        extracted.add(normalized)

    return extracted


# Return True if BeautifulSoup text element is likely visible content.
def _is_visible_text_element(text_element: Any) -> bool:
    parent_name = getattr(getattr(text_element, "parent", None), "name", "")
    if parent_name in {"script", "style", "noscript", "template", "head", "title", "meta"}:
        return False

    if isinstance(text_element, Comment):
        return False

    return True


# Extract visible, normalized plain text from HTML.
def extract_text(html: str) -> str:
    if not html:
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("Failed to parse HTML for text extraction: %s", exc)
        return ""

    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    for hidden in soup.select("[hidden]"):
        hidden.decompose()

    for hidden_style in soup.select("[style]"):
        style_value = (hidden_style.get("style") or "").lower()
        if "display:none" in style_value.replace(" ", "") or "visibility:hidden" in style_value.replace(" ", ""):
            hidden_style.decompose()

    visible_text = [text for text in soup.stripped_strings if _is_visible_text_element(text)]
    merged = " ".join(visible_text)
    cleaned = re.sub(r"\s+", " ", merged).strip()
    return cleaned


# Crawl reachable internal pages from start_url using BFS.
# Returns a list of dictionaries.
def crawl(
    start_url: str,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    normalized_start = normalize_url(start_url)
    if not normalized_start:
        logger.warning("Invalid start URL: %s", start_url)
        return []

    allowed_netloc = urlparse(normalized_start).netloc.lower()

    queue: deque[str] = deque([normalized_start])
    queued: set[str] = {normalized_start}
    visited: set[str] = set()
    results: list[dict[str, Any]] = []

    session = requests.Session()
    last_request_time: float | None = None

    try:
        while queue:
            current_url = queue.popleft()
            queued.discard(current_url)

            if current_url in visited:
                logger.info("Skipping duplicate URL: %s", current_url)
                continue

            if max_pages is not None and len(visited) >= max_pages:
                logger.info("Reached max_pages=%s, stopping crawl", max_pages)
                break

            if last_request_time is not None:
                elapsed = time.time() - last_request_time
                if elapsed < delay_seconds:
                    sleep_for = delay_seconds - elapsed
                    logger.info("Politeness delay: sleeping %.2f seconds", sleep_for)
                    time.sleep(sleep_for)

            logger.info("Crawling page: %s", current_url)
            html = fetch_page(current_url, session=session)
            last_request_time = time.time()
            visited.add(current_url)

            if html is None:
                logger.warning("No HTML retrieved for %s", current_url)
                continue

            text = extract_text(html)
            links = extract_links(html, current_url)

            internal_links = sorted(
                link
                for link in links
                if _is_same_domain(urlparse(link).netloc, allowed_netloc)
            )

            results.append(
                {
                    "url": current_url,
                    "text": text,
                    "links": internal_links,
                }
            )

            for link in internal_links:
                if link in visited or link in queued:
                    logger.info("Skipping duplicate URL: %s", link)
                    continue
                queue.append(link)
                queued.add(link)

            logger.info(
                "Crawl progress - visited: %d, pending: %d, stored: %d",
                len(visited),
                len(queue),
                len(results),
            )
    finally:
        session.close()

    logger.info("Crawl finished: %d pages crawled", len(results))
    return results


__all__ = [
    "normalize_url",
    "fetch_page",
    "extract_links",
    "extract_text",
    "crawl",
]
