# CCN: Contemplated Change Number (`--type ccn`)

Common handling: `change-documents-common.md`. Definitions and links: `relationships.md`.

**What differs:** a CCN is a notice of a possible change, usually with a request for pricing. Its amount, if present, is a request or an estimate, not an agreed price: set `amount_type` to `"estimate"` or `"none"` accordingly, and `status` to what the document says (e.g. `"issued"`).

**Keep:** the description of the contemplated change, the response requested (pricing due date), references to spec sections and drawings, and any pricing the contractor returned (may be a separate document; link, don't merge).

**Links:** may lead to one or several COs, or to none if withdrawn. Look for "further to", "in response to", "revised CCN"; a later CCN may supersede an earlier one (`supersedes`). Do not assume the next CO number belongs to it.
