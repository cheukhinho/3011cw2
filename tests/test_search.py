from __future__ import annotations
from src import search


# normalize_query should normalize query text into lowercase tokens.
def test_normalize_query_is_case_insensitive_and_strips_punctuation():
    assert search.normalize_query(" Good, BOOKS! ") == ["good", "books"]


# search should return URLs ranked by term frequency for single-word query.
def test_search_single_word_returns_ranked_urls():
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]},
            "https://quotes.toscrape.com/page/2/": {"frequency": 3, "positions": [0, 4, 9]},
        }
    }

    assert search.search("GOOD", index_data) == [
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/page/1/",
    ]


# search should return only pages containing all query terms.
def test_search_multi_word_uses_and_semantics():
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]},
            "https://quotes.toscrape.com/page/2/": {"frequency": 1, "positions": [2]},
        },
        "books": {
            "https://quotes.toscrape.com/page/2/": {"frequency": 1, "positions": [8]},
        },
    }

    assert search.search("good books", index_data) == ["https://quotes.toscrape.com/page/2/"]


# search should safely return empty results for invalid input.
def test_search_handles_empty_invalid_and_missing_queries():
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]},
        }
    }

    assert search.search("", index_data) == []
    assert search.search(123, index_data) == []
    assert search.search("!!!", index_data) == []
    assert search.search("missing", index_data) == []
    assert search.search("good", "not-a-dict") == []


# indexed_words should return sorted index terms.
def test_indexed_words_returns_sorted_terms():
    assert search.indexed_words({"zulu": {}, "alpha": {}}) == ["alpha", "zulu"]


# indexed_words should return empty list for malformed input.
def test_indexed_words_handles_invalid_input():
    assert search.indexed_words("not-a-dict") == []