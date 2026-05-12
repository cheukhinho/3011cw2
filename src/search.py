from __future__ import annotations
import logging
from typing import Any
from src import indexer

logger = logging.getLogger(__name__)


# Normalize a query string into lowercase tokens.
def normalize_query(query: str) -> list[str]:
    if not isinstance(query, str):
        logger.warning("Non-string query received; returning empty token list")
        return []

    return indexer.tokenize(query)


# Return indexed words sorted alphabetically.
def indexed_words(index: dict[str, Any]) -> list[str]:
    if not isinstance(index, dict):
        logger.warning("Malformed index input (expected dict)")
        return []

    return sorted(word for word in index.keys() if isinstance(word, str))


# Search for pages matching a query.
# Multi-word queries use AND semantics (all words must appear in a page).
# Results are ranked by combined term frequency (descending), then URL.
def search(query: str, index: dict[str, Any]) -> list[str]:
    if not isinstance(index, dict):
        logger.warning("Malformed index input (expected dict)")
        return []

    terms = normalize_query(query)
    if not terms:
        return []

    unique_terms = list(dict.fromkeys(terms))

    postings_by_term: list[dict[str, dict[str, Any]]] = []
    for term in unique_terms:
        posting = index.get(term)
        if not isinstance(posting, dict) or not posting:
            return []
        postings_by_term.append(posting)

    matching_urls = set(postings_by_term[0].keys())
    for posting in postings_by_term[1:]:
        matching_urls &= set(posting.keys())

    if not matching_urls:
        return []

    scored_results: list[tuple[int, str]] = []
    for url in matching_urls:
        score = 0
        for posting in postings_by_term:
            payload = posting.get(url, {})
            if isinstance(payload, dict):
                frequency = payload.get("frequency", 0)
                if isinstance(frequency, int):
                    score += frequency
        scored_results.append((score, url))

    scored_results.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, url in scored_results]


__all__ = ["normalize_query", "indexed_words", "search"]