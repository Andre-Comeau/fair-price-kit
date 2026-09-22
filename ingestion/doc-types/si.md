# SI: Site Instruction (`--type si`)

Common handling: `change-documents-common.md`. Definitions and links: `relationships.md`.

**What differs:** a change with no expected price adjustment. Set `amount_type` to `"none"`. If the document does carry an amount or a "no cost" statement, record exactly what is stated; if a price appears where none was expected, flag it to the user rather than deciding what it means.

**Keep:** the instruction, its reason, any wording about cost or time reservation (e.g. contractor's right to claim), and references to spec sections and drawings.

**Links:** an SI can later grow into a CCN/CO if a price effect emerges. Link only on a stated reference or a well-founded, explained inference.
