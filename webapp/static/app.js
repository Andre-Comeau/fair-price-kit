// Vanilla JS, no build step, no dependencies -- matches the rest of the kit.

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `request failed (${res.status})`);
  return data;
}

async function getJSON(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `request failed (${res.status})`);
  return data;
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

// ---------- register ----------

let registerRows = [];
let sessionSpendUsd = 0; // running total for this browser tab only -- reset on reload, not a real ledger

async function loadRegister() {
  const { rows } = await getJSON("/api/register");
  registerRows = rows;
  renderRegister(rows);
}

function renderRegister(rows) {
  const box = document.getElementById("register-table");
  if (!rows.length) { box.innerHTML = "<p class='hint'>No register loaded.</p>"; return; }
  const body = rows.map(r => `
    <tr>
      <td><code>${escapeHtml(r.id)}</code></td>
      <td>${escapeHtml(r.instrument)}</td>
      <td>${escapeHtml(r.provision)}</td>
      <td>${escapeHtml(r.status)}</td>
    </tr>`).join("");
  box.innerHTML = `<table><thead><tr><th>id</th><th>instrument</th><th>provision</th><th>status</th></tr></thead><tbody>${body}</tbody></table>`;
}

document.getElementById("register-filter").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase();
  renderRegister(registerRows.filter(r =>
    Object.values(r).some(v => (v || "").toLowerCase().includes(q))));
});

// ---------- sensitive-info scan ----------
// acceptedExceptions: text the operator has looked at and decided is not sensitive, this browser
// tab only -- sent back on every scan so it isn't flagged again. Never written to disk; mirrors
// the CLI's kb/gate-allow.txt idea (gates/sensitive-info-gate.md) but lasts only as long as the tab.
let acceptedExceptions = [];
let lastScanFindings = [];

document.querySelectorAll(".scan-btn").forEach(btn => {
  btn.addEventListener("click", () => runScan(document.getElementById(btn.dataset.target)));
});

async function runScan(target) {
  const box = document.getElementById("scan-result");
  box.innerHTML = "<p class='hint'>Scanning…</p>";
  try {
    const result = await postJSON("/api/scan", { text: target.value, allow: acceptedExceptions });
    lastScanFindings = result.findings;
    if (result.clean) {
      box.innerHTML = "<div class='finding ok'>No pattern matches. This does not guarantee nothing identifying remains — review before sharing.</div>";
      return;
    }
    const items = result.findings.map((f, i) => `
      <div class="finding warn">
        line ${f.line}: <strong>${escapeHtml(f.category)}</strong>: ${escapeHtml(f.masked)}
        <button type="button" class="redact-btn" data-idx="${i}" data-target="${target.id}">Redact</button>
        <button type="button" class="keep-btn" data-idx="${i}" data-target="${target.id}">Keep — not sensitive</button>
      </div>`).join("");
    box.innerHTML = `<div class="finding warn">${result.count} possible sensitive item(s) — do not share until reviewed.</div>${items}`;
    box.querySelectorAll(".redact-btn").forEach(b => b.addEventListener("click", () => {
      editField(document.getElementById(b.dataset.target), lastScanFindings[Number(b.dataset.idx)], "redact");
    }));
    box.querySelectorAll(".keep-btn").forEach(b => b.addEventListener("click", () => {
      editField(document.getElementById(b.dataset.target), lastScanFindings[Number(b.dataset.idx)], "keep");
    }));
  } catch (e) {
    box.innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
  }
}

// Redact replaces the exact matched span with [CATEGORY] in the field, in place. Keep records the
// exact matched text (read straight from the field -- the server only ever sent back a masked
// preview) as reviewed-and-accepted, so future scans won't flag that specific text again. Either
// way, re-scan afterward: editing shifts offsets, and a fresh scan is the only way to stay correct.
function editField(target, finding, action) {
  const lines = target.value.split("\n");
  const line = lines[finding.line - 1] || "";
  const matched = line.slice(finding.start, finding.end);
  if (action === "redact") {
    lines[finding.line - 1] = line.slice(0, finding.start) + `[${finding.category.toUpperCase()}]` + line.slice(finding.end);
    target.value = lines.join("\n");
  } else if (matched && !acceptedExceptions.includes(matched)) {
    acceptedExceptions.push(matched);
  }
  runScan(target);
}

// ---------- award search ----------

document.getElementById("award-search-btn").addEventListener("click", async () => {
  const q = document.getElementById("award-query").value;
  const unflagged = document.getElementById("award-unflagged").checked ? "1" : "0";
  const competitive = document.getElementById("award-competitive").checked ? "1" : "0";
  const box = document.getElementById("award-table");
  box.innerHTML = "<p class='hint'>Searching…</p>";
  try {
    const { rows } = await getJSON(`/api/awards?q=${encodeURIComponent(q)}&unflagged=${unflagged}&competitive=${competitive}&limit=25`);
    if (!rows.length) { box.innerHTML = "<p class='hint'>No matches.</p>"; return; }
    const body = rows.map(r => `
      <tr class="${r.quality_flags ? 'flagged' : ''}">
        <td>${escapeHtml(r.contract_number)}</td>
        <td>${escapeHtml(r.title)}</td>
        <td>${escapeHtml(r.total_contract_value)}</td>
        <td>${escapeHtml(r.award_date)}</td>
        <td>${escapeHtml(r.competitive)} / ${escapeHtml(r.selection_criteria)}</td>
        <td>${escapeHtml(r.quality_flags) || "—"}</td>
      </tr>`).join("");
    box.innerHTML = `<table><thead><tr><th>contract</th><th>title</th><th>value</th><th>date</th><th>process</th><th>flags</th></tr></thead><tbody>${body}</tbody></table>
      <p class="hint">Contains information licensed under the Open Government Licence – Canada. A flagged row (shaded) is not a usable comparable.</p>`;
  } catch (e) {
    box.innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
  }
});

// ---------- draft ----------
// conversationMessages holds the API's own "messages" array between calls, so a reply to the
// draft continues the same conversation instead of starting a fresh, context-free one.
let conversationMessages = null;

function renderDraftTurn(result, label) {
  const used = result.citations.used.map(id => `<span class="used">${escapeHtml(id)}</span>`).join("");
  const unknown = result.citations.unknown.map(id => `<span class="unknown">${escapeHtml(id)}</span>`).join("");
  if (typeof result.estimated_cost_usd === "number") sessionSpendUsd += result.estimated_cost_usd;
  const cost = typeof result.estimated_cost_usd === "number"
    ? `$${result.estimated_cost_usd.toFixed(4)} this call (${result.usage.input_tokens} in / ${result.usage.cache_read_input_tokens || 0} cached / ${result.usage.output_tokens} out) — $${sessionSpendUsd.toFixed(4)} so far this session`
    : "cost unknown for this model";
  const truncatedWarning = result.truncated
    ? `<div class="finding warn"><strong>⚠ Cut off before finishing:</strong> the model hit the output
       length limit mid-document. This is NOT a complete draft -- do not use it as one. Reply below
       asking it to continue, or shorten the inputs and try again.</div>`
    : "";
  return `
    <div class="draft-turn">
      ${label ? `<p class="hint"><strong>${escapeHtml(label)}</strong></p>` : ""}
      <div class="finding ok">${cost}</div>
      ${truncatedWarning}
      <div class="citation-list">
        ${used ? `<strong>Citations found in the register:</strong> ${used}` : ""}
        ${unknown ? `<br><strong>⚠ Not found in the register — check before trusting:</strong> ${unknown}` : ""}
      </div>
      <pre>${escapeHtml(result.draft)}</pre>
    </div>`;
}

document.getElementById("draft-btn").addEventListener("click", async () => {
  const box = document.getElementById("draft-result");
  box.innerHTML = "<p class='hint'>Drafting… this is the one step that calls an LLM.</p>";
  document.getElementById("draft-feedback").style.display = "none";
  const inputs = {
    organization: document.getElementById("org").value,
    requirement: document.getElementById("requirement").value,
    price: document.getElementById("price").value,
    price_evidence: document.getElementById("evidence").value,
  };
  try {
    const result = await postJSON("/api/draft", inputs);
    conversationMessages = result.messages;
    box.innerHTML = renderDraftTurn(result, null);
    document.getElementById("draft-feedback").style.display = "block";
  } catch (e) {
    box.innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
  }
});

document.getElementById("feedback-btn").addEventListener("click", async () => {
  const feedbackBox = document.getElementById("feedback-text");
  const text = feedbackBox.value.trim();
  const box = document.getElementById("draft-result");
  if (!text) return;
  if (!conversationMessages) {
    box.insertAdjacentHTML("beforeend", "<div class='finding warn'>Generate a draft first — there's no conversation to reply to yet.</div>");
    return;
  }
  box.insertAdjacentHTML("beforeend", "<p class='hint'>Sending your response…</p>");
  const nextMessages = conversationMessages.concat([{ role: "user", content: text }]);
  try {
    const result = await postJSON("/api/draft", { messages: nextMessages });
    conversationMessages = result.messages;
    feedbackBox.value = "";
    box.insertAdjacentHTML("beforeend", renderDraftTurn(result, `Your response: "${text}"`));
  } catch (e) {
    box.insertAdjacentHTML("beforeend", `<div class="finding warn">${escapeHtml(e.message)}</div>`);
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

loadRegister().catch(e => {
  document.getElementById("register-table").innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
});

// Tells the operator up front that drafting won't work, instead of only after they've filled in
// the whole form and clicked Generate.
getJSON("/api/health").then(health => {
  if (!health.draft_enabled) {
    document.getElementById("draft-disabled-banner").style.display = "block";
  }
}).catch(() => {}); // a failed health check isn't worth its own error message here; every other
                     // action already reports its own failure clearly if the server is unreachable
