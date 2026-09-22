# CD: Change Directive (`--type cd`)

Common handling: `change-documents-common.md`. Definitions and links: `relationships.md`.

**What differs:** a Change Order without a pre-set price: work is directed to proceed and the price is settled later. Set `amount_type` to `"tbd"` (or `"not-to-exceed"` / `"estimate"` if the document states one). Do not write an amount that is not in the document.

**Keep:** the basis on which the price will be determined (time and materials, unit rates, cost plus, agreed markups, cost-reporting requirements). This is central to later fair-and-reasonable review.

**Links:** the final price usually appears in a later CO or EA. Link only when stated, or inferred with a basis, and say that the CD had no price at issue. If no later document is in the batch, record `"present": false` so the gap is visible.
