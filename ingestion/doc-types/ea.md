# EA: Expenditure Authority (`--type ea`)

Common handling: `change-documents-common.md`. Definitions and links: `relationships.md`.

**What differs:** a tool for managing purchasing change in a construction-manager delivery. It authorizes spending on a trade or package and usually follows a CO or CD, but not always one-to-one: one EA may cover part of a CO or several. Its amounts are authorizations against a package budget, not necessarily the contract change amount.

**Keep:** the package or trade (as a role: `[SUB-<TRADE>-n]`), the authorized amount and how it is derived, prior authorized total, remaining budget or contingency drawn (whichever the document shows), and the CO/CD it cites.

**Metadata:** `amount` = the authorized amount as written; `amount_type` per the document (`"fixed"`, `"not-to-exceed"`); add `budget_line` via `--meta budget_line='"<generic label>"'` if the document has one.

**Links:** `authorizes` / `authorized-by` relations. Do not sum EAs to reproduce a CO or the reverse; keep each document's own numbers and let the user reconcile.
