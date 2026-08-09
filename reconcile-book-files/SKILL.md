---
name: reconcile-book-files
description: Reconcile a book CSV with actual local PDF or EPUB filenames, normalize Chinese or English titles, authors, and publishers, research ISBNs for duplicate title-and-publisher groups, safely rename book files and macOS AppleDouble sidecars, and verify strict one-to-one delivery without changing unauthorized CSV cells. Use when users ask to clean a book list, standardize 书籍名称/作者/出版社, search ISBNs, rename books by title, match CSV rows to real files, avoid dst_path-based matching, handle duplicate books, or process macOS ._ metadata files.
---

# Reconcile Book Files

Turn a source book CSV and a flat directory of book files into a verified delivery in which every value in the CSV title column equals exactly one visible file stem.

## Operating Contract

- Treat the source CSV and original book files as evidence. Never overwrite the source CSV.
- Calculate and record the source CSV SHA-256 before making changes.
- Inspect the directory's actual filenames. Never use `dst_path`, an export path, or a planned name as proof of a match.
- Exclude `._*` AppleDouble files from the visible-book count, but preserve or deliberately handle each sidecar together with its visible file.
- Change only columns explicitly authorized by the user. Default mutable columns are `书籍名称`, `作者`, `出版社`, and `ISBN` when ISBN enrichment is requested.
- Preserve every unauthorized cell byte-for-byte at the CSV value level, including blank values and row order.
- Do not infer uncertain titles, authors, publishers, editions, or ISBNs. Put unresolved items in an exception report.
- Perform a read-only inventory and dry run before any rename. Do not apply when counts, mappings, or target names are unresolved.

## Resource Routing

- For any task that edits or renames files, read [references/sop.md](references/sop.md) before designing the mapping.
- Use the standalone spreadsheet skill to read, write, and verify CSV structure correctly.
- Use the PDF skill when a filename alone is insufficient and the cover, title page, copyright page, or body must be inspected.
- Use Chrome control only when ISBN research depends on the user's browser state. Otherwise use authoritative web sources directly.
- Run `scripts/preflight.py` for a read-only baseline and `scripts/verify_delivery.py` for final acceptance.

## Workflow

### 1. Freeze The Inputs

Record these values before work begins:

- absolute source CSV path;
- absolute book-directory path;
- title, author, publisher, and ISBN column names;
- mutable-column allowlist;
- output CSV path;
- sidecar policy: preserve, ignore, or remove only with explicit approval;
- accepted book extensions and expected directory depth.

If the directory is supposed to be flat, treat every subdirectory as an exception.

### 2. Run Read-Only Preflight

Run:

```bash
python3 -B scripts/preflight.py \
  --csv "/absolute/source.csv" \
  --books "/absolute/books-directory" \
  --json "/absolute/preflight.json"
```

Confirm CSV dimensions, visible-book count, extension distribution, sidecar count, nested `._._*` files, duplicate filename keys, long filenames, and source hash. Explain AppleDouble files separately from real books; do not double the book count.

### 3. Match Rows To Actual Books

Build the row-to-file mapping from the CSV `书籍名称` value and the actual filename. Use progressively stronger evidence:

1. exact title-to-stem match;
2. normalized title match used only to locate candidates;
3. filename metadata such as ISBN, publisher, author, or sequence number;
4. cover, title page, copyright page, and body;
5. authoritative bibliographic sources.

Report each item as one of:

- `书名完全对应`;
- `书名相同但存在多个文件，需要进一步区分`;
- `文件名与 CSV 书名不对应`;
- `无法确认的异常文件`.

Normalization helps identify candidates but is not proof. Preserve a traceable evidence note for every non-exact match.

### 4. Normalize Bibliographic Fields

Apply the detailed rules in `references/sop.md` conservatively.

- Titles: remove book-title brackets, leading numbers, leading equals signs, decorative symbols, and duplicate spaces. Keep meaningful volume labels such as 上、中、下 and real edition information. Preserve native Chinese titles as Chinese and native English titles as English.
- Authors: remove only confirmed duplicate names and noise. Preserve meaningful roles such as 编著、主编、译. Do not merge people with similar names or discard role attribution.
- Publishers: remove address prefixes while preserving the complete, unambiguous publisher entity. Never reduce a name to an ambiguous fragment such as `大学出版社`.

Use the book itself as the primary authority when CSV text and file metadata disagree.

### 5. Resolve Duplicate Naming Groups

Choose the shortest filename stem that remains globally unique:

| Condition | Final stem |
|---|---|
| Base title is unique | `书名` |
| Base title repeats, publisher distinguishes it | `书名_出版社` |
| Title and publisher both repeat | `书名_出版社_ISBN` |
| Same verified ISBN still has multiple deliverable scans | `书名_出版社_ISBN_1`, `_2`, ... |

For title-and-publisher duplicates, search using `书名 + 出版社 + ISBN`. Verify ISBN-13 checksum and corroborate title, publisher, edition, and publication context. Never use an ISBN from a different edition merely to make a name unique. If no reliable ISBN is found, keep the existing value when safe and report the unresolved collision instead of guessing.

The final `书籍名称` cell must equal the final visible filename stem exactly, including publisher, ISBN, and sequence suffixes added for uniqueness.

### 6. Build And Review A Dry Run

Create a machine-readable mapping with at least:

- CSV row number;
- source title;
- source visible filename;
- normalized base title, author, and publisher;
- ISBN and evidence source when added;
- target title cell;
- target visible filename;
- source and target sidecar names;
- confidence and exception reason.

Before applying, prove that:

- every CSV row maps to one source visible file;
- every source visible file maps to one CSV row;
- every target stem is unique under the destination filesystem's normalization and case behavior;
- no target already exists outside the mapping;
- every target filename is within filesystem byte limits;
- unauthorized CSV cells are unchanged.

### 7. Apply As A Recoverable Transaction

Write a new CSV. Rename files in two phases through unique temporary names so cycles and swaps cannot overwrite data. Keep a rollback manifest and rename each retained AppleDouble sidecar with its visible file. Stop immediately on any unexpected collision or missing source.

Do not delete metadata files unless the user explicitly authorizes deletion. Never create nested sidecars such as `._._filename`.

### 8. Verify The Delivery

Run:

```bash
python3 -B scripts/verify_delivery.py \
  --source "/absolute/source.csv" \
  --final "/absolute/final.csv" \
  --books "/absolute/books-directory" \
  --mutable "书籍名称,作者,出版社,ISBN" \
  --sidecars preserve \
  --source-sha256 "recorded-source-digest" \
  --json "/absolute/verification.json"
```

Acceptance requires all of the following:

- source hash still matches;
- source and final CSV row counts match;
- no unauthorized header or cell changed;
- final title values and visible file stems form an exact one-to-one set;
- no duplicate target titles or filename keys remain;
- no missing or extra visible book files remain;
- retained sidecars correspond one-to-one and no `._._*` files exist;
- no temporary transaction files remain;
- every populated ISBN is a valid ISBN-13.

### 9. Report Clearly

Return the output CSV path, verification-report path, counts before and after, number of changed title/author/publisher/ISBN cells, rename count, duplicate groups resolved, ISBNs added with sources, unresolved exceptions, and confirmation that unauthorized data was unchanged.

## Stop Conditions

Do not mutate files when any of these conditions remains true:

- visible-book count and CSV data-row count differ without an explained mapping;
- a row or file has zero or multiple unresolved counterparts;
- duplicate target stems remain;
- an ISBN is required for uniqueness but cannot be verified;
- filesystem normalization or case behavior has not been tested for colliding names;
- an output CSV or rename target would be overwritten without explicit approval;
- the requested action would modify columns outside the allowlist.
