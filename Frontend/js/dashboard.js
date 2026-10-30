(async () => {
  const esc = window.PS.esc;
  const sidebar = document.getElementById("sidebarHistory");
  const recent = document.getElementById("dashboardRecent");

  function dateLabel(value) {
    if (!value) return "Date unavailable";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  function render(items) {
    const valid = Array.isArray(items) ? items : [];
    if (sidebar) {
      sidebar.innerHTML = valid.slice(0, 6).map(item => `
        <button class="session-item" data-open="${Number(item.id)}">
          <span>${item.mode === "reality" ? "◈" : "✧"}</span>
          <span style="min-width:0">
            <span class="session-name">${esc(item.title || "Untitled conversation")}</span>
            <span class="session-meta">${item.mode === "reality" ? "Reality" : "Digital"} · ${esc(dateLabel(item.updated_at))}</span>
          </span>
        </button>`).join("") || '<div class="sidebar-empty">No saved conversations yet.</div>';
    }
    if (recent) {
      recent.innerHTML = valid.slice(0, 3).map(item => `
        <button class="history-row ${item.mode === "reality" ? "reality" : "digital"}" data-open="${Number(item.id)}">
          <span class="history-symbol">${item.mode === "reality" ? "◈" : "✧"}</span>
          <span class="history-main">
            <strong>${esc(item.title || "Untitled conversation")}</strong>
            <small>${item.mode === "reality" ? "Reality Mode" : "Digital Mode"} · ${esc(dateLabel(item.updated_at))}</small>
          </span>
        </button>`).join("") || '<div class="empty-card"><span>✳</span><strong>Your next idea starts with an image.</strong><small>Completed analyses will appear here.</small></div>';
    }

    document.querySelectorAll("[data-open]").forEach(button => {
      button.addEventListener("click", () => openConversation(button.dataset.open));
    });
  }

  async function openConversation(id) {
    try {
      const result = await window.PSApi.get(`/history/${encodeURIComponent(id)}`);
      if (!result?.conversation) throw new Error("Conversation data was missing.");
      const conversation = result.conversation;
      sessionStorage.setItem("prismshift_open_conversation", JSON.stringify({
        id: conversation.id,
        mode: conversation.mode,
        messages: conversation.messages || []
      }));
      location.href = conversation.mode === "reality" ? "reality.html" : "digital.html";
    } catch (error) {
      window.PS.toast(error.message || "Could not open this conversation.");
    }
  }

  try {
    const result = await window.PSApi.get("/history/");
    render(result.history || []);
  } catch (error) {
    if (recent) recent.innerHTML = `<div class="empty-card"><strong>Recent activity unavailable</strong><small>${esc(error.message)}</small></div>`;
    if (sidebar) sidebar.innerHTML = '<div class="sidebar-empty">History could not be loaded.</div>';
  }
})();
