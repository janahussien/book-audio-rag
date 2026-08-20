const API = "/api/books";

const state = {
  books: [],
  activeBookId: null,
  prompts: [],
  summaries: [], // for the active book
  activeMode: "summary",
};

const el = {
  fileInput: document.getElementById("file-input"),
  spines: document.getElementById("spines"),
  emptyState: document.getElementById("empty-state"),
  bookView: document.getElementById("book-view"),
  bookTitle: document.getElementById("book-title"),
  bookStatus: document.getElementById("book-status"),
  bookMeta: document.getElementById("book-meta"),
  processingNote: document.getElementById("processing-note"),
  tabs: document.getElementById("tabs"),
  panel: document.getElementById("panel"),
  runAll: document.getElementById("run-all"),
};

// ---------- Data loading ----------

async function fetchBooks() {
  const res = await fetch(API);
  state.books = await res.json();
  renderShelf();
}

async function fetchPrompts() {
  const res = await fetch(`${API}/${state.activeBookId}/prompts`);
  state.prompts = await res.json();
}

async function fetchSummaries() {
  const res = await fetch(`${API}/${state.activeBookId}/summaries`);
  state.summaries = await res.json();
}

// ---------- Rendering ----------

function renderShelf() {
  el.spines.innerHTML = "";
  for (const book of state.books) {
    const div = document.createElement("div");
    div.className = "spine" + (book.id === state.activeBookId ? " active" : "");
    div.tabIndex = 0;
    div.innerHTML = `
      <div>
        <div>${escapeHtml(book.title)}</div>
        <div class="spine--status">${book.status}${book.num_chunks ? " · " + book.num_chunks + " chunks" : ""}</div>
      </div>
    `;
    div.addEventListener("click", () => selectBook(book.id));
    el.spines.appendChild(div);
  }
}

async function selectBook(bookId) {
  state.activeBookId = bookId;
  renderShelf();
  el.emptyState.classList.add("hidden");
  el.bookView.classList.remove("hidden");
  await refreshActiveBook();
}

async function refreshActiveBook() {
  const book = state.books.find((b) => b.id === state.activeBookId);
  if (!book) return;

  el.bookTitle.textContent = book.title;
  el.bookStatus.textContent = book.status;
  el.bookMeta.textContent = book.status === "ready"
    ? `${book.num_chunks} chunks indexed`
    : book.status === "error"
      ? `Error: ${book.error || "unknown"}`
      : "Processing…";

  el.processingNote.classList.toggle("hidden", book.status !== "processing");
  el.runAll.disabled = book.status !== "ready";

  if (book.status === "processing") {
    setTimeout(async () => {
      await fetchBooks();
      if (state.activeBookId === book.id) await refreshActiveBook();
    }, 2500);
    return;
  }

  await fetchPrompts();
  await fetchSummaries();
  renderTabs();
  renderPanel();
}

function renderTabs() {
  el.tabs.innerHTML = "";
  const modes = [
    { id: "summary", label: "Detailed Summary" },
    { id: "chat", label: "Ask the Book" },
  ];
  for (const mode of modes) {
    const tab = document.createElement("button");
    const isActive = mode.id === state.activeMode;
    tab.className = "tab" + (isActive ? " active" : "");
    tab.innerHTML = `<span class="tab-dot"></span>${escapeHtml(mode.label)}`;
    tab.addEventListener("click", () => {
      state.activeMode = mode.id;
      renderTabs();
      renderPanel();
    });
    el.tabs.appendChild(tab);
  }
}

function renderPanel() {
  el.panel.innerHTML = "";
  if (state.activeMode === "chat") {
    renderChatPanel();
    return;
  }

  const prompt = state.prompts.find((p) => p.id === "detailed_summary") || state.prompts[0];
  const summary = state.summaries.find((s) => s.prompt_id === prompt?.id);

  if (!summary) {
    el.panel.innerHTML = `
      <div class="panel-empty">
        <span class="panel-label">One complete reading companion</span>
        <h3>Detailed Book Summary</h3>
        <p class="panel-body">Generate one substantial summary covering the book's premise, structure, key people or ideas, turning points, themes, evidence, and ending.</p>
        <div class="panel-actions">
          <button class="btn btn--primary" id="panel-generate">Generate detailed summary</button>
        </div>
      </div>
    `;
    document.getElementById("panel-generate").addEventListener("click", async (e) => {
      e.target.disabled = true;
      e.target.textContent = "Generating…";
      await runSinglePrompt(prompt.id);
    });
    return;
  }

  el.panel.innerHTML = `
    <span class="panel-label">Complete reading companion</span>
    <h3>Detailed Book Summary</h3>
    <div class="panel-body markdown-body">${markdownToHtml(summary.text)}</div>
    <div class="panel-actions">
      <button class="btn btn--primary" id="panel-narrate">
        ${summary.audio_ready ? "▶ Rebuild narration" : "▶ Generate narration"}
      </button>
      <button class="btn btn--ghost" id="panel-regenerate">Regenerate complete summary</button>
      <audio id="panel-audio" controls class="hidden"></audio>
    </div>
  `;

  document.getElementById("panel-narrate").addEventListener("click", (e) =>
    playSummary(summary.id, e.target)
  );
  document.getElementById("panel-regenerate").addEventListener("click", async (e) => {
    e.target.disabled = true;
    e.target.textContent = "Regenerating all sections…";
    await runFullSummary();
  });

  if (summary.audio_ready) {
    const audioEl = document.getElementById("panel-audio");
    audioEl.src = `${API}/${state.activeBookId}/summaries/${summary.id}/audio?v=${encodeURIComponent(summary.created_at)}`;
    audioEl.classList.remove("hidden");
    setupWordHighlighting(summary.id, audioEl);
  }
}

async function setupWordHighlighting(summaryId, audioEl) {
  const reader = document.querySelector(".markdown-body");
  if (!reader) return;
  const wordElements = wrapReaderWords(reader);
  try {
    const res = await fetch(`${API}/${state.activeBookId}/summaries/${summaryId}/audio-timings`);
    if (!res.ok) return;
    const timings = (await res.json()).words || [];
    let activeIndex = -1;
    audioEl.addEventListener("timeupdate", () => {
      const time = audioEl.currentTime;
      const nextIndex = timings.findIndex((timing) => time >= timing.start && time < timing.end);
      if (nextIndex === activeIndex) return;
      if (activeIndex >= 0) wordElements[activeIndex]?.classList.remove("is-speaking");
      activeIndex = nextIndex;
      if (activeIndex >= 0) {
        const word = wordElements[activeIndex];
        word?.classList.add("is-speaking");
      }
    });
  } catch (_) {
    // Older audio files may not have timing metadata until narration is rebuilt.
  }
}

function wrapReaderWords(reader) {
  const words = [];
  const walker = document.createTreeWalker(reader, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);
  for (const node of textNodes) {
    const fragment = document.createDocumentFragment();
    for (const part of node.nodeValue.split(/(\s+)/)) {
      if (/^\s+$/.test(part) || !part) {
        fragment.appendChild(document.createTextNode(part));
        continue;
      }
      const span = document.createElement("span");
      span.className = "reader-word";
      span.textContent = part;
      fragment.appendChild(span);
      words.push(span);
    }
    node.parentNode.replaceChild(fragment, node);
  }
  return words;
}

function renderChatPanel() {
  el.panel.innerHTML = `
    <span class="panel-label">Book-grounded search</span>
    <h3>Ask the Book</h3>
    <p class="panel-intro">Search the indexed text in your own words. Answers are grounded in passages from this book.</p>
    <form id="chat-form" class="chat-form">
      <textarea id="chat-question" rows="3" placeholder="What do you want to understand about this book?" required></textarea>
      <div class="panel-actions">
        <button class="btn btn--primary" id="chat-submit" type="submit">Search the book</button>
      </div>
    </form>
    <div id="chat-answer" class="chat-answer hidden"></div>
  `;
  document.getElementById("chat-form").addEventListener("submit", askBook);
}

async function askBook(event) {
  event.preventDefault();
  const questionEl = document.getElementById("chat-question");
  const submitEl = document.getElementById("chat-submit");
  const answerEl = document.getElementById("chat-answer");
  submitEl.disabled = true;
  submitEl.textContent = "Searching…";
  answerEl.classList.add("hidden");
  try {
    const res = await fetch(`${API}/${state.activeBookId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: questionEl.value, use_web_enrichment: false }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    answerEl.innerHTML = markdownToHtml(data.answer);
    answerEl.classList.remove("hidden");
  } catch (e) {
    alert("Search failed: " + e);
  } finally {
    submitEl.disabled = false;
    submitEl.textContent = "Search the book";
  }
}

// ---------- Actions ----------

el.fileInput.addEventListener("change", async () => {
  const file = el.fileInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(API, { method: "POST", body: form });
  if (!res.ok) {
    alert("Upload failed: " + (await res.text()));
    return;
  }
  const book = await res.json();
  el.fileInput.value = "";
  await fetchBooks();
  await selectBook(book.id);
});

el.runAll.addEventListener("click", async () => {
  el.runAll.disabled = true;
  el.runAll.textContent = "Generating…";
  await runFullSummary();
  el.runAll.disabled = false;
  el.runAll.textContent = "Generate detailed summary";
});

async function runFullSummary() {
  try {
    const res = await fetch(`${API}/${state.activeBookId}/summaries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt_ids: null, use_web_enrichment: false }),
    });
    if (!res.ok) throw new Error(await res.text());
    await fetchSummaries();
    renderTabs();
    renderPanel();
  } catch (e) {
    alert("Generation failed: " + e);
  }
}

async function runSinglePrompt(promptId = "detailed_summary") {
  try {
    const res = await fetch(`${API}/${state.activeBookId}/summaries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt_ids: [promptId], use_web_enrichment: false }),
    });
    if (!res.ok) throw new Error(await res.text());
  } catch (e) {
    alert("Generation failed: " + e);
  }
  await fetchSummaries();
  renderTabs();
  renderPanel();
}

async function playSummary(summaryId, buttonEl) {
  const originalLabel = buttonEl.textContent;
  buttonEl.disabled = true;
  buttonEl.textContent = "Narrating…";
  try {
    const url = `${API}/${state.activeBookId}/summaries/${summaryId}/audio`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
    await fetchSummaries();
    renderTabs();
    renderPanel();
    const audioEl = document.getElementById("panel-audio");
    if (audioEl) audioEl.play();
  } catch (e) {
    alert("Narration failed: " + e);
    buttonEl.disabled = false;
    buttonEl.textContent = originalLabel;
  }
}

// ---------- Utils ----------

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function markdownToHtml(markdown) {
  const escaped = escapeHtml(markdown ?? "");
  const lines = escaped.split("\n");
  const output = [];
  let listType = null;

  const closeList = () => {
    if (listType) {
      output.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const line of lines) {
    const heading = line.match(/^\s{0,3}#{1,4}\s+(.+)$/);
    const bullet = line.match(/^\s*[-*]\s+(.+)$/);
    if (heading) {
      closeList();
      const level = Math.min((line.match(/^\s{0,3}(#+)/) || ["", "#"])[1].length + 1, 6);
      output.push(`<h${level}>${formatInlineMarkdown(heading[1])}</h${level}>`);
    } else if (bullet) {
      if (listType !== "ul") {
        closeList();
        output.push("<ul>");
        listType = "ul";
      }
      output.push(`<li>${formatInlineMarkdown(bullet[1])}</li>`);
    } else if (line.match(/^\s*\d+[.)]\s+(.+)$/)) {
      const numbered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (listType !== "ol") {
        closeList();
        output.push("<ol>");
        listType = "ol";
      }
      output.push(`<li>${formatInlineMarkdown(numbered[1])}</li>`);
    } else if (line.trim()) {
      closeList();
      output.push(`<p>${formatInlineMarkdown(line)}</p>`);
    } else {
      closeList();
    }
  }
  closeList();
  return output.join("");
}

function formatInlineMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
    .replace(/_([^_\n]+)_/g, "<em>$1</em>")
    .replace(/`([^`\n]+)`/g, "<code>$1</code>");
}

function truncate(str, n) {
  return str.length > n ? str.slice(0, n).trimEnd() + "…" : str;
}

// ---------- Init ----------

fetchBooks();