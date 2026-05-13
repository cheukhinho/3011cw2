# Quotes Search Engine CLI

## 1. Project Overview

This project is a Python command-line search engine for crawling and searching content from:
https://quotes.toscrape.com/

It crawls pages, extracts text, builds an inverted index, saves/loads the index as JSON, and provides an interactive CLI to query indexed content.

## 2. Features

- **Crawler** with URL normalization, internal-link extraction, duplicate prevention, and politeness delay
- **Inverted index** with token positions and frequencies
- **CLI search** with single-word, multi-word (AND), and quoted phrase search
- **Persistence** via `data/compiled_index.json`
- **Comprehensive pytest suite** for crawler, indexer, search, and CLI command handling

## 3. Architecture Overview

- `src/crawler.py`
  - Fetches pages safely
  - Normalizes URLs
  - Extracts internal links and visible text
  - Performs BFS crawl with delay controls
- `src/indexer.py`
  - Tokenizes and normalizes text
  - Builds inverted index with frequency and position tracking
  - Saves/loads validated JSON index files
- `src/search.py`
  - Normalizes queries
  - Runs ranked search over the inverted index
  - Supports quoted phrase matching using positional postings
- `src/main.py`
  - Implements interactive CLI commands (`build`, `load`, `print`, `find`, `help`, `exit`)
  - Configures consistent logging and user-facing output formatting

## 4. Installation Instructions

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 5. Usage Instructions

Run the CLI:

```bash
python -m src.main
```

Example session:

```text
> build
> load
> print wisdom
> find good friends
> find "good friends"
```

## 6. Testing Instructions

Run all tests:

```bash
python -m pytest -q
```

Optional coverage report:

```bash
python -m pytest --cov=src --cov-report=term-missing
```

## 7. Design Decisions

- **Data structure choice**
  - Inverted index: `term -> url -> {frequency, positions}` for fast lookup and phrase support.
- **Indexing strategy**
  - Lowercasing + punctuation cleanup + whitespace normalization.
- **Search algorithm**
  - AND semantics for multi-term queries.
  - Ranking by combined term frequency (plus phrase-match bonus).
- **Trade-offs**
  - Simpler tokenizer for readability and maintainability.
  - JSON persistence for portability over maximum performance.

## 8. Error Handling

The system handles failures gracefully without unexpected crashes:

- Request failures/timeouts and non-HTML responses
- Invalid URLs and malformed user queries
- Missing index files and corrupted/malformed JSON
- Empty pages/documents and invalid command inputs

Warnings/errors are logged while CLI messages remain user-friendly.

## 9. GenAI Usage Declaration

Generative AI was used as an engineering assistant for:

- test coverage gap identification
- documentation drafting and refinement
- code quality hardening suggestions (logging, validation, defensive handling)

All generated content was manually reviewed, validated with tests, and corrected where needed to match project requirements and behavior.