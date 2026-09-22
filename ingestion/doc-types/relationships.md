# Change documents and how they relate

Definitions below are working definitions used by this kit. Confirm them against the general conditions of the contract in use (`../../OPEN-QUESTIONS.md` #9) and correct this file where they differ.

| Code | Name | Working definition |
|---|---|---|
| CCN | Contemplated Change Number | notice of a possible change, normally with a request for pricing |
| CO | Change Order | an executed change to the contract with a price/time effect; usually linked to a CCN, but not always, and numbering is not sequential or one-to-one |
| CI | Change Instruction | often a combined CCN and CO in one document |
| CD | Change Directive | a Change Order without a pre-set price |
| SI | Site Instruction | a change with no expected price adjustment |
| EA | Expenditure Authority | a tool for managing purchasing changes in a construction-manager delivery; usually follows a CO or CD, not always one-to-one |

## Linking rules (do not force a tidy chain)
- Link only on evidence. `confidence: "stated"` when the document text names the other document (e.g. "further to CCN-012"). `confidence: "inferred"` when you matched by subject, amount, date or spec section; then explain the basis and mark it for the user to verify.
- Never assume one-to-one. One CCN may lead to several COs or none; one CO may answer several CCNs; an EA may cover part of a CO or several. Numbers are not sequential across types.
- Record links as `related: [{"doc": "CCN-012", "relation": "...", "confidence": "stated"}]`. Suggested `relation` values: `contemplated-by`, `contemplates`, `priced-by`, `settles`, `authorized-by`, `authorizes`, `combines`, `supersedes`, `related`.
- A CD has no price at issue; the final price may appear later in a CO or EA. Do not copy an amount across documents; each document keeps its own stated amount and type.
- A SI normally carries no price; if one does, record the amount and flag it to the user.
- If a document references a number you do not have (missing from the batch), record the reference in `related` with `"present": false`, so gaps are visible.

## Why this matters for price justification
The fair-and-reasonable analysis often needs the trail: the contemplated change, the pricing back-up, the final order and the expenditure authority. The index's `xref` lets an AI pull that trail, and the `confidence` field says how far to trust each link.
