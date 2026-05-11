from __future__ import annotations
from unittest.mock import MagicMock
import requests
from src import crawler


# fetch_page should return response text for valid HTML responses.
def test_fetch_page_success(monkeypatch):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.headers = {"Content-Type": "text/html; charset=utf-8"}
    response.text = "<html><body>Hello</body></html>"

    def fake_get(url, timeout):
        assert url == "https://quotes.toscrape.com/"
        assert timeout == crawler.DEFAULT_TIMEOUT
        return response

    monkeypatch.setattr(crawler.requests, "get", fake_get)

    html = crawler.fetch_page("https://quotes.toscrape.com/")
    assert html == "<html><body>Hello</body></html>"


# fetch_page should return None when request fails.
def test_fetch_page_failure(monkeypatch):

    def fake_get(url, timeout):
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr(crawler.requests, "get", fake_get)

    html = crawler.fetch_page("https://quotes.toscrape.com/")
    assert html is None


# extract_links should return only normalized internal links without duplicates.
def test_extract_links_internal_only_and_deduplicated():
    html = """
    <html><body>
      <a href="/page/2/">Next</a>
      <a href="https://quotes.toscrape.com/page/2/">Next Absolute</a>
      <a href="https://quotes.toscrape.com/page/2/#frag">Fragment</a>
      <a href="https://example.com/page/2/">External</a>
      <a href="#local">Anchor</a>
      <a href="mailto:test@example.com">Email</a>
      <a href="javascript:void(0)">JS</a>
    </body></html>
    """

    links = crawler.extract_links(html, "https://quotes.toscrape.com/page/1/")

    assert links == {"https://quotes.toscrape.com/page/2/"}


# extract_text should return meaningful visible text only.
def test_extract_text_removes_scripts_styles_hidden_and_normalizes_whitespace():
    html = """
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>console.log('x')</script>
      </head>
      <body>
        <div>  Hello   world  </div>
        <div hidden>hidden 1</div>
        <div style="display: none">hidden 2</div>
        <p>Line 2</p>
      </body>
    </html>
    """

    text = crawler.extract_text(html)

    assert text == "Hello world Line 2"


# extract_text should handle empty and malformed HTML gracefully.
def test_extract_text_empty_and_invalid_html():
    assert crawler.extract_text("") == ""

    malformed = "<html><body><p>Open tag only"
    text = crawler.extract_text(malformed)
    assert "Open tag only" in text

# extract_links should fail safely when base URL is malformed.
def test_extract_links_handles_malformed_base_url():
    html = '<a href="/page/2/">Next</a>'
    links = crawler.extract_links(html, "not-a-valid-url")
    assert links == set()


# crawl should avoid revisiting already seen URLs.
def test_crawl_prevents_duplicate_urls_and_collects_pages(monkeypatch):
    pages = {
        "https://quotes.toscrape.com/": "<html>page1</html>",
        "https://quotes.toscrape.com/page/2/": "<html>page2</html>",
    }

    fetched = []

    def fake_fetch(url, session=None, timeout=crawler.DEFAULT_TIMEOUT):
        fetched.append(url)
        return pages.get(url)

    def fake_extract_links(html, base_url):
        if "page1" in html:
            return {
                "https://quotes.toscrape.com/page/2/",
                "https://quotes.toscrape.com/page/2/",  # duplicate on purpose
            }
        return set()

    def fake_extract_text(html):
        return html.replace("<html>", "").replace("</html>", "")

    monkeypatch.setattr(crawler, "fetch_page", fake_fetch)
    monkeypatch.setattr(crawler, "extract_links", fake_extract_links)
    monkeypatch.setattr(crawler, "extract_text", fake_extract_text)
    monkeypatch.setattr(crawler.time, "sleep", lambda _: None)
    monkeypatch.setattr(crawler.time, "time", lambda: 0.0)

    results = crawler.crawl("https://quotes.toscrape.com/")

    assert fetched == [
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    ]
    assert [item["url"] for item in results] == fetched


# crawl should sleep to enforce the minimum delay between requests.
def test_crawl_politeness_delay(monkeypatch):
    pages = {
        "https://quotes.toscrape.com/": "<html>one</html>",
        "https://quotes.toscrape.com/page/2/": "<html>two</html>",
    }

    def fake_fetch(url, session=None, timeout=crawler.DEFAULT_TIMEOUT):
        return pages.get(url)

    def fake_extract_links(html, base_url):
        return {"https://quotes.toscrape.com/page/2/"} if "one" in html else set()

    sleep_calls = []

    monkeypatch.setattr(crawler, "fetch_page", fake_fetch)
    monkeypatch.setattr(crawler, "extract_links", fake_extract_links)
    monkeypatch.setattr(crawler, "extract_text", lambda html: html)
    monkeypatch.setattr(crawler.time, "time", lambda: 0.0)
    monkeypatch.setattr(crawler.time, "sleep", lambda s: sleep_calls.append(s))

    crawler.crawl("https://quotes.toscrape.com/")

    assert sleep_calls, "Expected at least one politeness sleep call"
    assert sleep_calls[0] >= 6


# crawl should return an empty result for malformed start URL.
def test_crawl_invalid_start_url_returns_empty():
    assert crawler.crawl("notaurl") == []