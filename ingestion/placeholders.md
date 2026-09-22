# Placeholder scheme (role-based generic names)

Format: `[ROLE]` or `[ROLE-n]`, upper case, square brackets. A placeholder names the *role*, never the party. Number multiples in order of first appearance within the project (`-1`, `-2`). Add roles when needed; keep them generic and record new ones here.

| Placeholder | Replaces |
|---|---|
| `[OWNER]` | the owner / client organization |
| `[OWNER-PM]`, `[OWNER-REP]`, `[OWNER-CONTRACTING]` | owner staff by role |
| `[CM]` | construction manager (organization) |
| `[PERSON-CM-PM-1]`, `[PERSON-CM-SUPT-1]` | CM staff by role |
| `[GC]` | general contractor (organization) |
| `[PERSON-GC-PM-1]` | GC staff by role |
| `[SUB-<TRADE>-n]` | subcontractor or trade contractor; TRADE = MECH, ELEC, STRUCT-STEEL, CONCRETE, ROOFING, ... |
| `[CONSULTANT-ARCH-n]`, `[CONSULTANT-STRUCT-n]`, `[CONSULTANT-MECH-n]`, `[CONSULTANT-ELEC-n]`, `[CONSULTANT-COST-n]`, `[CONSULTANT-<DISCIPLINE>-n]` | design and other consultants |
| `[PERSON-<ORG-ROLE>-n]` | any other named individual, by their organization and role |
| `[VENDOR-n]` | supplier or vendor not covered above |
| `[BIDDER-n]` | a named bidder or proponent |
| `[MANUFACTURER-n]` | manufacturer or product brand (if the user chose to replace them) |
| `[PROJECT]` | project name |
| `[SITE]`, `[BUILDING-n]`, `[ROOM-n]` | site, building, identifying room names |
| `[ADDRESS]`, `[POSTAL-CODE]`, `[COORDINATES]`, `[MUNICIPALITY]` | location details |
| `[CONTRACT-NO]`, `[PO-NO]`, `[SOLICITATION-NO]`, `[FILE-NO]` | identifiers |
| `[EMAIL]`, `[PHONE]`, `[BUSINESS-NO]`, `[ID-NUMBER]`, `[URL]` | contact and ID patterns (set by `tools/prescrub.py`) |
| `[SIGNATURE]`, `[STAMP]`, `[LOGO]`, `[PERSON]` | signatures, seals, logos; generic person (from prescrub, refine to a role when known) |
| `[PARTY-?n]` | provisional: role unknown; must be resolved before approval |

Rules: same real party -> same placeholder everywhere in the project. Record assignments in `private/mapping.csv` only. If a placeholder would still identify a party (e.g. `[SUB-GEOTHERMAL-1]` when only one such trade exists in a small market), ask the user whether to generalize the trade.
