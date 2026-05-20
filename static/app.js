(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const state = { selected: new Set() };

  async function loadCategories() {
    const res = await fetch("/api/categories");
    if (!res.ok) throw new Error("Failed to load categories");
    return res.json();
  }

  function renderCategories(categories) {
    const root = $("#categories");
    root.innerHTML = "";
    categories.forEach((cat) => {
      const el = document.createElement("button");
      el.type = "button";
      el.className = "chip";
      el.textContent = cat;
      el.setAttribute("data-cat", cat);
      el.addEventListener("click", () => {
        if (state.selected.has(cat)) {
          state.selected.delete(cat);
          el.classList.remove("active");
        } else {
          state.selected.add(cat);
          el.classList.add("active");
        }
      });
      root.appendChild(el);
    });
  }

  function parseFollowing(value) {
    return value
      .split(/[,\s]+/)
      .map((h) => h.replace(/^@/, "").trim().toLowerCase())
      .filter(Boolean);
  }

  function renderResults(recs) {
    const root = $("#results");
    root.classList.add("has-content");
    if (!recs || recs.length === 0) {
      root.innerHTML = `<div class="empty">No suggestions — try picking a few categories.</div>`;
      return;
    }
    const items = recs
      .map((r, i) => {
        const handle = r.page.username;
        const url = `https://instagram.com/${handle}`;
        const reasons = (r.reasons || [])
          .map((reason) => `<li>${escapeHtml(reason)}</li>`)
          .join("");
        return `
          <article class="rec">
            <div class="rank">${i + 1}.</div>
            <div class="body">
              <h3><a href="${url}" target="_blank" rel="noopener">${escapeHtml(
          r.page.name
        )}</a></h3>
              <div class="handle">@${escapeHtml(handle)} · ${escapeHtml(
          r.page.categories.join(", ")
        )}</div>
              <p class="desc">${escapeHtml(r.page.description || "")}</p>
              ${reasons ? `<ul class="reasons">${reasons}</ul>` : ""}
            </div>
            <div class="score">${(r.score * 100).toFixed(0)}</div>
          </article>
        `;
      })
      .join("");
    root.innerHTML = `<h2 style="margin-top:0">Suggestions</h2>${items}`;
  }

  function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[c]));
  }

  function showError(message) {
    const root = $("#results");
    root.classList.add("has-content");
    root.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
  }

  async function recommend() {
    const btn = $("#recommend");
    btn.disabled = true;
    btn.textContent = "Thinking…";
    try {
      const payload = {
        categories: Array.from(state.selected),
        following: parseFollowing($("#following").value),
        limit: Math.max(1, Math.min(50, parseInt($("#limit").value, 10) || 10)),
      };
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          (err.detail && err.detail.message) || `Request failed (${res.status})`
        );
      }
      const data = await res.json();
      renderResults(data.recommendations || []);
    } catch (e) {
      showError(e.message || "Something went wrong.");
    } finally {
      btn.disabled = false;
      btn.textContent = "Get suggestions";
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    try {
      const cats = await loadCategories();
      renderCategories(cats);
    } catch (e) {
      showError(e.message);
    }
    $("#recommend").addEventListener("click", recommend);
  });
})();
