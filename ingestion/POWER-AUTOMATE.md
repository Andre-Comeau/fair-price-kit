# Power Automate build guide: the gates and chunking, without Python or PowerShell

Assumptions (planning assumptions recorded 2026-09-21, none verified; register `ASSUMPTION-PLANNING`): no Python or PowerShell on the target computer; Microsoft Power Automate is available; Copilot is capable of and permitted to handle the documents; flows can be created with the **SharePoint and Outlook** connectors. Teams is not used and Office Scripts are not wanted, so Power Automate alone is the route. This guide takes the checks and the chunking that the Python tools do and rebuilds them as cloud flows over a SharePoint library. Copilot still does the language work (extraction and sanitization, `COPILOT-MODE.md` prompts P1-P3, P5, P6).

**Status: designed from Microsoft's documentation, NOT yet built or run.** The algorithm was validated in Python (`tools/test/flow_reference.py`, which mirrors each expression below). Action names, menu labels and connector behaviour can differ in your tenant; test every flow on the synthetic fixtures (section 7) before any real document. Anything marked *(verify)* is something I could not confirm.

## 1. What cloud flows can and cannot do

Per community write-ups and Microsoft's ideas forum (Microsoft's function reference lists no regex function): cloud flows have **no built-in regular-expression support**. `split`, `substring`, `indexOf`, `replace`, `join`, `contains` (case-sensitive: wrap both sides in `toLower`), `startsWith`/`endsWith` (case-sensitive), `skip`/`take`, `if`, `json`, `string`, `coalesce` all exist; a newline must be written `decodeUriComponent('%0A')` (a typed `\n` is not a newline). `.md` files come back from *Get file content* as plain text (if you get a base64 object instead, use the `base64ToString` form in section 5).

| Python tool | In Power Automate | Difference |
|---|---|---|
| `scan_sensitive.py` / `prescrub.py` patterns (email, phone, postal code, addresses, company suffixes, contract numbers) | **not possible** without regex | replaced by: (a) exact-match check of every value in your private mapping list, (b) marking words, (c) `@` / `http` / `www.` characters, (d) unresolved `[PARTY-?n]`; plus Copilot audit P3 and your review |
| approval flag | **Outlook *Send email with options*** (Approve/Reject buttons), logged in `IngestLog` | the record is the log row plus the email; anyone with access to your mailbox could click |
| `chunk_doc.py` | Flow 2 (split on literal `SECTION `, page markers) | no `PART` sub-split; no sheet-number detection; no `refs` |
| `build_index.py` | Flow 3 | no keywords or `xref` (need regex); includes leak re-check |

The mapping-list check is the strongest gate here: it stops any *known* party (a name you already replaced once) from surviving in a footer or signature block. It cannot find a name nobody has recorded, so the audit and your review still matter.

## 2. Prerequisites (ask IT; all standard, no premium connectors used)
- A SharePoint site, private (members: you, and IT if they need it), no external sharing. The library and list below live there.
- Confirmed by the user: cloud flows with the SharePoint and Office 365 Outlook connectors. Not assumed: the Approvals connector (the approval below uses Outlook instead) and Teams (untried; not used). Still ask whether a data-loss-prevention policy limits combining them.
- Flow run history stores each action's inputs and outputs (your document text) for the flow owner. **Turn on *Secure inputs* and *Secure outputs*** (action Settings -> Security) on every action that touches document text or the mapping list, as marked below. Community documentation says a secured output makes downstream actions that reference it secured too *(verify)*.
- Files are named with lower-case letters, digits and hyphens only, one dot (`spec-vol1.md`, `co-007.md`). The name prefix sets the document type: `spec-`, `dwg-`, `ccn-`, `co-`, `ci-`, `cd-`, `si-`, `ea-`, anything else = `other`.

## 3. SharePoint layout
Library `Ingestion`, folder per project (`P001`):
```
P001/raw/                 originals             (private)
P001/text/                Copilot extraction    (private)
P001/sanitized-review/    sanitized .md, awaiting the gate + your approval
P001/sanitized-approved/  written ONLY by Flow 1 after approval
P001/kb/chunks/           written by Flow 2
P001/kb/INDEX.md, index.json, masterformat.json   (Flow 3 writes the first two)
```
List `Mapping` (private; this is the re-identification key: restrict it tightly): columns `Title` (the placeholder, e.g. `[SUB-MECH-1]`), `Role`, `RealValue` (single line of text), `Project`, `FirstSeenDoc`. List `IngestLog`: `Title` (doc name), `Project`, `Step`, `Result`, `Detail` (counts and placeholders only, **never document text or real values**), plus the built-in Created.
Put the real values into `Mapping` as you sanitize (Copilot's P2 output 2; paste rows or use *Edit in grid view*).

## 3b. Building it: tips for a first flow
- **Name every action exactly as this guide names it** (`text`, `lower`, `Leaks`, ...). Expressions refer to actions by name, case-sensitive, and spaces become underscores (`Get file content` is `Get_file_content`). Rename first, then write the expression.
- **Build one step at a time.** Start Flow 1 with steps 1-5, run it on `gate-clean.md`, open the run and check `text` looks right; then add the next step. A *Compose* is the way to look at any value.
- **Debug on synthetic files only.** With *Secure inputs/outputs* on, the run history hides the values you need to debug. While building, use only the synthetic fixtures and leave the secure settings off; **switch them on for every listed action before the first real document**, then confirm a run shows "Content not shown due to security configuration".
- Expressions go in the expression tab (`fx`) of a field, not typed as plain text; the pasted ones here start at the function name, without a leading `@`, except in Filter array's advanced mode, where the `@` is part of it.

## 4. Flow 1: gate, then approval (trigger: file created or modified in `sanitized-review`)

1. **Trigger:** SharePoint *When a file is created or modified (properties only)*, site/library, folder `P001/sanitized-review`. Add a first **Condition**: `endsWith(toLower(<File name with extension>), '.md')`; the rest goes in the *Yes* branch. One copy of this flow per project (set the project folder and the constant below).
2. **Compose `project`** = `P001` (constant).
3. **Get file content** (identifier from the trigger). *Secure outputs ON.*
4. **Compose `text`** (*Secure inputs and outputs ON*):
   `replace(if(contains(string(outputs('Get_file_content')?['body']),'$content'),base64ToString(outputs('Get_file_content')?['body']?['$content']),string(outputs('Get_file_content')?['body'])),decodeUriComponent('%0D%0A'),decodeUriComponent('%0A'))`
5. **Compose `lower`** = `toLower(outputs('text'))` (*secure*).
6. **Get items** (list `Mapping`), Filter Query `Project eq 'P001'`, Top Count 5000 and pagination on. *Secure outputs ON.*
7. **Filter array `Leaks`** (*secure*): From `body('Get_items')?['value']`, edit in advanced mode:
   `@and(greater(length(coalesce(item()?['RealValue'],'')),3),contains(outputs('lower'),toLower(coalesce(item()?['RealValue'],''))))`
   (values of 3 characters or fewer are ignored to avoid false hits, matching the reference).
8. **Select `LeakPlaceholders`**: From `body('Leaks')`, Map `item()?['Title']` (placeholders only, safe to show).
9. **Filter array `Markings`**: From `createArray('protected a','protected b','protected c','top secret','secret','confidential','cabinet confidence','protégé','très secret','confidentiel','srcl')`, condition `@contains(outputs('lower'),item())`. (Words such as "secretary" will hit; that is a prompt to look, not a verdict.)
10. **Compose `contactChars`** = `add(add(if(contains(outputs('lower'),'@'),1,0),if(contains(outputs('lower'),'http'),1,0)),if(contains(outputs('lower'),'www.'),1,0))`
11. **Compose `pending`** = `if(contains(outputs('lower'),'[party-?'),1,0)`
12. **Compose `problems`** = `add(add(add(length(body('Leaks')),length(body('Markings'))),outputs('contactChars')),outputs('pending'))`
13. **Condition** `problems` is greater than 0:
    - **Yes:** *Create item* in `IngestLog` (Step `gate`, Result `failed`, Detail = `concat('leaks: ',join(body('LeakPlaceholders'),', '),' | markings: ',join(body('Markings'),', '),' | contact chars: ',string(outputs('contactChars')),' | unresolved placeholders: ',string(outputs('pending')))`); send yourself an email (Outlook *Send an email (V2)*) with the same detail and the file link; then **Terminate** (Status: Failed) so the run shows red. Fix the file and re-upload or edit it (the trigger re-runs).
    - **No:** continue.
14. **Send email with options** (Office 365 Outlook), To: you. Subject `Approve sanitized document: ` + file name; User Options `Approve,Reject`; Body: the checklist *I read the whole sanitized file; no names, addresses, contact details, signatures or stamps remain; no classification markings; provisional placeholders are resolved; numbers were spot-checked against the source; the Copilot audit (P3) was done*, and the link to the file. Put only the file name and link in the email, never document text. The flow waits for your click (this action times out after 30 days).
15. **Condition** `SelectedOption` (from step 14) is equal to `Approve`:
    - **Yes:** SharePoint **Copy file** from `sanitized-review` to `sanitized-approved`, overwrite existing *(verify: the action's replace option)*; *Create item* in `IngestLog` (Step `approval`, Result `approved`, Detail = the time and `SelectedOption`; no text).
    - **No:** *Create item* in `IngestLog` (`rejected`), and end.
    (If you later get the Approvals connector, *Start and wait for an approval* can replace steps 14-15: it keeps a formal record in the Approvals app.)

Only Flow 1 should write to `sanitized-approved`; do not drop files there by hand. Because you own the flow, this is a discipline, not a lock; the `IngestLog` is your record.

## 5. Flow 2: chunk and publish (trigger: file created or modified in `sanitized-approved`)

Common start (same *Secure* settings as Flow 1 on every step that holds text):
1. Trigger on `P001/sanitized-approved`; **Get file content**; **Compose `text`** exactly as Flow 1 step 4.
2. **Compose `nl`** = `decodeUriComponent('%0A')`
3. **Compose `stem`** = `toLower(first(split(<File name with extension>,'.')))`; **Compose `docId`** = `toUpper(outputs('stem'))`
4. **Compose `type`** = `if(startsWith(outputs('stem'),'spec-'),'spec',if(startsWith(outputs('stem'),'dwg-'),'drawing',if(startsWith(outputs('stem'),'ccn-'),'ccn',if(startsWith(outputs('stem'),'co-'),'co',if(startsWith(outputs('stem'),'ci-'),'ci',if(startsWith(outputs('stem'),'cd-'),'cd',if(startsWith(outputs('stem'),'si-'),'si',if(startsWith(outputs('stem'),'ea-'),'ea','other'))))))))`
5. **Regenerate cleanly:** *Get files (properties only)* in `P001/kb/chunks` (top 5000); **Filter array** `startsWith(item()?['{FilenameWithExtension}'],concat(outputs('stem'),'__'))` *(verify the property name in the dynamic content)*; **Apply to each** -> *Delete file* (identifier). This only removes chunks generated from this same document.
6. **Switch** on `type`:

**Case `spec`**
- **Compose `items`** = `split(concat(outputs('nl'),outputs('text')),concat(outputs('nl'),'SECTION '))` (a section starts at a line beginning `SECTION `; a mid-line "see SECTION 05 12 00" does not split).
- **Initialize variable `counter`** (Integer) = `sub(length(split(first(outputs('items')),'<!-- page ')),1)`
- **Front matter chunk:** **Compose `preRaw`** = `trim(first(outputs('items')))`; **Compose `preTail`** = `if(endsWith(outputs('preRaw'),'-->'),1,0)`; **Compose `pre`** = `if(equals(outputs('preTail'),1),join(take(split(outputs('preRaw'),outputs('nl')),sub(length(split(outputs('preRaw'),outputs('nl'))),1)),outputs('nl')),outputs('preRaw'))`. **Condition** `not(empty(outputs('pre')))` -> create `concat(outputs('stem'),'__front.md')` with the content built like the section chunks below (chunk_title `front matter`, pages `[1,` + `max(1,sub(variables('counter'),outputs('preTail')))` + `]`, no `section`/`division`).
- **Apply to each** over `skip(outputs('items'),1)`, **Settings -> Concurrency control ON, degree 1** (the page counter needs the order). Inside:
  - `heading` = `first(split(item(),outputs('nl')))`; `hp` = `split(outputs('heading'),' - ')`; `sec` = `trim(first(outputs('hp')))`; `title` = `trim(join(skip(outputs('hp'),1),' - '))`; `division` = `substring(replace(outputs('sec'),' ',''),0,2)`
  - `it` = `trim(item())`; `tail` = `if(endsWith(outputs('it'),'-->'),1,0)`; `mk` = `sub(length(split(item(),'<!-- page ')),1)`
  - `startPage` = `max(1,variables('counter'))`; `endPage` = `max(outputs('startPage'),sub(add(variables('counter'),outputs('mk')),outputs('tail')))`
  - `lines` = `split(outputs('it'),outputs('nl'))`; `body` = `concat('SECTION ',join(if(equals(outputs('tail'),1),take(outputs('lines'),sub(length(outputs('lines')),1)),outputs('lines')),outputs('nl')))`
  - **Set variable** `counter` = `add(variables('counter'),outputs('mk'))`
  - `cid` = `concat(outputs('stem'),'__',replace(outputs('sec'),' ','-'))`
  - JSON-quoted values (helper): for a value X, `substring(string(createArray(X)),1,sub(length(string(createArray(X))),2))` gives a correctly escaped `"X"`. Create Composes `qCid`, `qDocId`, `qSec`, `qTitle` with it.
  - **Compose `fm`** = `concat('---',nl,'id: ',qCid,nl,'doc_type: "spec"',nl,'doc_id: ',qDocId,nl,'doc_title: ""',nl,'section: ',qSec,nl,'chunk_title: ',qTitle,nl,'division: "',division,'"',nl,'pages: [',startPage,',',endPage,']',nl,'chars: ',length(outputs('body')),nl,'sanitization: "approved"',nl,'---',nl,nl,outputs('body'),nl)` (write `nl` as `outputs('nl')`, etc.; wrap every number, such as `startPage`, `endPage`, `length(...)`, in `string()` inside `concat`).
  - **Create file** in `P001/kb/chunks`, name `concat(outputs('cid'),'.md')`, content `outputs('fm')`.
- Long sections stay whole (no `PART` sub-split): if one exceeds about 12,000 characters, split it by hand before approval.

**Case `drawing`**
- `items` = `split(outputs('text'),'<!-- page ')`; **Apply to each** over `skip(outputs('items'),1)`: `page` = `trim(first(split(item(),' -->')))`; `body` = `trim(join(skip(split(item(),outputs('nl')),1),outputs('nl')))`; `padded` = `substring(concat('000',outputs('page')),length(outputs('page')),3)`; `cid` = `concat(outputs('stem'),'__pg',outputs('padded'))`; front matter: `id`, `doc_type: "drawing"`, `doc_id`, `doc_title: ""`, `chunk_title` = `"Sheet page N"`, `pages: [N,N]`, `chars`, `sanitization: "approved"`. Create file as above. The sheet number is not detected; add `sheet` by hand if you want it.

**Default (change documents and `other`)**
- `hasHeader` = `startsWith(outputs('text'),concat('---',outputs('nl')))`; `parts` = `split(concat(outputs('nl'),outputs('text')),concat(outputs('nl'),'---',outputs('nl')))`
- `hdrLines` = **Filter array** over `if(outputs('hasHeader'),split(outputs('parts')[1],outputs('nl')),createArray())` with condition `@and(not(empty(trim(item()))),not(contains(createArray('id','doc_type','doc_id','doc_title','section','sheet','chunk_title','division','division_name','masterformat_edition','pages','chars','sanitization'),trim(first(split(item(),':'))))))`. **This removes reserved keys, so a document can never approve itself or rename its chunk.**
- `body` = `trim(if(outputs('hasHeader'),join(skip(outputs('parts'),2),concat(outputs('nl'),'---',outputs('nl'))),outputs('text')))`; `mk` = `sub(length(split(outputs('body'),'<!-- page ')),1)`
- **Compose `fm`** = `concat('---',nl,if(empty(body('hdrLines')),'',concat(join(body('hdrLines'),nl),nl)),'id: ',qCid,nl,'doc_type: "',type,'"',nl,'doc_id: ',qDocId,nl,'doc_title: ""',nl,'chunk_title: ""',nl,'pages: [1,',string(max(1,mk)),']',nl,'chars: ',length(body),nl,'sanitization: "approved"',nl,'---',nl,nl,body,nl)`; `cid` = `concat(stem,'__all')`. Create file.

If the base64 form of file content appears, the `text` expression in Flow 1 step 4 already handles it.

## 6. Flow 3: rebuild the index (trigger: manual button; or scheduled daily)

1. **Get files (properties only)** in `P001/kb/chunks`; **Get items** from `Mapping` (project filter, secure); **Initialize variables** `chunks` (Array, `[]`) and `excluded` (Array, `[]`).
2. **Apply to each** file (concurrency 1): **Get file content** -> `t` = the Flow 1 step 4 expression (secure); `lower` = `toLower(outputs('t'))`; **Filter array** `Leaks` over the mapping items (same expression as Flow 1 step 7). **Condition** `length(body('Leaks'))` greater than 0:
   - **Yes:** *Append to array variable* `excluded` = `concat(<file name>,': known-value leak (',join(body('LeakPlaceholders'),', '),')')`.
   - **No:** `hdr` = `split(split(concat(nl,t),concat(nl,'---',nl))[1],nl)`; **Filter array** `hdrOk` `not(empty(trim(item())))`; **Select** `kv` (Map) `concat('"',substring(item(),0,indexOf(item(),': ')),'":',substring(item(),add(indexOf(item(),': '),2)))`; `obj` = `json(concat('{',join(body('kv'),','),'}'))`; *Append to array variable* `chunks` = `addProperty(outputs('obj'),'path',concat('chunks/',<File name>))`.
3. **Filter array** `approved` over `variables('chunks')`: `@equals(item()?['sanitization'],'approved')`.
4. **Select** `rows` over `body('approved')`, Map: `concat('| ',item()?['id'],' | ',item()?['doc_type'],' | ',coalesce(item()?['section'],item()?['sheet'],''),' | ',replace(coalesce(item()?['chunk_title'],item()?['doc_title'],''),'|','/'),' | ',if(equals(item()?['pages']?[0],item()?['pages']?[1]),string(item()?['pages']?[0]),concat(string(item()?['pages']?[0]),'-',string(item()?['pages']?[1]))),' | ',string(coalesce(item()?['amount'],'')),' |')`
5. **Compose `indexMd`** = `concat('# Knowledge-base index',nl,nl,'Read this file first. Then open only the chunks you need.',nl,nl,string(length(body('approved'))),' chunks.',nl,nl,'| id | type | section/sheet | title | pages | amount |',nl,'|---|---|---|---|---|---|',nl,join(body('rows'),nl),if(empty(variables('excluded')),'',concat(nl,nl,'## Excluded (fix and rebuild)',nl,nl,'- ',join(variables('excluded'),concat(nl,'- ')))),nl)`
   **Compose `indexJson`** = `concat('{"schema":"kb-index/1","generated":"',utcNow(),'","chunk_count":',string(length(body('approved'))),',"chunks":',string(body('approved')),'}')`
6. **Write both files:** for each of `INDEX.md` and `index.json`: *Get files (properties only)* in `P001/kb` filtered to that name -> *Apply to each* *Delete file* -> *Create file* with the Compose output. (Alternative: *Send an HTTP request to SharePoint*, POST `_api/web/GetFolderByServerRelativeUrl('<server-relative path to P001/kb>')/Files/add(url='INDEX.md',overwrite=true)` with the content as body *(verify)*.)
7. *Create item* in `IngestLog` (Step `index`, Detail = chunk and exclusion counts).

No `keywords` or `xref` are produced (they need pattern matching). Retrieval leans on good chunk titles, the section/sheet columns and, for change documents, `related`.

## 7. Test before real use (synthetic fixtures in `tools/test/flow-fixtures/`)
1. Create a test project `PTEST`. Add the rows of `mapping.csv` to the `Mapping` list with Project `PTEST`.
2. Upload `gate-leaky.md` to `sanitized-review`. **Expect:** Flow 1 fails; leaks `[SUB-MECH-1]`, `[PERSON-CM-PM-1]`; marking `protected b`; contact chars 2 (`@`, `www.`); unresolved placeholders 1; no approval request.
3. Upload `gate-clean.md`. **Expect:** no problems; an email with Approve/Reject buttons arrives; click Approve; the file appears in `sanitized-approved`; `IngestLog` has both rows.
4. Upload `spec-vol1.md`, `dwg-arch.md`, `co-007.md` to `sanitized-review`, approve each. **Expect in `kb/chunks`:** 3 spec chunks (`spec-vol1__front`, `__03-30-00` pages 2-2, `__05-12-00` pages 3-4), 3 drawing chunks (`dwg-arch__pg001`-`003`), 1 change chunk (`co-007__all`, amount 11500, related CCN-012, and `sanitization "approved"` even though the file's own header tried to set `id: "spoofed"`).
5. Run Flow 3. Compare `INDEX.md` and the chunk files with `tools/test/flow-fixtures/expected.json` (the reference output: chunk files and `INDEX.md` should match character for character; `index.json` is written as compact JSON, so compare its parsed content and ignore `generated`). Differences mean an expression differs from the reference: fix the flow, not the reference, unless you find the reference wrong.
6. Add `Contoso Concrete` to the `Mapping` list for `PTEST` and rerun Flow 3. **Expect:** `co-007__all` is excluded ("known-value leak") and listed under Excluded.
7. Only then run a real, low-risk document. Keep *Secure inputs/outputs* on; open a run's history and confirm text is hidden ("Content not shown due to security configuration").

## 8. Known limits
- No pattern scanner: unknown names in plain words, phone numbers, postal codes and street addresses are caught only by Copilot's audit and by you.
- Real specs may have no `SECTION` heading lines at all (running page headers only). The flows do not split those; have Copilot insert the heading lines (prompt P2) before approval, or the whole spec becomes one chunk.
- `SECTION ` headings must start at column 0 as `SECTION nn nn nn - TITLE` (P2 tells Copilot to keep them that way). Other heading styles give one big chunk or none.
- Windows/Unix line endings are normalized; nothing else in the text is altered by the flows, which is the reason for splitting in a flow and not asking Copilot to re-type chunks.
- The `IngestLog` holds metadata, not content; the approval email holds only a file name and link. Run history is the residual risk, hence the secure settings.
- The approval is a click in your mailbox: protect the mailbox accordingly.
