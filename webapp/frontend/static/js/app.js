// AI StudyMate — frontend controller
// Talks to the Flask REST API in backend/app.py

const state = {
  currentPdfId: null,
  voiceOn: true,
  isAdmin: false,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || "Something went wrong.");
  return data;
}

function showToast(msg) {
  const toast = $("#toast");
  toast.textContent = msg;
  toast.classList.remove("hidden");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.add("hidden"), 2600);
}

function speak(text) {
  if (!state.voiceOn) return;
  if (!("speechSynthesis" in window)) return;
  const clean = Array.isArray(text) ? text.join(". ") : String(text);
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(clean.slice(0, 600));
  utter.rate = 1;
  window.speechSynthesis.speak(utter);
}

// ---------------------------------------------------------------
// Auth
// ---------------------------------------------------------------
function initAuth() {
  $$(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      $("#login-form").classList.toggle("hidden", tab !== "login");
      $("#register-form").classList.toggle("hidden", tab !== "register");
    });
  });

  $("#login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    $("#login-error").textContent = "";
    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: fd.get("username"), password: fd.get("password") }),
      });
      state.isAdmin = !!data.is_admin;
      enterApp();
    } catch (err) {
      $("#login-error").textContent = err.message;
    }
  });

  $("#register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    $("#register-error").textContent = "";
    $("#register-success").textContent = "";
    try {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username: fd.get("username"), password: fd.get("password") }),
      });
      $("#register-success").textContent = "Account created — switch to Log in.";
      e.target.reset();
    } catch (err) {
      $("#register-error").textContent = err.message;
    }
  });

  $("#logout-btn").addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    location.reload();
  });
}

function enterApp() {
  $("#auth-screen").classList.add("hidden");
  $("#app-screen").classList.remove("hidden");
  $("#nav-admin").classList.toggle("hidden", !state.isAdmin);
}

// ---------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------
function initNav() {
  $$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".nav-btn").forEach((b) => b.classList.remove("active"));
      $$(".view").forEach((v) => v.classList.remove("active"));
      btn.classList.add("active");
      $(`#view-${btn.dataset.view}`).classList.add("active");

      if (btn.dataset.view === "quiz") loadQuiz();
      if (btn.dataset.view === "planner") loadPlanner();
      if (btn.dataset.view === "about") loadAbout();
      if (btn.dataset.view === "admin") loadAdmin();
    });
  });

  $("#voice-toggle").addEventListener("click", () => {
    state.voiceOn = !state.voiceOn;
    $("#voice-icon").textContent = state.voiceOn ? "🔊" : "🔇";
    $("#voice-label").textContent = state.voiceOn ? "Voice on" : "Voice off";
    if (!state.voiceOn) window.speechSynthesis?.cancel();
  });
}

// ---------------------------------------------------------------
// Upload: PDF
// ---------------------------------------------------------------
function initUpload() {
  $("#pdf-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const statusEl = $("#pdf-status");
    statusEl.className = "status-line";
    statusEl.textContent = "Uploading…";

    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/pdf/upload", { method: "POST", body: fd, credentials: "same-origin" });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.message || "Upload failed.");
      state.currentPdfId = data.id;
      statusEl.className = "status-line ok";
      const readiness = data.text_ready
        ? "Ready for Ask AI & Quiz."
        : `Uploaded, but text couldn't be read${data.text_warning ? " — " + data.text_warning : ""}.`;
      statusEl.textContent = `PDF uploaded\nFile: ${data.file_name}\nPages: ${data.pages}\nSize: ${data.size_kb} KB\n${readiness}`;
      showToast("PDF uploaded successfully");
    } catch (err) {
      statusEl.className = "status-line err";
      statusEl.textContent = err.message;
    }
  });

  $("#image-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const statusEl = $("#image-status");
    statusEl.className = "status-line";
    statusEl.textContent = "Uploading…";

    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/image/upload", { method: "POST", body: fd, credentials: "same-origin" });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.message || "Upload failed.");
      statusEl.className = "status-line ok";
      const readiness = data.text_ready
        ? "Text read successfully — ready for Ask AI & Quiz."
        : `Uploaded, but no readable text found${data.text_warning ? " — " + data.text_warning : ""}.`;
      statusEl.textContent = `Image uploaded: ${data.file_name}\n${readiness}`;
      const img = $("#image-preview");
      img.src = data.url;
      img.classList.remove("hidden");
      showToast("Image uploaded successfully");
    } catch (err) {
      statusEl.className = "status-line err";
      statusEl.textContent = err.message;
    }
  });
}

// ---------------------------------------------------------------
// Chat — shows only the current question/answer, no history kept
// ---------------------------------------------------------------
function initChat() {
  $("#chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = $("#chat-input");
    const question = input.value.trim();
    if (!question) return;

    showBubbles(question, "Thinking…");
    input.value = "";

    try {
      const data = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ question, id: state.currentPdfId }),
      });
      showBubbles(question, data.answer);
      speak(data.answer);
    } catch (err) {
      showBubbles(question, err.message);
    }
  });
}

function showBubbles(question, answer) {
  const win = $("#chat-window");
  win.innerHTML = "";
  const q = document.createElement("div");
  q.className = "chat-bubble bubble-user";
  q.textContent = question;
  const a = document.createElement("div");
  a.className = "chat-bubble bubble-ai";
  a.textContent = answer;
  win.appendChild(q);
  win.appendChild(a);
}

// ---------------------------------------------------------------
// Summarize
// ---------------------------------------------------------------
function initSummarize() {
  $("#summarize-btn").addEventListener("click", async () => {
    const out = $("#summary-output");
    out.classList.remove("hidden");
    out.innerHTML = "⏳ Generating summary…";
    try {
      const data = await api("/api/pdf/summarize", {
        method: "POST",
        body: JSON.stringify({ id: state.currentPdfId }),
      });
      if (Array.isArray(data.summary)) {
        out.innerHTML = `<ul>${data.summary.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul>`;
        speak(data.summary);
      } else {
        out.innerHTML = escapeHtml(data.summary);
        speak(data.summary);
      }
    } catch (err) {
      out.innerHTML = escapeHtml(err.message);
    }
  });
}

// ---------------------------------------------------------------
// Search
// ---------------------------------------------------------------
function initSearch() {
  $("#search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const keyword = $("#search-input").value.trim();
    if (!keyword) return;
    const out = $("#search-output");
    out.classList.remove("hidden");
    out.innerHTML = "Searching…";
    try {
      const data = await api("/api/pdf/search", {
        method: "POST",
        body: JSON.stringify({ id: state.currentPdfId, keyword }),
      });
      out.innerHTML = `${data.found ? "✅" : "❌"} ${escapeHtml(data.message)}` +
        (data.snippet ? `<span class="snippet">…${escapeHtml(data.snippet)}…</span>` : "");
    } catch (err) {
      out.innerHTML = escapeHtml(err.message);
    }
  });
}

// ---------------------------------------------------------------
// Quiz
// ---------------------------------------------------------------
async function loadQuiz() {
  const wrap = $("#quiz-list");
  wrap.innerHTML = "Loading…";
  try {
    const data = await api("/api/quiz");
    wrap.innerHTML = data.questions
      .map(
        (q, qi) => `<div class="quiz-card">
          <div class="q-text">${qi + 1}. ${escapeHtml(q.question)}</div>
          <div class="quiz-options">
            ${q.options
              .map((opt) => `<button type="button" class="quiz-option" data-answer="${escapeHtml(q.answer)}" data-value="${escapeHtml(opt)}">${escapeHtml(opt)}</button>`)
              .join("")}
          </div>
        </div>`
      )
      .join("");

    wrap.querySelectorAll(".quiz-option").forEach((btn) => {
      btn.addEventListener("click", () => {
        const card = btn.closest(".quiz-card");
        const correctVal = btn.dataset.answer;
        card.querySelectorAll(".quiz-option").forEach((b) => {
          b.disabled = true;
          if (b.dataset.value === correctVal) b.classList.add("correct");
          else if (b === btn) b.classList.add("wrong");
        });
      });
    });
  } catch (err) {
    wrap.innerHTML = escapeHtml(err.message);
  }
}

// ---------------------------------------------------------------
// Planner
// ---------------------------------------------------------------
async function loadPlanner() {
  const wrap = $("#planner-list");
  wrap.innerHTML = "Loading…";
  try {
    const data = await api("/api/planner");
    wrap.innerHTML = data.plan
      .map((p) => `<div class="planner-row"><span class="day">${escapeHtml(p.day)}</span><span class="task">${escapeHtml(p.task)}</span></div>`)
      .join("");
  } catch (err) {
    wrap.innerHTML = escapeHtml(err.message);
  }
}

// ---------------------------------------------------------------
// About
// ---------------------------------------------------------------
async function loadAbout() {
  const wrap = $("#about-body");
  wrap.innerHTML = "Loading…";
  try {
    const data = await api("/api/about");
    wrap.innerHTML = `
      <p><strong>${escapeHtml(data.app)}</strong> — v${escapeHtml(data.version)}</p>
      <p>Developed by ${escapeHtml(data.developed_by)} · ${escapeHtml(data.department)} · ${escapeHtml(data.college)}</p>
      <h3>Features</h3>
      <ul>${data.features.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul>
    `;
  } catch (err) {
    wrap.innerHTML = escapeHtml(err.message);
  }
}

// ---------------------------------------------------------------
// Admin (admin account only) — who has logged in, who's online
// ---------------------------------------------------------------
async function loadAdmin() {
  const statsEl = $("#admin-stats");
  const onlineEl = $("#admin-online");
  const historyEl = $("#admin-history");
  statsEl.innerHTML = "Loading…";
  onlineEl.innerHTML = "";
  historyEl.innerHTML = "";

  try {
    const data = await api("/api/admin/logins");

    statsEl.innerHTML = `
      <div class="admin-stat-card"><div class="stat-num">${data.total_registered_users}</div><div class="stat-label">Registered users</div></div>
      <div class="admin-stat-card"><div class="stat-num">${data.total_logins}</div><div class="stat-label">Total logins</div></div>
      <div class="admin-stat-card"><div class="stat-num">${data.online_count}</div><div class="stat-label">Online now</div></div>
    `;

    onlineEl.innerHTML = data.online_users.length
      ? data.online_users
          .map((u) => `<div class="note-card"><span class="note-name"><span class="admin-online-badge"></span>${escapeHtml(u.username)}</span><span class="note-meta">since ${escapeHtml(u.last_seen)}</span></div>`)
          .join("")
      : `<p class="muted">Nobody else is online right now.</p>`;

    historyEl.innerHTML = data.login_history.length
      ? data.login_history
          .map((h) => `<div class="note-card"><span class="note-name">${escapeHtml(h.username)}</span><span class="note-meta">${escapeHtml(h.login_time)}</span></div>`)
          .join("")
      : `<p class="muted">No login activity yet.</p>`;
  } catch (err) {
    statsEl.innerHTML = escapeHtml(err.message);
  }
}

// ---------------------------------------------------------------
// Utils
// ---------------------------------------------------------------
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ---------------------------------------------------------------
// Boot
// ---------------------------------------------------------------
async function boot() {
  initAuth();
  initNav();
  initUpload();
  initChat();
  initSummarize();
  initSearch();

  try {
    const me = await api("/api/auth/me");
    if (me.logged_in) {
      state.isAdmin = !!me.is_admin;
      enterApp();
    }
  } catch (_) {}
}

document.addEventListener("DOMContentLoaded", boot);
