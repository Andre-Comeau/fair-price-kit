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

document.querySelectorAll(".scan-btn").forEach(btn => {
  btn.addEventListener("click", async () => {
    const target = document.getElementById(btn.dataset.target);
    const box = document.getElementById("scan-result");
    box.innerHTML = "<p class='hint'>Scanning…</p>";
    try {
      const result = await postJSON("/api/scan", { text: target.value });
      if (result.clean) {
        box.innerHTML = "<div class='finding ok'>No pattern matches. This does not guarantee nothing identifying remains — review before sharing.</div>";
      } else {
        const items = result.findings.map(f =>
          `<div class="finding warn">line ${f.line}: <strong>${escapeHtml(f.category)}</strong>: ${escapeHtml(f.masked)}</div>`).join("");
        box.innerHTML = `<div class="finding warn">${result.count} possible sensitive item(s) — do not share until reviewed.</div>${items}`;
      }
    } catch (e) {
      box.innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
    }
  });
});

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

document.getElementById("draft-btn").addEventListener("click", async () => {
  const box = document.getElementById("draft-result");
  box.innerHTML = "<p class='hint'>Drafting… this is the one step that calls an LLM.</p>";
  const inputs = {
    organization: document.getElementById("org").value,
    requirement: document.getElementById("requirement").value,
    price: document.getElementById("price").value,
    price_evidence: document.getElementById("evidence").value,
    decision_maker: document.getElementById("decisionmaker").value,
  };
  try {
    const { draft, citations, usage, estimated_cost_usd } = await postJSON("/api/draft", inputs);
    const used = citations.used.map(id => `<span class="used">${escapeHtml(id)}</span>`).join("");
    const unknown = citations.unknown.map(id => `<span class="unknown">${escapeHtml(id)}</span>`).join("");
    if (typeof estimated_cost_usd === "number") sessionSpendUsd += estimated_cost_usd;
    const cost = typeof estimated_cost_usd === "number"
      ? `$${estimated_cost_usd.toFixed(4)} this call (${usage.input_tokens} in / ${usage.cache_read_input_tokens || 0} cached / ${usage.output_tokens} out) — $${sessionSpendUsd.toFixed(4)} so far this session`
      : "cost unknown for this model";
    box.innerHTML = `
      <div class="finding ok">${cost}</div>
      <div class="citation-list">
        ${used ? `<strong>Citations found in the register:</strong> ${used}` : ""}
        ${unknown ? `<br><strong>⚠ Not found in the register — check before trusting:</strong> ${unknown}` : ""}
      </div>
      <pre>${escapeHtml(draft)}</pre>`;
  } catch (e) {
    box.innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
  }
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

loadRegister().catch(e => {
  document.getElementById("register-table").innerHTML = `<div class="finding warn">${escapeHtml(e.message)}</div>`;
});
