from __future__ import annotations
import json
from pathlib import Path
from src import crawler, indexer, search

START_URL = "https://quotes.toscrape.com/"


# Interactive CLI for building/loading/inspecting/searching index data.
class SearchCLI:
    def __init__(self) -> None:
        self.index: indexer.InvertedIndex = {}

    # Start the interactive command loop.
    def run(self) -> None:
        print("Quotes Search Engine CLI")
        print("Commands: build, load, print [word], find <query>, help, exit")

        while True:
            try:
                raw_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                break

            if not raw_input:
                continue

            should_exit = self.process_command(raw_input)
            if should_exit:
                break

    # Process a single command. Returns True when CLI should exit.
    def process_command(self, command_line: str) -> bool:
        command, _, arguments = command_line.partition(" ")
        command = command.lower().strip()
        arguments = arguments.strip()

        if command in {"exit", "quit"}:
            print("Goodbye.")
            return True

        if command == "help":
            print("Available commands:")
            print("- build            Crawl site, build index, save to data/compiled_index.json")
            print("- load             Load index from data/compiled_index.json")
            print("- print [word]     Print indexed words or posting list for one word")
            print("- find <query>     Search pages that contain all query words")
            print("- exit             Exit the CLI")
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
        print("Starting crawl...")
        pages = crawler.crawl(START_URL)
        print(f"Crawl complete: {len(pages)} page(s) collected.")

        print("Building inverted index...")
        built_index = indexer.build_index(pages)
        print(f"Index built: {len(built_index)} unique word(s).")

        target_path = indexer.DEFAULT_INDEX_PATH
        print(f"Saving index to {target_path}...")
        if indexer.save_index(built_index, target_path):
            self.index = built_index
            print("Build complete.")
        else:
            print("Failed to save index.")

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
        print(f"Index loaded successfully ({len(self.index)} indexed word(s)).")

    def _print_index(self, argument: str) -> None:
        if not self.index:
            print("No index loaded. Use 'build' or 'load' first.")
            return

        if not argument:
            words = search.indexed_words(self.index)
            print(f"Indexed words ({len(words)}):")
            for word in words:
                print(word)
            return

        entry = indexer.get_word_entry(argument, self.index)
        if not entry:
            print(f"No indexed entry found for '{argument}'.")
            return

        print(f"Word '{argument}' appears in {len(entry)} page(s):")
        for url, payload in sorted(entry.items()):
            frequency = payload.get("frequency", 0)
            positions = payload.get("positions", [])
            print(f"- {url} (frequency={frequency}, positions={positions})")

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

        print(f"Found {len(matches)} matching page(s):")
        for url in matches:
            print(f"- {url}")


# Entrypoint for the interactive CLI.
def run_cli() -> None:
    SearchCLI().run()


if __name__ == "__main__":
    run_cli()
