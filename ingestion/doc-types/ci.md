# CI: Change Instruction (`--type ci`)

Common handling: `change-documents-common.md`. Definitions and links: `relationships.md`.

**What differs:** often a combined CCN and CO: it both describes the change and carries the price and instruction to proceed. Record it as one document (`doc_type: "ci"`); do not split it into a CCN and a CO.

**Metadata:** capture both the request side (description, response requested) and the order side (`amount`, `amount_type`, `status`). If the amount is stated as an estimate and later finalized elsewhere, keep the stated type and link the later document.

**Links:** it may replace the usual CCN-then-CO pair, so its `related` list may be short. It may be followed by EAs. Look for references to earlier CCNs it absorbs (`combines`).
