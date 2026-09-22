# Change documents: common handling (CCN, CO, CI, CD, SI, EA)

Read `relationships.md` for definitions and linking rules first. Each type has a short guide with what differs.

## What these documents usually contain (expect; adjust after the first real sample)
Header (type, number, date, project identification, parties), description of the change and its reason, references (spec sections, drawings, related change documents, RFIs), pricing (lump sum or breakdown: labour, materials, equipment, subcontractor quotes, markups, taxes), time effect, approvals/signature block, sometimes attachments (quotes, backup, revised sheets).

## Sanitize focus
- Header: strip project name/number, contract numbers, party names (roles instead), addresses. Keep the type and number (`CO-007`), date, status.
- Pricing tables: keep every figure exactly. Replace subcontractor and supplier names with `[SUB-<TRADE>-n]` / `[VENDOR-n]`. Do not round, merge or "tidy" numbers.
- Signature blocks: names, titles, signatures, stamps -> role placeholders / `[SIGNATURE]`.
- Attached quotes: often contain letterhead, phone, email, bank or tax numbers, HST/GST registration numbers: replace. If an attachment is a separate document, treat it as its own document.
- Free text narratives can identify the site ("in the east wing of the ... building"): flag and ask.

## Chunking
One chunk per document (`--type <ccn|co|ci|cd|si|ea>`). A document longer than the size cap splits by page. Keep a document's attachments in the same `--doc-id` unless the user says otherwise.

## Metadata (via `--meta`; only what the document states)
`number`, `date`, `status`, `amount`, `amount_type`, `currency`, `originator_role`, `recipient_role`, `reason_category`, `spec_sections`, `sheets`, `related`. Formats in `../FORMAT.md`. Example:

```
python tools/chunk_doc.py sanitized/co-007.md --type co --doc-id CO-007 --title "Change order 007" \
  --out kb/chunks --approved --meta number='"007"' --meta amount=12500 --meta amount_type='"fixed"' \
  --meta currency='"CAD"' --meta status='"approved"' \
  --meta related='[{"doc":"CCN-012","relation":"contemplated-by","confidence":"stated"}]'
```

## Checks
- The stated total matches the sum of its lines; if it does not, keep both as written and flag the discrepancy to the user. Never correct silently.
- Amounts in different currencies or with/without taxes are labelled as the document states.
