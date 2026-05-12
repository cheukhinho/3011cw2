from __future__ import annotations
import json
from src import indexer


# tokenize should normalize case, punctuation, and whitespace.
def test_tokenize_lowercases_and_removes_punctuation():
    tokens = indexer.tokenize(" Good friends,   good books! ")
    assert tokens == ["good", "friends", "good", "books"]


# tokenize should return empty list for non-string input.
def test_tokenize_handles_non_string_input():
    assert indexer.tokenize(None) == []


# build_index should create frequency and position postings correctly.
def test_build_index_tracks_frequency_positions_and_case_insensitive_tokens():
    pages = [
        {
            "url": "https://quotes.toscrape.com/page/1/",
            "text": "Good friends are good",
            "links": [],
        }
    ]
    built = indexer.build_index(pages)

    assert built["good"]["https://quotes.toscrape.com/page/1/"]["frequency"] == 2
    assert built["good"]["https://quotes.toscrape.com/page/1/"]["positions"] == [0, 3]
    assert built["friends"]["https://quotes.toscrape.com/page/1/"]["positions"] == [1]


# build_index should safely skip malformed page entries.
def test_build_index_skips_empty_and_malformed_pages():
    pages = [
        {},
        {"url": "", "text": "valid words"},
        {"url": "https://quotes.toscrape.com/page/2/", "text": ""},
        "not-a-dict",
    ]
    built = indexer.build_index(pages)
    assert built == {}


# build_index should only index the first occurrence of a duplicated URL.
def test_build_index_skips_duplicate_urls_to_avoid_duplicate_indexing():
    pages = [
        {"url": "https://quotes.toscrape.com/page/1/", "text": "alpha beta"},
        {"url": "https://quotes.toscrape.com/page/1/", "text": "alpha alpha alpha"},
    ]
    built = indexer.build_index(pages)
    assert built["alpha"]["https://quotes.toscrape.com/page/1/"]["frequency"] == 1
    assert built["alpha"]["https://quotes.toscrape.com/page/1/"]["positions"] == [0]


# save_index and load_index should persist and retrieve the same structure.
def test_save_and_load_index_round_trip(tmp_path):
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {
                "frequency": 2,
                "positions": [0, 3],
            }
        }
    }
    output_file = tmp_path / "data" / "compiled_index.json"

    assert indexer.save_index(index_data, output_file) is True
    loaded = indexer.load_index(output_file)
    assert loaded == index_data


# save_index should fail safely when given an invalid file path target.
def test_save_index_handles_invalid_path(tmp_path):
    invalid_target = tmp_path / "directory-target"
    invalid_target.mkdir()
    assert indexer.save_index({}, invalid_target) is False


# load_index should return empty dict if file does not exist.
def test_load_index_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "not_found.json"
    assert indexer.load_index(missing) == {}


# load_index should return empty dict for invalid JSON files.
def test_load_index_invalid_json_returns_empty(tmp_path):
    bad_file = tmp_path / "bad_index.json"
    bad_file.write_text("{not-valid-json", encoding="utf-8")
    assert indexer.load_index(bad_file) == {}


# load_index should reject data that does not match index schema.
def test_load_index_invalid_structure_returns_empty(tmp_path):
    bad_structure_file = tmp_path / "wrong_shape.json"
    bad_structure_file.write_text(json.dumps({"word": ["unexpected"]}), encoding="utf-8")
    assert indexer.load_index(bad_structure_file) == {}


# get_word_entry should support case-insensitive word retrieval.
def test_get_word_entry_case_insensitive_lookup():
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]}
        }
    }
    entry = indexer.get_word_entry("GOOD", index_data)
    assert entry == index_data["good"]                                                                                       
    assert indexer.get_word_entry("missing", index_data) == {}


# get_word_entry should return empty result for multi-word lookups.
def test_get_word_entry_rejects_multi_token_input():
    index_data = {
        "good": {
            "https://quotes.toscrape.com/page/1/": {"frequency": 1, "positions": [0]}
        }
    }
    assert indexer.get_word_entry("good books", index_data) == {}
