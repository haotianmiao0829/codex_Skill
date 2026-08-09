#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True

from lib import (
    duplicate_groups,
    filename_key,
    malformed_rows,
    nfc,
    print_json,
    read_csv,
    sha256_file,
    title_key,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only inventory for reconciling a book CSV and directory."
    )
    parser.add_argument("--csv", required=True, help="Source or candidate CSV")
    parser.add_argument("--books", required=True, help="Flat book directory")
    parser.add_argument("--title-column", default="书籍名称")
    parser.add_argument("--json", help="Optional JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    books_path = Path(args.books).resolve()
    headers, data_rows = read_csv(csv_path)
    if args.title_column not in headers:
        raise ValueError(f"Missing title column: {args.title_column}")
    title_column = headers.index(args.title_column)
    malformed_csv_rows = malformed_rows(data_rows, len(headers))

    entries = list(books_path.iterdir())
    all_files = [entry.name for entry in entries if entry.is_file()]
    directories = [entry.name for entry in entries if entry.is_dir()]
    nested_sidecars = [name for name in all_files if name.startswith("._._")]
    sidecars = [
        name for name in all_files if name.startswith("._") and not name.startswith("._._")
    ]
    hidden_files = [
        name for name in all_files if name.startswith(".") and not name.startswith("._")
    ]
    book_files = [name for name in all_files if not name.startswith(".")]

    book_file_set = {nfc(name) for name in book_files}
    sidecar_set = {nfc(name) for name in sidecars}
    orphan_sidecars = [
        name for name in sidecars if nfc(name[2:]) not in book_file_set
    ]
    missing_sidecars = [
        name for name in book_files if nfc(f"._{name}") not in sidecar_set
    ]
    extensions = Counter(Path(name).suffix.lower() or "[no extension]" for name in book_files)

    titles = [str(row[title_column]) if title_column < len(row) else "" for row in data_rows]
    stems = [Path(name).stem for name in book_files]
    stem_set = {nfc(stem) for stem in stems}
    exact_stem_matches = sum(nfc(title) in stem_set for title in titles)
    filename_duplicates = duplicate_groups(book_files, filename_key)
    stem_duplicates = duplicate_groups(stems, filename_key)
    title_duplicates = duplicate_groups((title for title in titles if title), title_key)
    long_filenames = [name for name in book_files if len(name.encode("utf-8")) > 253]

    ready = (
        len(data_rows) == len(book_files)
        and not filename_duplicates
        and not stem_duplicates
        and not nested_sidecars
        and not directories
        and not malformed_csv_rows
    )
    result = {
        "mode": "read-only-preflight",
        "sourceCsv": str(csv_path),
        "booksDirectory": str(books_path),
        "sourceCsvSha256": sha256_file(csv_path),
        "csvRowsIncludingHeader": len(data_rows) + 1,
        "csvDataRows": len(data_rows),
        "csvColumns": len(headers),
        "headers": headers,
        "titleColumn": args.title_column,
        "bookFiles": len(book_files),
        "sidecars": len(sidecars),
        "nestedSidecars": len(nested_sidecars),
        "otherHiddenFiles": len(hidden_files),
        "directories": len(directories),
        "extensionCounts": dict(sorted(extensions.items())),
        "exactTitleToStemMatches": exact_stem_matches,
        "titleDuplicateGroups": len(title_duplicates),
        "normalizedFilenameDuplicateGroups": len(filename_duplicates),
        "normalizedStemDuplicateGroups": len(stem_duplicates),
        "missingSidecars": len(missing_sidecars),
        "orphanSidecars": len(orphan_sidecars),
        "filenamesOver253Bytes": len(long_filenames),
        "malformedCsvRows": len(malformed_csv_rows),
        "status": "ready-for-mapping" if ready else "needs-review",
        "samples": {
            "directories": directories[:20],
            "nestedSidecars": nested_sidecars[:20],
            "missingSidecars": missing_sidecars[:20],
            "orphanSidecars": orphan_sidecars[:20],
            "normalizedFilenameDuplicates": filename_duplicates[:10],
            "normalizedStemDuplicates": stem_duplicates[:10],
            "titleDuplicates": title_duplicates[:10],
            "longFilenames": long_filenames[:20],
            "malformedCsvRows": malformed_csv_rows[:20],
        },
    }
    write_json(args.json, result)
    print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
