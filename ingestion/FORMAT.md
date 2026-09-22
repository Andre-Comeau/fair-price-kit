# Data formats

## Project workspace
```
P001/
  raw/         PRIVATE originals
  text/        PRIVATE <id>.raw.md (converted), <id>.pre.md (pre-scrubbed)
  private/     PRIVATE mapping.csv, LOG.md
  sanitized/   <id>.md          reviewed, identifier-free, page markers kept
  kb/
    masterformat.json  spec projects only: {"edition", "divisions": {"03": "title as this spec words it"}}
    INDEX.md   read first
    index.json machine lookup
    chunks/    <doc-id>__<section-or-page>.md
```
Ids are neutral and lower-case: `spec-vol1`, `dwg-arch`, `ccn-012`, `co-007`, `ci-003`, `cd-002`, `si-015`, `ea-004`. No project codes, no original filenames.

## sanitized/<id>.md
Plain Markdown text of the document with `<!-- page N -->` markers before each page. Optionally, change documents start with a metadata header block (`---`, `key: JSON` lines, `---`; prompt P6 in `COPILOT-MODE.md`). Both the Python chunker and the Power Automate flow copy the header into the chunk's front matter but ignore reserved keys (`id`, `doc_type`, `doc_id`, `doc_title`, `section`, `sheet`, `chunk_title`, `division`, `division_name`, `masterformat_edition`, `pages`, `chars`, `sanitization`), so a document cannot approve itself. Otherwise no front matter. Placeholders per `placeholders.md`. Tables from PDFs stay as aligned text (from `pdftotext -layout`); if a table matters for pricing, rewrite it as a Markdown table during review and keep the numbers exact.

## Chunk files (kb/chunks/*.md)
Front matter, then a blank line, then the sanitized body. Front-matter values are JSON (strings quoted, lists in brackets) so tools and LLMs can read them without a YAML library.

| Field | Meaning |
|---|---|
| `id` | unique chunk id: `<doc-id>__<suffix>` |
| `doc_type` | spec, drawing, ccn, co, ci, cd, si, ea, other |
| `doc_id` | document id, e.g. `CO-007`, `SPEC-VOL1` |
| `doc_title` | generic title (no identifying words) |
| `section` | spec section exactly as written: `03 30 00` (6-digit) or `03300` (older 5-digit) |
| `sheet` | sheet number if detected (drawing only) |
| `chunk_title` | section or sheet title |
| `division`, `division_name`, `masterformat_edition` | first two digits of the section number; name and edition come only from the project's `kb/masterformat.json` (edition is project dependent), omitted if that file is absent |
| `pages` | `[first, last]` page numbers in the source PDF |
| `chars` | body length |
| `sanitization` | `pending` or `approved`; only `approved` chunks are indexed |
| extra (`--meta`) | for change documents, see below |

Change-document metadata (set via `--meta key=json`; only what the document states, never guessed):
`number` (`"007"`), `date` (`"2026-03"`), `status` (`"issued"`, `"approved"`, `"pending"`, `"rejected"`), `amount` (number), `amount_type` (`"fixed"`, `"estimate"`, `"not-to-exceed"`, `"none"`, `"tbd"`), `currency` (`"CAD"`), `originator_role`, `recipient_role` (placeholders' roles), `reason_category` (`"owner-requested"`, `"unforeseen-condition"`, `"design-error"`, `"code"`, `"other"`), `spec_sections` (`["03 30 00"]`), `sheets` (`["A-101"]`), `related` (`[{"doc":"CCN-012","relation":"contemplated-by","confidence":"stated"}]`).
`confidence`: `stated` = the text itself names the other document; `inferred` = you matched by subject/amount/date (always say why in the chunk notes; the user verifies).

## index.json (schema `kb-index/1`)
```
{ "schema", "generated", "chunk_count",
  "chunks": [{ "id","path","doc_type","doc_id","doc_title","section","sheet","chunk_title","division","pages","chars","keywords","refs", ...change metadata }],
  "by_doc_type": { "spec": [chunk ids], ... },
  "by_division": { "03": [chunk ids], ... },
  "xref": { "CO-007": [chunk ids that mention it], "SEC-03 30 00": [...], "SHEET-A-101": [...] },
  "excluded": [{ "path", "reason" }] }
```
`refs` and `xref` are found by pattern (`CCN|CO|CI|CD|SI|EA` + number, "Section nn nn nn", "Drawing/Sheet A-101"); they are leads, not verified links ("CO 2 emissions" would match `CO-002`).

## INDEX.md
Generated. A per-document-type table (id, section/sheet, title, pages, keywords, refs) plus how to search and the excluded list. An AI reads it first, then opens only the chunks it needs.

## Differences between the Python tools and the Power Automate flows
The flows (`POWER-AUTOMATE.md`) produce the same chunk front matter and `INDEX.md` layout but: no `PART` sub-splitting of long sections, no sheet-number detection, no `keywords`/`refs`/`xref` (they need pattern matching), a shorter `INDEX.md` table (no refs/keywords columns), and `index.json` written as compact JSON. The Python tools remain the reference for the fuller format.

## Sizing
Default chunk cap 12,000 characters (about 3,000 tokens); longer spec sections split at `PART 1/2/3`, then at paragraph breaks. Change documents are normally one chunk. Drawings are one chunk per sheet page.
