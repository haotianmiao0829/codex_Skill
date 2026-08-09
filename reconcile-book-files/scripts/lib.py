from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


def read_csv(target: str | Path) -> tuple[list[str], list[list[str]]]:
    path = Path(target)
    with path.open("r", encoding="utf-8-sig", errors="strict", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ValueError(f"CSV has no rows: {path}")
    return [str(value) for value in rows[0]], rows[1:]


def sha256_file(target: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(target).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def filename_key(value: str) -> str:
    return unicodedata.normalize("NFD", str(value)).casefold()


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", str(value))


def title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return "".join(character for character in normalized if character.isalnum())


def duplicate_groups(
    values: Iterable[str], key_function: Callable[[str], str]
) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for value in values:
        groups[key_function(value)].append(value)
    return [group for group in groups.values() if len(group) > 1]


def malformed_rows(rows: list[list[str]], expected_width: int) -> list[dict[str, int]]:
    return [
        {"csvRow": row_index, "columns": len(row), "expectedColumns": expected_width}
        for row_index, row in enumerate(rows, start=2)
        if len(row) != expected_width
    ]


def valid_isbn13(value: str) -> bool:
    if len(value) != 13 or not value.isascii() or not value.isdigit():
        return False
    if not value.startswith(("978", "979")):
        return False
    checksum = sum(
        int(digit) * (3 if index % 2 else 1)
        for index, digit in enumerate(value[:12])
    )
    return (10 - checksum % 10) % 10 == int(value[-1])


def write_json(target: str | Path | None, value: Any) -> None:
    if target is None:
        return
    Path(target).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))
