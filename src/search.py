from __future__ import annotations
import logging
import re
from typing import Any
from src import indexer

logger = logging.getLogger(__name__)
_PHRASE_PATTERN = re.compile(r'"([^"]+)"')


# Normalize a query string into lowercase tokens.
def normalize_query(query: str) -> list[str]:
    if not isinstance(query, str):
        logger.warning("Non-string query received; returning empty token list")
        return []

    return indexer.tokenize(query)


# Parse query into normal terms and quoted phrase terms.
def _parse_query_components(query: str) -> tuple[list[str], list[list[str]]]:
    if not isinstance(query, str):
        logger.warning("Non-string query received; returning empty query components")
        return [], []

    if query.count('"') % 2 != 0:
        logger.warning("Malformed query received (unmatched quote): %s", query)
        return [], []

    phrase_tokens = [indexer.tokenize(match) for match in _PHRASE_PATTERN.findall(query)]
    phrase_tokens = [tokens for tokens in phrase_tokens if tokens]

    query_without_phrases = _PHRASE_PATTERN.sub(" ", query)
    normal_terms = indexer.tokenize(query_without_phrases)
    return normal_terms, phrase_tokens


# Return True when all phrase terms appear consecutively in a document.
def _phrase_matches_url(
    phrase_terms: list[str],
    url: str,
    index: dict[str, Any],
) -> bool:
    if not phrase_terms:
        return False

    position_sets: list[set[int]] = []
    for term in phrase_terms:
        posting = index.get(term, {})
        if not isinstance(posting, dict):
            return False

        payload = posting.get(url, {})
        if not isinstance(payload, dict):
            return False

        positions = payload.get("positions", [])
        if not isinstance(positions, list):
            return False

        valid_positions = {pos for pos in positions if isinstance(pos, int) and pos >= 0}
        if not valid_positions:
            return False
        position_sets.append(valid_positions)

    start_positions = position_sets[0]
    for start in start_positions:
        if all((start + offset) in position_sets[offset] for offset in range(1, len(position_sets))):
            return True
    return False


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

    terms, phrase_groups = _parse_query_components(query)
    if not terms and not phrase_groups:
        return []

    unique_terms = list(dict.fromkeys(terms))

    postings_by_term: list[dict[str, dict[str, Any]]] = []
    for term in unique_terms:
        posting = index.get(term)
        if not isinstance(posting, dict) or not posting:
            return []
        postings_by_term.append(posting)

    if postings_by_term:
        matching_urls = set(postings_by_term[0].keys())
        for posting in postings_by_term[1:]:
            matching_urls &= set(posting.keys())
    else:
        if phrase_groups:
            first_phrase = phrase_groups[0]
            if not first_phrase:
                return []
            first_term_posting = index.get(first_phrase[0], {})
            if not isinstance(first_term_posting, dict):
                return []
            matching_urls = set(first_term_posting.keys())
        else:
            return []

    for phrase_terms in phrase_groups:
        if not phrase_terms:
            return []

        phrase_term_postings = []
        for phrase_term in phrase_terms:
            posting = index.get(phrase_term)
            if not isinstance(posting, dict) or not posting:
                return []
            phrase_term_postings.append(posting)

        candidate_urls = set(phrase_term_postings[0].keys())
        for posting in phrase_term_postings[1:]:
            candidate_urls &= set(posting.keys())

        phrase_matching_urls = {
            url for url in candidate_urls if _phrase_matches_url(phrase_terms, url, index)
        }
        matching_urls &= phrase_matching_urls

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
        for phrase_terms in phrase_groups:
            if _phrase_matches_url(phrase_terms, url, index):
                score += len(phrase_terms)
        scored_results.append((score, url))

    scored_results.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, url in scored_results]


__all__ = ["normalize_query", "indexed_words", "search"]