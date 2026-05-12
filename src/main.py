from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from src import crawler, indexer, search

START_URL = "https://quotes.toscrape.com/"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logger = logging.getLogger(__name__)


# Configure application-wide logging with optional file output.
def configure_logging() -> None:
    log_level_name = os.getenv("SEARCH_ENGINE_LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("SEARCH_ENGINE_LOG_FILE")

    level = getattr(logging, log_level_name, logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        try:
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except OSError as exc:
            logging.basicConfig(level=level, format=LOG_FORMAT, handlers=handlers, force=True)
            logger.warning("Could not enable log file '%s': %s", log_file, exc)
            return

    logging.basicConfig(level=level, format=LOG_FORMAT, handlers=handlers, force=True)


# Interactive CLI for building/loading/inspecting/searching index data.
class SearchCLI:
    def __init__(self) -> None:
        self.index: indexer.InvertedIndex = {}

    # Start the interactive command loop.
    def run(self) -> None:
        print("\n Quotes Search Engine CLI")
        print("Commands: build, load, print [word], find <query>, help, exit")

        while True:
            try:
                raw_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not raw_input:
                continue

            try:
                should_exit = self.process_command(raw_input)
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.exception("Unexpected command processing failure: %s", exc)
                print("An unexpected error occurred while processing the command.")
                should_exit = False
            if should_exit:
                break

    # Process a single command. Returns True when CLI should exit.
    def process_command(self, command_line: str) -> bool:
        if not isinstance(command_line, str):
            print("Invalid command input. Please enter text commands only.")
            return False

        command, _, arguments = command_line.partition(" ")
        command = command.lower().strip()
        arguments = arguments.strip()

        if command in {"exit", "quit"}:
            print("Goodbye.")
            return True

        if command == "help":
            print("\nAvailable commands:")
            print("- build            Crawl site, build index, save to data/compiled_index.json")
            print("- load             Load index from data/compiled_index.json")
            print("- print [word]     Print indexed words or posting list for one word")
            print("- find <query>     Search pages that contain all query words")
            print("- exit             Exit the CLI")
            print("- help             Show this command list\n")
            return False

        if command == "build":
            self._build_index()
            return False

        if command == "load":
            self._load_index()
            return False

        if command == "print":
            self._print_index(arguments)
            return False

        if command == "find":
            self._find(arguments)
            return False

        print(f"Invalid command: {command}. Type 'help' for available commands.")
        return False

    def _build_index(self) -> None:
        print("\n[Build] Starting crawl...")
        pages = crawler.crawl(START_URL)
        print(f"[Build] Crawl complete: {len(pages)} page(s) collected.")
        if not pages:
            print("[Build] No pages were collected. Index not updated.")
            return

        print("[Build] Building inverted index...")
        built_index = indexer.build_index(pages)
        print(f"[Build] Index built: {len(built_index)} unique word(s).")
        if not built_index:
            print("[Build] Index is empty. Nothing to save.")
            return

        target_path = indexer.DEFAULT_INDEX_PATH
        print(f"[Build] Saving index to {target_path}...")
        if indexer.save_index(built_index, target_path):
            self.index = built_index
            print("[Build] Completed.\n")
        else:
            print("[Build] Failed to save index.\n")

    def _load_index(self) -> None:
        index_path = Path(indexer.DEFAULT_INDEX_PATH)
        if not index_path.exists():
            print(f"Index file not found: {index_path}")
            return

        try:
            with index_path.open("r", encoding="utf-8") as file_handle:
                raw = json.load(file_handle)
        except json.JSONDecodeError:
            print(f"Index file is corrupted: {index_path}")
            return
        except OSError as exc:
            print(f"Failed to read index file {index_path}: {exc}")
            return

        loaded_index = indexer.load_index(index_path)
        if loaded_index == {} and raw != {}:
            print(f"Index file has invalid structure: {index_path}")
            return

        self.index = loaded_index
        print(f"Index loaded successfully ({len(self.index)} indexed word(s)).\n")

    def _print_index(self, argument: str) -> None:
        if not self.index:
            print("No index loaded. Use 'build' or 'load' first.")
            return

        if not argument:
            words = search.indexed_words(self.index)
            print(f"\nIndexed words ({len(words)}):")
            for index_num, word in enumerate(words, start=1):
                print(f"{index_num:>3}. {word}")
            print()
            return

        entry = indexer.get_word_entry(argument, self.index)
        if not entry:
            print(f"No indexed entry found for '{argument}'.")
            return

        print(f"\nWord '{argument}' appears in {len(entry)} page(s):")
        for index_num, (url, payload) in enumerate(sorted(entry.items()), start=1):
            frequency = payload.get("frequency", 0)
            positions = payload.get("positions", [])
            print(f"{index_num:>3}. {url}")
            print(f"     frequency={frequency}, positions={positions}")
        print()

    def _find(self, query: str) -> None:
        if not self.index:
            print("No index loaded. Use 'build' or 'load' first.")
            return

        if not query.strip():
            print("Please provide a search query. Example: find life")
            return

        matches = search.search(query, self.index)
        if not matches:
            print("No matching pages found.")
            return

        print(f"\nFound {len(matches)} matching page(s):")
        for index_num, url in enumerate(matches, start=1):
            print(f"{index_num:>3}. {url}")
        print()


# Entrypoint for the interactive CLI.
def run_cli() -> None:
    configure_logging()
    SearchCLI().run()


if __name__ == "__main__":
    run_cli()
