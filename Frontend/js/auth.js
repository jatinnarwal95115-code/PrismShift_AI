(() => {
  const $ = id => document.getElementById(id);
  const tabs = document.querySelectorAll("[data-auth]");
  const form = $("authForm");
  if (!form) return;

  let mode = "login";
  const notify = message => {
    const toast = $("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 3000);
  };

  function setMode(nextMode) {
    mode = nextMode;
    tabs.forEach(button => button.classList.toggle("active", button.dataset.auth === mode));
    $("authTitle").innerHTML = mode === "login" ? "Welcome <em>back.</em>" : "Create your <em>space.</em>";
    $("authSub").textContent = mode === "login"
      ? "Sign in to continue exploring two worlds."
      : "A fresh perspective is one step away.";
    $("nameLabel").classList.toggle("hidden", mode === "login");
    $("authName").required = mode === "signup";
    $("authPassword").minLength = mode === "signup" ? 8 : 1;
    $("authPassword").autocomplete = mode === "login" ? "current-password" : "new-password";
    $("authSubmit").innerHTML = mode === "login" ? "Sign in <span>→</span>" : "Create account <span>→</span>";
  }

  tabs.forEach(button => button.addEventListener("click", () => setMode(button.dataset.auth)));
  $("togglePassword")?.addEventListener("click", () => {
    const password = $("authPassword");
    password.type = password.type === "password" ? "text" : "password";
    $("togglePassword").textContent = password.type === "password" ? "Show" : "Hide";
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const submit = $("authSubmit");
    const email = $("authEmail").value.trim();
    const password = $("authPassword").value;
    const name = $("authName").value.trim();

    if (mode === "signup" && password.length < 8) {
      notify("Password must contain at least 8 characters.");
      return;
    }
    if (mode === "signup" && name.length < 2) {
      notify("Please enter your name (at least 2 characters).");
      return;
    }

    submit.disabled = true;
    submit.textContent = mode === "login" ? "Signing in…" : "Creating account…";
    try {
      const payload = mode === "signup"
        ? { name, email, password }
        : { email, password };
      const result = await window.PSApi.json(
        mode === "signup" ? "/auth/register" : "/auth/login",
        payload,
        { auth: false, redirectOn401: false }
      );

      if (!result?.token || !result?.user) {
        throw new Error("The authentication response did not include a token and user.");
      }
      window.PSApi.setToken(result.token);
      localStorage.setItem("prismshift_user", JSON.stringify({
        id: result.user.id, name: result.user.name, email: result.user.email
      }));
      location.href = "dashboard.html";
    } catch (error) {
      notify(error.message || "Authentication failed.");
      submit.innerHTML = mode === "login" ? "Sign in <span>→</span>" : "Create account <span>→</span>";
    } finally {
      submit.disabled = false;
    }
  });

  if (window.PSApi.getToken()) {
    window.PSApi.get("/auth/me", { redirectOn401: false })
      .then(() => { location.href = "dashboard.html"; })
      .catch(() => window.PSApi.clearSession());
  }
})();
