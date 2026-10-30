const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;

(() => {
  const TOKEN_KEY = "prismshift_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  }

  function clearSession() {
    setToken(null);
    localStorage.removeItem("prismshift_user");
    sessionStorage.removeItem("prismshift_open_conversation");
  }

  function errorMessage(data, fallback) {
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail.map(item => item.msg || "Invalid input").join("; ");
    }
    if (typeof data?.message === "string") return data.message;
    if (typeof data?.error === "string") return data.error;
    return fallback;
  }

  async function request(path, options = {}, settings = {}) {
    const { auth = true, redirectOn401 = true } = settings;
    const headers = new Headers(options.headers || {});
    if (auth && getToken()) headers.set("Authorization", `Bearer ${getToken()}`);

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers
    });

    const contentType = response.headers.get("content-type") || "";
    let data = null;
    if (contentType.includes("application/json")) {
      data = await response.json().catch(() => null);
    } else if (!options.expectBlob) {
      const raw = await response.text().catch(() => "");
      if (raw) {
        try { data = JSON.parse(raw); }
        catch { data = { detail: raw.slice(0, 500) }; }
      }
    }

    if (response.status === 401 && redirectOn401) {
      clearSession();
      if (!location.pathname.endsWith("login.html")) location.href = "login.html";
    }

    if (!response.ok) {
      const fallback = response.status === 0
        ? "Could not reach the PrismShift backend."
        : `Request failed (${response.status}).`;
      throw new Error(errorMessage(data, fallback));
    }

    return { response, data };
  }

  async function json(path, body, settings = {}) {
    const { data } = await request(path, {
      method: settings.method || "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }, settings);
    return data;
  }

  async function form(path, formData, settings = {}) {
    const { data } = await request(path, {
      method: settings.method || "POST",
      body: formData
    }, settings);
    return data;
  }

  async function get(path, settings = {}) {
    const { data } = await request(path, { method: "GET" }, settings);
    return data;
  }

  async function remove(path, settings = {}) {
    const { data } = await request(path, { method: "DELETE" }, settings);
    return data;
  }

  async function download(path, formData, filename) {
    const { response } = await request(path, {
      method: "POST",
      body: formData,
      expectBlob: true
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  window.PSApi = {
    baseUrl: API_BASE_URL,
    tokenKey: TOKEN_KEY,
    getToken,
    setToken,
    clearSession,
    request,
    json,
    form,
    get,
    remove,
    download
  };
})();
