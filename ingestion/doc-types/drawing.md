# Drawings (`--type drawing`)

**What it is:** visual PDFs (plans, sections, details, schedules). The meaning is mostly graphic; the text layer is only labels, notes, schedules and the title block.

**Set expectations with the user:** extracted text is scattered, in reading order that follows the drawing's layout, not a sentence flow. It supports search ("which sheet has the door schedule?") and notes/schedules, not visual interpretation. Do not describe or infer what a drawing shows from fragments.

**Extract drawings with `python tools/pdf_to_text.py IN.pdf OUT.md --raw`.** Layout mode pads large sheets with spaces (a 14-page structural set gave 9.9 million characters, 98% whitespace; raw mode gave about 195,000). Keep dimension lists intact: a scrub must never treat "450 450 450" as an ID or "300 300 2500" as a phone number (the patterns now require a cue).

**Expect notices that trip the marking check.** Owners often print a proprietary-information notice ("...confidential to the owner...") on every sheet. That is not a classification marking, but the check will stop the document; the user decides, the decision is logged, and a reviewed exception (`kb/gate-allow.txt`) keeps the scanner quiet about it afterwards. Title blocks name the designer and drafter as initial plus surname ("S. SURNAME"): the mapping needs that form as well as the full name.

**Extraction checks:** `pdf_to_text.py` reports low-text pages. Common causes: scanned drawings (need OCR; none is installed by default), text converted to outlines (unrecoverable as text), very large sheet sizes. Report these pages by number; do not invent content. Where the user wants visual content captured, they can add a short human-written description per sheet as a `notes` line in the sanitized text; label it `[USER NOTE]`.

**Title blocks are the highest identifying content on a drawing.** Keep: sheet number, sheet title, discipline, revision letter/number and date, scale. Replace: project name and number, owner, address, consultant names, stamps and seals, signatures, drawn/checked initials, file paths, plotting stamps (often contain usernames and folder names of the drafter's computer: remove).

**Chunking:** one chunk per page (one page = one sheet). `chunk_doc.py` tries to read a sheet number from a `SHEET NO:` or `DWG NO:` line; if it does not find one, set it by hand in the chunk's front matter (`"sheet": "A-101"`) after review, and rebuild the index.

**Metadata:** `--doc-id DWG-ARCH --title "Architectural drawings"`; set `discipline` via `--meta discipline='"architectural"'` (architectural, structural, mechanical, electrical, civil, landscape, other).

**Schedules and notes worth keeping intact:** finish, door, equipment and fixture schedules; general notes; revision clouds lists; legend text. Quantities in schedules can support estimating later.

**Links:** drawings are cited by specs and change documents ("Drawing A-101", "Sheet S-201"), and revision lists show which sheets a change touched. Those references are picked up by `xref`.

**Privacy note:** drawings of secure areas, security systems, or utilities can be sensitive even when unmarked. Apply stop rule 3 in `../RULEBOOK.md`.
