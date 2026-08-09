#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
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
    valid_isbn13,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only final verification for a reconciled book delivery."
    )
    parser.add_argument("--source", required=True, help="Original CSV")
    parser.add_argument("--final", required=True, help="Final CSV")
    parser.add_argument("--books", required=True, help="Final flat book directory")
    parser.add_argument("--mutable", default="书籍名称,作者,出版社,ISBN")
    parser.add_argument("--title-column", default="书籍名称")
    parser.add_argument("--isbn-column", default="ISBN")
    parser.add_argument("--sidecars", choices=("preserve", "ignore"), default="preserve")
    parser.add_argument("--source-sha256")
    parser.add_argument("--json", help="Optional JSON report path")
    return parser.parse_args()


def duplicate_values(values: list[str]) -> list[str]:
    counts = Counter(values)
    return [value for value, count in counts.items() if count > 1]


def main() -> int:
    args = parse_args()
    source_path = Path(args.source).resolve()
    final_path = Path(args.final).resolve()
    books_path = Path(args.books).resolve()
    mutable_columns = {value.strip() for value in args.mutable.split(",") if value.strip()}

    source_headers, source_rows = read_csv(source_path)
    final_headers, final_rows = read_csv(final_path)
    source_hash = sha256_file(source_path)
    malformed_source_rows = malformed_rows(source_rows, len(source_headers))
    malformed_final_rows = malformed_rows(final_rows, len(final_headers))
    source_header_index = {header: index for index, header in enumerate(source_headers)}
    final_header_index = {header: index for index, header in enumerate(final_headers)}
    if args.title_column not in final_header_index:
        raise ValueError(f"Final CSV is missing title column: {args.title_column}")

    unauthorized_header_changes: list[dict[str, str]] = []
    for header in source_headers:
        if header not in final_header_index:
            unauthorized_header_changes.append({"type": "missing-source-header", "header": header})
    for header in final_headers:
        if header not in source_header_index and header not in mutable_columns:
            unauthorized_header_changes.append({"type": "unauthorized-new-header", "header": header})
    surviving_source_headers = [
        header for header in final_headers if header in source_header_index
    ]
    source_header_order_changed = surviving_source_headers != source_headers

    unauthorized_cell_changes: list[dict[str, object]] = []
    comparable_rows = min(len(source_rows), len(final_rows))
    for row_index in range(comparable_rows):
        source_row = source_rows[row_index]
        final_row = final_rows[row_index]
        for header in source_headers:
            if header in mutable_columns or header not in final_header_index:
                continue
            source_column = source_header_index[header]
            final_column = final_header_index[header]
            source_value = source_row[source_column] if source_column < len(source_row) else ""
            final_value = final_row[final_column] if final_column < len(final_row) else ""
            if source_value != final_value:
                unauthorized_cell_changes.append(
                    {"csvRow": row_index + 2, "column": header}
                )

    entries = list(books_path.iterdir())
    all_files = [entry.name for entry in entries if entry.is_file()]
    directories = [entry.name for entry in entries if entry.is_dir()]
    nested_sidecars = [name for name in all_files if name.startswith("._._")]
    sidecars = [
        name for name in all_files if name.startswith("._") and not name.startswith("._._")
    ]
    other_hidden_files = [
        name for name in all_files if name.startswith(".") and not name.startswith("._")
    ]
    book_files = [name for name in all_files if not name.startswith(".")]
    book_stems = [Path(name).stem for name in book_files]

    title_column = final_header_index[args.title_column]
    final_titles = [
        row[title_column] if title_column < len(row) else "" for row in final_rows
    ]
    title_values = {nfc(title) for title in final_titles}
    stem_values = {nfc(stem) for stem in book_stems}
    missing_files = [title for title in final_titles if nfc(title) not in stem_values]
    extra_files = [stem for stem in book_stems if nfc(stem) not in title_values]
    duplicate_final_titles = duplicate_groups(final_titles, filename_key)
    duplicate_book_stems = duplicate_groups(book_stems, filename_key)
    temporary_files = [
        name
        for name in all_files
        if re.search(r"(?:codex[-_.]|\.tmp$|\.stage$)", name, flags=re.IGNORECASE)
    ]
    long_filenames = [name for name in book_files if len(name.encode("utf-8")) > 253]

    expected_sidecars = {nfc(f"._{name}") for name in book_files}
    sidecar_values = {nfc(name) for name in sidecars}
    missing_sidecars = []
    extra_sidecars = []
    if args.sidecars == "preserve":
        missing_sidecars = [
            f"._{name}" for name in book_files if nfc(f"._{name}") not in sidecar_values
        ]
        extra_sidecars = [
            name for name in sidecars if nfc(name) not in expected_sidecars
        ]

    invalid_isbn: list[dict[str, object]] = []
    if args.isbn_column in final_header_index:
        isbn_column = final_header_index[args.isbn_column]
        for row_index, row in enumerate(final_rows, start=2):
            isbn = (row[isbn_column] if isbn_column < len(row) else "").strip()
            if isbn and not valid_isbn13(isbn):
                invalid_isbn.append({"csvRow": row_index, "isbn": isbn})

    failures: dict[str, object] = {
        "sourceHashMismatch": bool(
            args.source_sha256 and source_hash != args.source_sha256
        ),
        "rowCountMismatch": len(source_rows) != len(final_rows),
        "duplicateSourceHeaders": duplicate_values(source_headers),
        "duplicateFinalHeaders": duplicate_values(final_headers),
        "malformedSourceRows": malformed_source_rows,
        "malformedFinalRows": malformed_final_rows,
        "sourceHeaderOrderChanged": source_header_order_changed,
        "unauthorizedHeaderChanges": unauthorized_header_changes,
        "unauthorizedCellChanges": unauthorized_cell_changes,
        "missingFiles": missing_files,
        "extraFiles": extra_files,
        "duplicateFinalTitles": duplicate_final_titles,
        "duplicateBookStems": duplicate_book_stems,
        "missingSidecars": missing_sidecars,
        "extraSidecars": extra_sidecars,
        "nestedSidecars": nested_sidecars,
        "unexpectedDirectories": directories,
        "temporaryFiles": temporary_files,
        "filenamesOver253Bytes": long_filenames,
        "invalidISBN": invalid_isbn,
    }
    failure_count = sum(
        int(value) if isinstance(value, bool) else len(value)
        for value in failures.values()
    )

    result = {
        "mode": "read-only-final-verification",
        "sourceCsv": str(source_path),
        "finalCsv": str(final_path),
        "booksDirectory": str(books_path),
        "sourceCsvSha256": source_hash,
        "sourceCsvHashMatchesExpected": (
            not failures["sourceHashMismatch"] if args.source_sha256 else None
        ),
        "sourceDimensions": [len(source_rows) + 1, len(source_headers)],
        "finalDimensions": [len(final_rows) + 1, len(final_headers)],
        "bookFiles": len(book_files),
        "sidecars": len(sidecars),
        "nestedSidecars": len(nested_sidecars),
        "otherHiddenFiles": len(other_hidden_files),
        "directories": len(directories),
        "finalTitles": len(final_titles),
        "failureCount": failure_count,
        "status": "failed" if failure_count else "passed",
        "failures": failures,
    }
    write_json(args.json, result)
    print_json(result)
    return 1 if failure_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
