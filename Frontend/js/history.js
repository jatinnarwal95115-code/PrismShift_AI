(() => {
  const list = document.getElementById("historyList");
  const search = document.getElementById("historySearch");
  if (!list || !search) return;
  let conversations = [];

  const esc = window.PS.esc;
  const dateLabel = value => {
    if (!value) return "Date unavailable";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  };

  function render() {
    const query = search.value.trim().toLowerCase();
    const filtered = conversations.filter(item =>
      `${item.title || ""} ${item.mode || ""} ${item.subtype || ""}`.toLowerCase().includes(query)
    );
    list.innerHTML = filtered.map(item => `
      <article class="history-row ${item.mode === "reality" ? "reality" : "digital"}">
        <span class="history-symbol">${item.mode === "reality" ? "◈" : "✧"}</span>
        <div class="history-main">
          <strong>${esc(item.title || "Untitled conversation")}</strong>
          <small>${item.mode === "reality" ? "Reality Mode" : "Digital Mode"} · ${esc(dateLabel(item.updated_at))}</small>
        </div>
        <div class="history-actions">
          <button type="button" data-open="${Number(item.id)}">Open</button>
          <button type="button" data-delete="${Number(item.id)}">Delete</button>
        </div>
      </article>`).join("") || '<div class="empty-card"><span>◷</span><strong>No conversations found</strong><small>Your saved analyses will appear here.</small></div>';

    list.querySelectorAll("[data-open]").forEach(button => {
      button.addEventListener("click", () => openConversation(button.dataset.open));
    });
    list.querySelectorAll("[data-delete]").forEach(button => {
      button.addEventListener("click", () => deleteConversation(button.dataset.delete));
    });
  }

  async function openConversation(id) {
    try {
      const result = await window.PSApi.get(`/history/${encodeURIComponent(id)}`);
      const conversation = result.conversation;
      if (!conversation) throw new Error("Conversation data was missing.");
      sessionStorage.setItem("prismshift_open_conversation", JSON.stringify({
        id: conversation.id,
        mode: conversation.mode,
        messages: conversation.messages || [],
        input_data: conversation.input_data || {},
        image_url: conversation.image_url || null
      }));
      location.href = conversation.mode === "reality" ? "reality.html" : "digital.html";
    } catch (error) {
      window.PS.toast(error.message || "Could not open conversation.");
    }
  }

  async function deleteConversation(id) {
    if (!confirm("Delete this conversation? This cannot be undone.")) return;
    try {
      await window.PSApi.remove(`/history/${encodeURIComponent(id)}`);
      conversations = conversations.filter(item => String(item.id) !== String(id));
      render();
      window.PS.toast("Conversation deleted.");
    } catch (error) {
      window.PS.toast(error.message || "Could not delete conversation.");
    }
  }

  async function load() {
    list.innerHTML = '<div class="empty-card"><strong>Loading history…</strong></div>';
    try {
      const result = await window.PSApi.get("/history/");
      conversations = Array.isArray(result.history) ? result.history : [];
      render();
    } catch (error) {
      list.innerHTML = `<div class="empty-card"><strong>Could not load history</strong><small>${esc(error.message)}</small></div>`;
    }
  }

  search.addEventListener("input", render);
  load();
})();
