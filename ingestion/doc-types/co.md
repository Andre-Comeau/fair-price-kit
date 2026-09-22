# CO: Change Order (`--type co`)

Common handling: `change-documents-common.md`. Definitions and links: `relationships.md`.

**What differs:** an executed change with a stated price and/or time effect. `amount_type` is normally `"fixed"` (or `"not-to-exceed"` if stated). Capture add/deduct direction exactly as written (a deduct is a negative `amount`); keep the running contract-sum table if present.

**Keep:** breakdown lines, markups (overhead, profit, bonding, contingency, with the percentages and what they apply to), taxes, time extension, the revised contract total. These are the core evidence for fair-and-reasonable pricing.

**Links:** usually to a CCN, but not always; numbering is not sequential or one-to-one. Check for references to a CD that the CO now prices (`settles`), and to EAs (`authorized-by`). Link only when stated, or inferred with a written basis.
