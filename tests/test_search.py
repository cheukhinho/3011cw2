from __future__ import annotations
from src.main import SearchCLI
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


# search should support quoted phrase queries.
def test_search_phrase_query_matches_consecutive_positions():=
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]},
            "https://quotes.toscrape.com/page/2/": {"frequency": 1, "positions": [2]},
        },
        "friends": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [1]},
            "https://quotes.toscrape.com/page/2/": {"frequency": 1, "positions": [8]},
        },
    }

    assert search.search('"good friends"', index_data) == ["https://quotes.toscrape.com/page/1/"]


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


# search should reject malformed quoted queries.
def test_search_malformed_quoted_query_returns_empty():
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]},
        }
    }
    assert search.search('"good', index_data) == []


# indexed_words should return sorted index terms.
def test_indexed_words_returns_sorted_terms():
    assert search.indexed_words({"zulu": {}, "alpha": {}}) == ["alpha", "zulu"]


# indexed_words should return empty list for malformed input.
def test_indexed_words_handles_invalid_input():
    assert search.indexed_words("not-a-dict") == []


# CLI should guide the user when searching without an index.
def test_cli_find_before_load_or_build(capsys):
    cli = SearchCLI()
    cli.process_command("find good friends")
    output = capsys.readouterr().out
    assert "No index loaded. Use 'build' or 'load' first." in output


# CLI should return a user-friendly error for unknown commands.
def test_cli_invalid_command_message(capsys):
    cli = SearchCLI()
    should_exit = cli.process_command("unknown-command")
    output = capsys.readouterr().out
    assert should_exit is False
    assert "Invalid command" in output


# CLI print command should show structured posting output.
def test_cli_print_word_output_format(capsys):
    cli = SearchCLI()
    cli.index = {
        "wisdom": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 2, "positions": [1, 7]},
        }
    }
    cli.process_command("print wisdom")
    output = capsys.readouterr().out
    assert "Word 'wisdom' appears in 1 page(s):" in output
    assert "1. https://quotes.toscrape.com/page/1/" in output
    assert "frequency=2" in output