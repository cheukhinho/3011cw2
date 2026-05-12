from __future__ import annotations
from collections import defaultdict
import json
import logging
from pathlib import Path
import re
from typing import Any


logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("data/compiled_index.json")
TOKEN_PATTERN = re.compile(r"\w+")

WordEntry = dict[str, dict[str, Any]]
InvertedIndex = dict[str, WordEntry]


# Tokenize text into lowercase words with punctuation removed.
def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        logger.warning("Non-string text received for tokenization; returning empty tokens")
        return []

    lowered_text = text.lower()
    normalized_text = re.sub(r"[^\w\s]", " ", lowered_text)
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()

    if not normalized_text:
        return []

    return TOKEN_PATTERN.findall(normalized_text)


# Build an inverted index from crawled pages.
def build_index(pages: list[dict[str, Any]]) -> InvertedIndex:
    if not isinstance(pages, list):
        logger.warning("Malformed pages input (expected list); returning empty index")
        return {}

    index: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    processed_urls: set[str] = set()
    indexed_pages = 0
    indexed_tokens = 0

    for page in pages:
        if not isinstance(page, dict):
            logger.warning("Malformed page entry skipped (expected dict)")
            continue

        url = page.get("url")
        text = page.get("text")

        if not isinstance(url, str) or not url.strip():
            logger.warning("Page without valid URL skipped")
            continue

        if url in processed_urls:
            logger.warning("Duplicate page URL skipped: %s", url)
            continue

        if not isinstance(text, str) or not text.strip():
            logger.warning("Empty or missing page text skipped for URL: %s", url)
            processed_urls.add(url)
            continue

        tokens = tokenize(text)
        if not tokens:
            logger.warning("No indexable tokens found; skipped URL: %s", url)
            processed_urls.add(url)
            continue

        for position, token in enumerate(tokens):
            document_entry = index[token].setdefault(url, {"frequency": 0, "positions": []})
            document_entry["frequency"] += 1
            document_entry["positions"].append(position)

        processed_urls.add(url)
        indexed_pages += 1
        indexed_tokens += len(tokens)
        logger.info("Indexed page %s (%d tokens)", url, len(tokens))

    logger.info(
        "Indexing complete: %d pages indexed, %d unique terms, %d total tokens",
        indexed_pages,
        len(index),
        indexed_tokens,
    )
    return dict(index)


# Save an inverted index to disk in JSON format.
def save_index(index: InvertedIndex, filepath: str | Path = DEFAULT_INDEX_PATH) -> bool:
    path = Path(filepath)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file_handle:
            json.dump(index, file_handle, indent=2, ensure_ascii=False, sort_keys=True)
        logger.info("Saved index to %s", path)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Failed to save index to %s: %s", path, exc)
        return False


# Validate that loaded JSON matches expected inverted-index structure.
def _is_valid_index_structure(index_data: Any) -> bool:
    if not isinstance(index_data, dict):
        return False

    for term, docs in index_data.items():
        if not isinstance(term, str) or not isinstance(docs, dict):
            return False

        for url, payload in docs.items():
            if not isinstance(url, str) or not isinstance(payload, dict):
                return False

            frequency = payload.get("frequency")
            positions = payload.get("positions")

            if not isinstance(frequency, int) or frequency <= 0:
                return False

            if (
                not isinstance(positions, list)
                or not positions
                or not all(isinstance(pos, int) and pos >= 0 for pos in positions)
            ):
                return False
            
            if len(positions) != frequency:
                return False

    return True


# Load an inverted index from disk, returning an empty index on failure.
def load_index(filepath: str | Path = DEFAULT_INDEX_PATH) -> InvertedIndex:
    path = Path(filepath)

    try:
        with path.open("r", encoding="utf-8") as file_handle:
            loaded_index = json.load(file_handle)
    except FileNotFoundError:
        logger.warning("Index file not found: %s", path)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON index file at %s: %s", path, exc)
        return {}
    except OSError as exc:
        logger.error("Failed to load index file %s: %s", path, exc)
        return {}

    if not _is_valid_index_structure(loaded_index):
        logger.error("Loaded index has invalid structure: %s", path)
        return {}

    logger.info("Loaded index from %s", path)
    return loaded_index


# Return the posting entry for a word with case-insensitive lookup.
def get_word_entry(word: str, index: InvertedIndex) -> WordEntry:
    if not isinstance(index, dict):
        logger.warning("Malformed index input (expected dict)")
        return {}

    tokens = tokenize(word)
    if not tokens:
        return {}

    if len(tokens) != 1:
        logger.warning("Expected a single word for lookup; recieved %d tokens", len(tokens))
        return {}
    
    normalized_word = tokens[0]
    return index.get(normalized_word, {})


__all__ = [
    "tokenize",
    "build_index",
    "save_index",
    "load_index",
    "get_word_entry",
    "DEFAULT_INDEX_PATH",
]