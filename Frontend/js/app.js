(() => {
  const $ = selector => document.querySelector(selector);
  const toast = message => {
    const element = $("#toast");
    if (!element) return;
    element.textContent = message;
    element.classList.add("show");
    window.clearTimeout(window.__psToastTimer);
    window.__psToastTimer = window.setTimeout(() => element.classList.remove("show"), 3000);
  };

  window.PS = {
    toast,
    esc(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      })[char]);
    },
    user: () => {
      try { return JSON.parse(localStorage.getItem("prismshift_user") || "{}"); }
      catch { return {}; }
    },
    logout: async () => {
      try {
        if (window.PSApi.getToken()) {
          await window.PSApi.request("/auth/logout", { method: "POST" }, { redirectOn401: false });
        }
      } catch (error) {
        console.warn("Logout request failed; clearing local session.", error);
      } finally {
        window.PSApi.clearSession();
        location.href = "login.html";
      }
    }
  };

  const page = document.body.dataset.page;
  const publicPage = page === "login" || page === "entry";
  if (!publicPage && !window.PSApi.getToken()) {
    location.replace("login.html");
    return;
  }

  document.querySelectorAll("[data-nav]").forEach(link => {
    if (link.dataset.nav === page) link.classList.add("active");
  });
  $("#logoutBtn")?.addEventListener("click", window.PS.logout);
  $("#profileLogout")?.addEventListener("click", window.PS.logout);
  $("#newAnalysisBtn")?.addEventListener("click", () => location.href = "dashboard.html");
  $("#mobileMenu")?.addEventListener("click", () => $("#sidebar")?.classList.toggle("open"));

  async function loadSidebarHistory() {
    const container = $("#sidebarHistory");
    if (!container || publicPage) return;
    try {
      const result = await window.PSApi.get("/history/");
      const items = Array.isArray(result.history) ? result.history.slice(0, 6) : [];
      container.innerHTML = items.map(item => `
        <button class="session-item" data-history-id="${Number(item.id)}">
          <span>${item.mode === "reality" ? "◈" : "✧"}</span>
          <span style="min-width:0">
            <span class="session-name">${window.PS.esc(item.title || "Untitled conversation")}</span>
            <span class="session-meta">${item.mode === "reality" ? "Reality" : "Digital"} · ${window.PS.esc(item.updated_at || "")}</span>
          </span>
        </button>`).join("") || '<div class="sidebar-empty">Your saved conversations will appear here.</div>';
      container.querySelectorAll("[data-history-id]").forEach(button => {
        button.addEventListener("click", async () => {
          try {
            const opened = await window.PSApi.get(`/history/${encodeURIComponent(button.dataset.historyId)}`);
            const conversation = opened.conversation;
            sessionStorage.setItem("prismshift_open_conversation", JSON.stringify({
              id: conversation.id,
              mode: conversation.mode,
              messages: conversation.messages || []
            }));
            location.href = conversation.mode === "reality" ? "reality.html" : "digital.html";
          } catch (error) {
            toast(error.message || "Could not open conversation.");
          }
        });
      });
    } catch (error) {
      container.innerHTML = '<div class="sidebar-empty">History is unavailable.</div>';
    }
  }
  loadSidebarHistory();

  if (!publicPage) {
    window.PSApi.get("/auth/me").then(result => {
      const user = result.user;
      if (!user) throw new Error("The backend did not return the current user.");
      localStorage.setItem("prismshift_user", JSON.stringify({
        id: user.id, name: user.name, email: user.email
      }));
      const name = user.name || "PrismShift user";
      if ($("#userName")) $("#userName").textContent = name;
      if ($("#userAvatar")) $("#userAvatar").textContent = name.charAt(0).toUpperCase();
      if ($("#welcomeTitle")) {
        $("#welcomeTitle").innerHTML = `Welcome back, <em>${window.PS.esc(name.split(" ")[0])}.</em>`;
      }
      if ($("#profileName")) $("#profileName").textContent = name;
      if ($("#profileNameDetail")) $("#profileNameDetail").textContent = name;
      if ($("#profileEmail")) $("#profileEmail").textContent = user.email || "—";
      if ($("#profileEmailDetail")) $("#profileEmailDetail").textContent = user.email || "—";
      if ($("#profileAvatar")) $("#profileAvatar").textContent = name.charAt(0).toUpperCase();
    }).catch(error => {
      if (window.PSApi.getToken()) toast(error.message || "Could not load your account.");
    });
  }
})();
